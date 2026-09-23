# Independent verification, 2026-09-20

Recorder role in a three-way verification. Everything below was re-run by me
on this machine; nothing is carried over from the main agent's prose. Commands
are given verbatim so any of this can be re-run without me.

Host: darwin 25.6.0. Python: `/opt/anaconda3/bin/python3` (3.12.7).
Repo HEAD at time of checking: `afda24c`, 2026-09-20 22:53:51 +0800,
"Corroborate the ±5 cm against a central agency, not just a city".
Working tree clean apart from two untracked files:
`results/dash_population.json`, `scripts/dash_population.py`.

## Headline

**No claim was found false.** Four of six verified in full. Two are
**PARTIAL**, and the wording rather than the substance is what fails:

- Claim 6 — `tests/test_pitch_roundtrip.py` does not "pass" under pytest. It
  contains no test function and no assertion, so pytest collects zero items
  and exits 5. Run as a script it produces the stated result and exits 0.
- Claim 4 — the six numbers are all described as withdrawn, and none is in
  the figure registry or reachable from `src/`. But five of them are still
  sitting in `results/*.json` as plain unflagged values.

One further discrepancy, not among the claims, is recorded at the end:
`docs/deployment.md` states a verdict for this exact request that the live
endpoint no longer returns.

---

## 1. Public endpoint, GET — VERIFIED

```sh
curl -s -m 60 -w "\n[HTTP %{http_code}] time=%{time_total}s\n" \
  https://3p4k7s4bx7.execute-api.ap-southeast-2.amazonaws.com
```

```json
{"service": "road marking taper gate", "opencv": "5.0.0", "post": {"image_base64": "JPEG or PNG, <= 3 MB encoded; 2000 px on the long side is plenty", "fov_deg": "horizontal field of view", "pitch_deg": "negative looks down", "heading_deg": "compass bearing the camera faced", "road_bearing_deg": "compass bearing the road runs", "posted_kmh": "speed limit in force"}, "states": {"WITHIN_REFERENCE": "clear of the reference by more than the measurement's doubt", "STEEPER_THAN_REFERENCE": "past it by more than the doubt", "INDETERMINATE": "measured, but nearer the reference than this measurement can resolve", "CANNOT_MEASURE": "the photograph does not show what is needed"}}
```

`[HTTP 200] time=1.180575s`. The endpoint answers, it is JSON, it describes
the interface, and `"opencv": "5.0.0"` is present. Four states are declared,
including `INDETERMINATE`.

## 2. Three POSTs of one capture — VERIFIED

`output/api/f90_p-20.jpg`, 56,424 bytes, base64 length 75,232. Payload built
with:

```py
body = {"image_base64": b64, "fov_deg": 90, "pitch_deg": -20,
        "heading_deg": 128, "road_bearing_deg": 141.6, "posted_kmh": kmh}
```

```sh
curl -s -m 120 -X POST -H "Content-Type: application/json" \
  --data @req_$k.json \
  https://3p4k7s4bx7.execute-api.ap-southeast-2.amazonaws.com
```

All three returned HTTP 200. Verdicts, exactly as claimed:

| posted_kmh | state | taper_rate | required_rate | ratio | wall time |
|---|---|---|---|---|---|
| 30 | `WITHIN_REFERENCE` | 0.066 | 0.172 | 0.38 | 2.655 s |
| 50 | `INDETERMINATE` | 0.066 | 0.062 | 1.06 | 2.411 s |
| 60 | `STEEPER_THAN_REFERENCE` | 0.066 | 0.043 | 1.53 | 2.337 s |

Reasons returned, verbatim:

- 30: "the taper is clear of what the reference asks at 30 km/h by more than
  the +-0.018 of doubt"
- 50: "the taper measures 0.066 against a reference of 0.062 at 50 km/h, and
  the two are closer than the +-0.018 this measurement can resolve. Neither
  answer is available"
- 60: "the taper is 1.5 times steeper than the reference asks at 60 km/h, by
  more than the +-0.018 of doubt; its geometry suits about 49 km/h"

Shared across all three responses: `"opencv": "5.0.0"`, `image_px [640, 640]`,
`guard_band 0.0184`, `arm_to_band_deg 44.7`, `arms 19`,
`camera_to_road_deg 13.6`, `chord_run_camera_heights 3.019`,
`equivalent_kmh 48.5`. Only `required_rate`, the decision bounds and the state
move with `posted_kmh`, which is what a guard band on a fixed measurement
should do.

Note for the record: the returned rate is **0.066**, not the 0.068 that
`docs/status-2026-09-20.md` tabulates for `f90_p-20`, nor the 0.070 that
`docs/tolerances.md` works through. Neither figure is registered, and 0.070 is
the mean of the doc's three captures rather than this one, so this is drift in
prose, not a contradicted figure.

