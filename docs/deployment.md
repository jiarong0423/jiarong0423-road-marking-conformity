# The gate, live

> The status table under *What is deployed* is current as of 2026-09-23. The example response and the finding table below it predate v12; the current response fields are listed in [`technical-report.md`](technical-report.md) §3.

    https://3p4k7s4bx7.execute-api.ap-southeast-2.amazonaws.com

`GET` describes the interface. `POST` takes JSON:

```json
{ "image_base64": "...", "fov_deg": 60, "posted_kmh": 50, "lane_width_m": 3.0 }
```

`lane_width_m` is optional. Without it the width check is skipped, and the
response says it was skipped rather than quietly dropping it - a photograph
carries no scale, so the width has to come from a tape or a plan.

The pitch, the road's bearing and a scale were all required until
2026-09-20 and all three are gone: the angle measured is invariant to the
camera's rotation, the road's own markings give its direction, and a rate
is dimensionless. Those three were also the three inputs that could not be
established - the Street View pitch carries a degree or two of suspension,
the bearing measured 141.87 ± 8.32°, and no scale survived its own check -
so the version that asked for them answered INDETERMINATE to everything.

## What comes back

The answer is a **scenario**: what a person riding through this place
meets, in the order they meet it. One line per thing that happens to them,
composed only from findings that were actually detected in that frame.

```
1. 你以 50 公里的速度接近，前方車道要縮減。漸變段的幾何只適合 29 公里，
   你通過它的時間是 1.2 秒。駕駛人光是察覺並反應就要 2.5 秒。
2. 一輛車跟你並行。法定側向間隔是半公尺，汽車加機車加那半公尺需要
   3.03 公尺，大型車旁邊要 3.75 公尺，而這條車道是 3.00 公尺。
3. 你往右看：路緣畫著紅線，依規定紅線劃設於緣石，可行駛的路面到那裡就沒了。
   你往左看：雙白實線，那裡禁止變換車道。
4. 而你所在的位置，路面分得出 3 種鋪面，腳下有新舊路面的銜接處。
5. 所以：右邊不是車道，左邊禁止變換，原地湊不出法定間隔。
```

Alongside it, `findings` carries the same thing itemised, each with its
measurement, its clause and its own state. The scenario is the claim; the
findings are how it was arrived at.

| code | what it means | clause |
|---|---|---|
| `TAPER_TOO_STEEP` | 車道縮減漸變段過陡 | 交通工程手冊 p.9, L = W·V²/155 |
| `NO_LANE_CHANGE` | 雙白實線，禁止變換車道 | 道路交通標誌標線號誌設置規則 §167 |
| `EDGE_NOT_CARRIAGEWAY` | 沿路的紅線；畫在哪種面上、可行駛路面是否至此為止，程式不判 | §169 |
| `SURFACE_IN_PIECES` | 行車道內有新舊鋪面銜接處 | 新北市挖掘道路審查原則 |
| `LANE_TOO_NARROW` | 汽機車並行不足法定間隔 | 道路交通安全規則 §101 |

Each finding still carries `WITHIN_REFERENCE`, `STEEPER_THAN_REFERENCE`,
`INDETERMINATE` or `CANNOT_MEASURE`, always with `basis`. `INDETERMINATE`
is not a weak version of the other two: it means the measurement succeeded
and the value sits inside the guard band, so no verdict is available. This
page said 50 km/h returned `WITHIN_REFERENCE` until 2026-09-20, which was
the stale confident answer the guard band exists to withhold.

Why a scenario and not a list: a list of codes tells an engineer which
clauses are in play. It does not tell anyone what the road is like to use,
and that is the thing being complained about. No single code on its own is
the problem here - the complaint is that the right is not carriageway, the
left is forbidden, and the lane in between is not wide enough, all at once,
which is a sentence about a person rather than an audit.

## What is deployed

