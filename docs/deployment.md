# The gate, live

> The status table under *What is deployed* is current as of 2026-10-14 (image v18: image_url, the burst loop with a time budget, and the English block; Function URL since v14). The current response fields are listed in [`technical-report.md`](technical-report.md) §3; the scenario below shows the shape of the answer, not a measurement of this site.

    https://3p4k7s4bx7.execute-api.ap-southeast-2.amazonaws.com

`GET` describes the interface. `POST` takes JSON:

```json
{ "image_base64": "...", "fov_deg": 60, "posted_kmh": 50, "lane_width_m": 3.0 }
```

or, since image v17, a photo's raw GitHub URL instead of the bytes, with optional
photos taken a second apart (the response then opens with an English `en` block and
carries `red_line_gap_burst` with every step traced):

```json
{ "image_url": "https://raw.githubusercontent.com/<owner>/<repo>/main/evidence/<set>/<file>.jpg",
  "burst_urls": ["<a photo taken a second earlier>", "<a second later>"],
  "fov_deg": 56.812, "posted_kmh": 50 }
```

`lane_width_m` is optional. Without it the width check is skipped, and the
response says it was skipped rather than quietly dropping it - a photograph
carries no scale, so the width has to come from a tape or a plan.

The pitch, the road's bearing and a scale were all required until
2026-09-20 and all three are gone: the angle measured is invariant to the
camera's rotation, the road's own markings give its direction, and a rate
is dimensionless. Those three were also the three inputs that could not be
established - the pitch and the road bearing were too uncertain, and no
scale survived its own check -
so the version that asked for them answered INDETERMINATE to everything.

## What comes back

The answer is a **scenario**: what a person riding through this place
meets, in the order they meet it. One line per thing that happens to them,
composed only from findings that were actually detected in that frame.

```
1. 你以 50 公里的速度接近，前方車道要縮減。
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
| `TAPER_TOO_STEEP` | 車道縮減漸變段過陡(對照值，非判定) | 施工之交通管制守則 p.9, L = W·V²/155 |
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
| function | `road-marking-gate`, container, arm64, **3008 MB** (the account's cap; 10240 MB was refused again on 2026-10-14), timeout **300 s**, reserved concurrency **3** |
| access | POST requires the `x-access-token` header (token set on the function, given to judges with the submission); GET is open |
| limits | API Gateway throttling 1 request/s, burst 3; the account's Lambda concurrency quota was raised from 10 to 1000 on 2026-10-13; $5/month budget alert |
| entry points | API Gateway (30 s limit) for small requests; since 2026-10-14 a Lambda Function URL, `https://cjy6l22ni2mh5gtc6wgjltz7bu0ehjjb.lambda-url.ap-southeast-2.on.aws/`, with no 30 s limit, for full-size photos. A full-size photo (JPEG 90, 2.2 MB) took **145.5 s** live on image v14 and returned the red-line gap 0.668 m on F31 |
| logs | CloudWatch, 14-day retention |
| image | `road-marking-gate:v18` (live 2026-10-14: v14 added the new site figures, v15 the GET text for the Function URL, v16 dropped the bridge's distance from a site point that came from Google Maps, v17 added image_url, the burst loop and the English block, and copies the two evidence MANIFESTs into the image, v18 the review fixes (a measured gap stands without a burst, a time budget, size caps); v17 kept for rollback), `public.ecr.aws/lambda/python:3.12`, numpy pinned 2.5.3 |
| OpenCV | `opencv-python-headless==5.0.0.93`, reported by the running function as 5.0.0 |
| public entry | API Gateway HTTP API `3p4k7s4bx7`, proxy to the function |
| role | `road-marking-gate-role`, basic execution only |

Cold start 7.3 s on the first call, 2.0-2.4 s warm. Costs nothing at this
traffic: Lambda's free tier covers it and the HTTP API's first million
requests are free.

## The Function URL, and why it returned 403 before

A Lambda Function URL was created first, on 2026-09-20, and returned 403 to every
request even though its resource policy carried `lambda:InvokeFunctionUrl` for
`Principal: "*"` with `FunctionUrlAuthType: NONE`. It was removed and API Gateway
used instead. API Gateway answers within 30 s, and a full-size photo needs about
2.5 minutes (about 4 with v17's burst check), so full-size photos always timed out through API Gateway.

On 2026-10-14 the cause was found: a public Function URL now also needs
`lambda:InvokeFunction` for `Principal: "*"`, conditioned on
`lambda:InvokedViaFunctionUrl: true`. With both statements the new URL answers:
`GET` 200, `POST` with a wrong token 401, and a full-size F31 measured in 145.5 s.
The token check in the handler is the same for both doors; reserved concurrency 3
caps how many requests can run at once, since a Function URL has no gateway throttle.

```sh
aws lambda create-function-url-config --function-name road-marking-gate --auth-type NONE
aws lambda add-permission --function-name road-marking-gate --statement-id furl-invoke-url \
  --action lambda:InvokeFunctionUrl --principal '*' --function-url-auth-type NONE
aws lambda add-permission --function-name road-marking-gate --statement-id furl-invoke-fn \
  --action lambda:InvokeFunction --principal '*' --invoked-via-function-url
aws lambda put-function-concurrency --function-name road-marking-gate --reserved-concurrent-executions 3
aws lambda update-function-configuration --function-name road-marking-gate --timeout 300
```

## The size limit

The handler refuses an image over 3 MB of decoded bytes with a reason the
caller can act on. Larger requests may not reach it: Lambda's synchronous
payload is 6 MB and base64 adds a third, so API Gateway answers its own
`413` for anything over about 4.4 MB. Re-save the photograph as JPEG at
quality 90 rather than downscaling it, because `red_line_gap` and
`taper_table_4_2_7` need the camera's original resolution and refuse at
2000 px.

## Rebuilding

`AWS_PROFILE` was hardcoded here to another project's profile name — the
previous competition entry, stopped 2026-09-19. This project does not
name it. Set the profile to whatever your own credentials are called.

```sh
AWS_PROFILE=<your-profile> AWS_REGION=ap-southeast-2 ACCOUNT=<account> \
  ./aws/build-and-push.sh v18
aws lambda update-function-code --function-name road-marking-gate \
  --image-uri <account>.dkr.ecr.ap-southeast-2.amazonaws.com/road-marking-gate:v18
```

`--provenance=false --sbom=false` are in the script and are not optional:
without them buildx writes an OCI manifest and Lambda refuses the image.

## Removed

The previous entry's two functions, their Function URL and its ECR
repository with 18 images, all deleted on 2026-09-20 at the owner's
instruction. The account now holds this project only.

Their names are not repeated here. This project is judged on its own and
nothing in it should read as though it belongs to the earlier one.