## 3. ±5 cm lateral tolerance in both sources — VERIFIED

```sh
grep -n "5cm\|5 cm\|±5\|橫向位置" docs/source-02898-tolerances.txt
grep -n "5cm\|5 cm\|±5\|橫向位置" docs/source-02898-freeway.txt
```

`docs/source-02898-tolerances.txt` (臺北市), lines 379-385:

```
3.3     許可差
3.3.1   標線長度：每一縱向 3m 標線之許可差為±5cm。
3.3.2   標線寬度：標線寬度之許可差為±6mm。
3.3.3   車道寬度：車道寬度為從路面邊緣至標線中心，或兩標線之中心間距，
        其許可差為±5cm。
3.3.4   標線之線形：標線之橫向位置與契約圖說所示及工程司核可之位置，其
        許可差為±5cm。
```

`docs/source-02898-freeway.txt` (高公局), lines 120-126:

```
(7)   標繪標線之容許誤差規定如下︰
      A. 標線長度︰每一縱向 4 m 標線之容許誤差為±5 cm。
      B. 標線寬度︰標線寬度之容許誤差為±6 mm。
      C. 車道寬度︰車道寬度為從路面邊緣至標線中心，或兩標線之中
        心間距，其容許誤差為±5 cm。
      D. 標線位置︰標線之橫向位置應按設計圖所示位置，其容許誤差
        為±5 cm。
```

Both files carry a clause fixing the **lateral position** of a marking at
**±5 cm** — 臺北市 §3.3.4 and 高公局 §3.1(7)D. The width (±6 mm) and lane
width (±5 cm) clauses also match. The only divergence is the length clause,
3 m against 4 m, and that is not the clause the guard band uses. The
corroboration claim in `docs/tolerances.md` holds.

## 4. Git log and the withdrawn numbers — PARTIAL

```sh
git log --oneline | wc -l          # 37
git log --oneline | head -5
```

```
afda24c Corroborate the ±5 cm against a central agency, not just a city
3121a8f Add INDETERMINATE, so a near miss stops reading as a breach
21356d4 Find the construction tolerance, and let it size the guard band
1e90d04 Route refusals with a typed judgment, and send no image to do it
abbf307 Measure the taper as a chord, because that is what the rule defines
```

37 commits, in a coherent sequence. Verified.

**Described as withdrawn — VERIFIED.** `docs/status-2026-09-20.md` lines
25-34 carry a "## Withdrawn" heading, the sentence "Every one of these was
printed by something in this repository and is wrong", and six bullets
covering all seven values: 84.1%; 25% and 16%; 18.3 km/h and 18.7 km/h;
1.9 m; 42.1 km/h; 12.8%. Each bullet names the specific failure mode. Nothing
is missing.

**Not used as if valid — PARTIAL.** Two separate findings.

*src/ is clean.* Both hits are self-incriminating prose, not use:

```
src/marking/gate.py:40:          alone rejects the 84.1%, the 25% and the 16%.
src/marking/identify.py:7:which quietly assumed the camera faced along the road. It returned 18.3 km/h
```

`grep -rn "results/" src/` returns nothing, so no module reads any result file.

*The figure registry is clean.* `results/figure_registry.json` holds 9
published figures and none is a withdrawn value:

```
chevron_to_boundary_deg 46.41 | chevron_to_road_deg 57.47
chevron_method_spread_deg 1.97 | taper_rate_relative_deg 11.4
taper_equivalent_design_speed 27.8 | accidents_before_per_month 1.0
accidents_during_per_month 2.62 | accidents_national_control_ratio 1.04
accidents_poisson_p 0.00016
```

```sh
/opt/anaconda3/bin/python3 scripts/check_figures.py
# 9 published figures match their sources      (exit 0)
```

The registry's own note says a number not listed there is not verified, so by
the repo's stated rule none of the withdrawn figures is published.

*results/ still carries five of them, unflagged.*
`grep -rln "withdrawn\|superseded\|retracted" results/ src/` returns **nothing**
— there is no in-file marker anywhere. The raw values remain:

| withdrawn figure | still at | value in file |
|---|---|---|
| 25% erased | `results/erasure.json` | `"median_erased_share": 0.246` |
| 16% erased | `results/erasure_edges.json` | `"erased_share_median": 0.164` |
| 18.3 km/h | `results/epochs.json:60` | `"equivalent_kmh": 18.3` |
| 42.1 km/h | `results/taper_after.json:13` | `"equivalent_kmh": 42.1` |
| 1.9 m band | `results/band_width.json` | `"band_width_m": 1.86 / 1.95 / 1.91` |

84.1% and 12.8% were searched for and are **not** present anywhere in `src/`
or `results/` as values (`grep -rn "0\.841\|0\.128\|12\.8" results/*.json`
returns only unrelated periodicity and dash-length figures). 18.7 km/h is also
gone — `results/taper_after.json` now holds 42.1, its successor.