| | |
|---|---|
| account / region | <account>, ap-southeast-2 |
| function | `road-marking-gate`, container, arm64, **3008 MB** (the account's current cap; 10240 MB needs an AWS limit increase: a full-resolution photo takes 52.5 s on 2 CPUs, over the gateway's 30 s), 60 s |
| access | POST requires the `x-access-token` header (token set on the function, given to judges with the submission); GET is open |
| limits | API Gateway throttling 1 request/s, burst 3; the account's total Lambda concurrency is 10; $5/month budget alert |
| entry points | API Gateway only; the unused Lambda Function URL was removed 2026-09-23 |
| logs | CloudWatch, 14-day retention |
| image | `road-marking-gate:v13` (live 2026-09-23), `public.ecr.aws/lambda/python:3.12`, numpy pinned 2.5.3 |
| OpenCV | `opencv-python-headless==5.0.0.93`, reported by the running function as 5.0.0 |
| public entry | API Gateway HTTP API `3p4k7s4bx7`, proxy to the function |
| role | `road-marking-gate-role`, basic execution only |

Cold start 7.3 s on the first call, 2.0-2.4 s warm. Costs nothing at this
traffic: Lambda's free tier covers it and the HTTP API's first million
requests are free.

## Why API Gateway and not a Function URL

A Lambda Function URL was created first and returned 403 to every request.
Its `AuthType` is `NONE` and the resource policy carries the right statement
- `Principal: "*"`, `lambda:InvokeFunctionUrl`, conditioned on
`FunctionUrlAuthType: NONE` - and direct `aws lambda invoke` on the same
function returns 200 with a full verdict, so the function was never the
problem. The account is not in an Organization and the calling user has no
permissions boundary, which leaves the account-level public access block for
Lambda. The installed CLI (2.36.44) has no subcommand for it, so it could
not be read or changed from here.

That is unresolved rather than fixed. The HTTP API goes around it.

## What the live endpoint actually does

| request | result |
|---|---|
| f60_p-20, 30 km/h | `INDETERMINATE` - 0.1835 against 0.1722, inside the ±0.0199 band |
| f60_p-20, 40 km/h | `STEEPER_THAN_REFERENCE`, 1.9x |
| f60_p-20, 50 km/h | `STEEPER_THAN_REFERENCE`, **3.0x**, "the geometry suits about 29 km/h" |
| f60_p-20, 60 km/h | `STEEPER_THAN_REFERENCE`, 4.3x |

Every response carries the candidate list the search considered, with the
hatching evidence for each - `arms`, `lopsided`, `nearest_px`, `borders` -
so a reader can see which line was chosen as §171's boundary and why the
others were not.
| a capture whose arms fail §171 | `CANNOT_MEASURE`: the arms lie 32° from the band, not 45° |
| the same image without `road_bearing_deg` | `CANNOT_MEASURE`: it will not guess where the road runs |
| 2026 field photograph, downscaled to 1500x2000 | `CANNOT_MEASURE`: only one arm survives |

The last is the right answer. Two thirds of that chevron has been ground
off, and what is left does not support the measurement.

## A limit that is documented but not enforced

The handler caps an image at 3 MB and explains why. It never fires: Lambda's
synchronous request payload is 6 MB, base64 adds a third, and API Gateway
rejects anything larger with its own `413 Request Entity Too Large` before
the function is invoked. A 4.81 MB photograph becomes 6.41 MB encoded and is
turned away by AWS with no reason a caller can act on. The cap in the code is
documentation, not a defence, and callers should downscale to about 2000 px
on the long side - which costs the gate nothing, since it measures in the
bird's eye plane.

## Rebuilding

`AWS_PROFILE` was hardcoded here to another project's profile name — the
previous competition entry, stopped 2026-09-19. This project does not
name it. Set the profile to whatever your own credentials are called.

```sh
AWS_PROFILE=<your-profile> AWS_REGION=ap-southeast-2 ACCOUNT=<account> \
  ./aws/build-and-push.sh v3
aws lambda update-function-code --function-name road-marking-gate \
  --image-uri <account>.dkr.ecr.ap-southeast-2.amazonaws.com/road-marking-gate:v3
```

`--provenance=false --sbom=false` are in the script and are not optional:
without them buildx writes an OCI manifest and Lambda refuses the image.

## Removed

The previous entry's two functions, their Function URL and its ECR
repository with 18 images, all deleted on 2026-09-20 at the owner's
instruction. The account now holds this project only.

Their names are not repeated here. This project is judged on its own and
nothing in it should read as though it belongs to the earlier one.