So the honest statement is narrower than the claim: nothing in `src/` uses a
withdrawn number, nothing publishes one, and no code path reads these files —
but five of the numbers sit on disk in `results/` with nothing in the file
itself saying they are wrong. A reader who opens `results/taper_after.json`
without also reading `docs/status-2026-09-20.md` has no way to know. One
partial mitigation exists and is narrow: `results/ipm_band_width.json` marks
its captures `"accepted": false`.

## 5. Local reproduction of the three verdicts — VERIFIED

```sh
/opt/anaconda3/bin/python3 -c "
import sys; sys.path.insert(0,'src')
import cv2
from marking.gate import assess
img = cv2.imread('output/api/f90_p-20.jpg')
for kmh in (30,50,60):
    v = assess(img, fov_deg=90, pitch_deg=-20, posted_kmh=kmh,
               heading_deg=128, road_bearing_deg=141.6)
    print(kmh, v.state, v.taper_rate, v.required_rate, v.ratio_too_steep)"
```

```
local opencv 5.0.0
image shape (640, 640, 3)
30 WITHIN_REFERENCE rate= 0.066 required= 0.172 ratio= 0.38
50 INDETERMINATE rate= 0.066 required= 0.062 ratio= 1.06
60 STEEPER_THAN_REFERENCE rate= 0.066 required= 0.043 ratio= 1.53
```

Identical to the live endpoint in state, rate, required rate and ratio, to
every digit returned. Local OpenCV also reports 5.0.0, so the deployed
container and this machine agree on the library as well as the answer.

## 6. tests/test_pitch_roundtrip.py — PARTIAL

```sh
/opt/anaconda3/bin/python3 -m pytest tests/test_pitch_roundtrip.py -v
```

```
collecting ... collected 0 items
============================ no tests ran in 0.10s =============================
```

Exit code **5** (`no tests collected`). `grep -nE "^(def |class )"` finds a
single top-level definition, `def project(...)` at line 13 — no `test_*`
function, no `assert` anywhere in the file. **Under pytest this file cannot
pass and cannot fail.** It is a script, and the claim that it "passes" is not
supported by pytest.

Run the way it is written, it does work and its result is as the status
document reports:

```sh
/opt/anaconda3/bin/python3 tests/test_pitch_roundtrip.py    # exit 0
```

24 pitch × fov combinations; 2 off frame (−40/40 and −42/40); **22 in-frame
cases, every one reading back `0.200000` with error `±0.000000`**. Final line:

> every case round-trips exactly: rectify.py handles pitch correctly, so the
> inconsistency is in what is being measured, not in the projection

So the *finding* the file exists to establish is verified — the projection is
exact to six decimals across −12° to −42° and 40° to 90° of field of view, and
the count of 22 in `docs/status-2026-09-20.md` is right. What is not verified
is that it is a passing test. It asserts nothing, so it will not fail a CI run
either; a regression in `rectify.py` would change the printed numbers and
still exit 0.

`tests/test_rectify.py` exists alongside it and was not part of the claim, so
it was not run.

---

## Discrepancy found outside the six claims

`docs/deployment.md`, under "What the live endpoint actually does":

> | Street View capture, 30 and 50 km/h | `WITHIN_REFERENCE`, 2.0-2.4 s |

The live endpoint returns `INDETERMINATE` at 50 km/h, as verified in item 2
above, and `src/marking/gate.py`'s own docstring says it should. The table
predates commit `3121a8f` "Add INDETERMINATE" and was not updated with it.
The timing, 2.0-2.4 s warm, is accurate.

The same staleness is in `docs/status-2026-09-20.md` lines 164-167, where the
gate is described as having three states and `INDETERMINATE` is absent from
the list, although the `GET` response and the module docstring both declare
four.

This matters more than it looks. The whole argument of `docs/tolerances.md` is
that 0.070 at 50 km/h "without a guard band reads as a breach and with one
reads as not knowing" — and `docs/deployment.md` is the document a reader
reaches first, reporting exactly the confident verdict the guard band was
built to withhold.

## Not verified

- Nothing was checked about the AWS account, the Lambda configuration, the
  ECR image, the role, or the deletions recorded in `docs/deployment.md`. Only
  the endpoint's behaviour over HTTPS was exercised.
- The 403 on the Lambda Function URL, and the account-level public access
  block offered as its explanation, were not reproduced.
- `src/marking/route.py` and the `MODEL_UNAVAILABLE` path were not exercised;
  no claim covered them.
- Whether 臺北市's chapter 02898 binds work on a 新北市 縣道 is a legal question
  and is outside what can be checked by running something. Both documents were
  read as text only; neither was authenticated against its issuing authority.

Nothing was committed. Two untracked files predate this check and were left
alone.
