# What OpenCV 5 is doing here

2026-09-21. Checked against the official OpenCV 5 pages and against the
build that actually ships in the Lambda image,
`opencv-python-headless==5.0.0.93`, which reports `5.0.0`.

Registration, added 2026-09-21 under standing rule 2. The capability table
below, the model's size and the CPU feature line are now produced by
`scripts/opencv5_build.py` into `results/opencv5_build.json` and are in
`results/figure_registry.json`. The introspection ran on a Darwin arm64
host, not inside the Lambda image; same package version, different wheel,
and the output records the platform so the two cannot be conflated. Every
figure on this page that comes from a run over the 42 photographs is
marked below as not reproduced - those runs cost about 45 minutes and were
not repeated.

## What the release adds, and what this build exposes

Re-derived: `/opt/anaconda3/bin/python3 scripts/opencv5_build.py`. Every
cell in the "in this build" column below is an assertion in
`results/opencv5_build.json`.

| capability | official | in this build |
|---|---|---|
| `CV_32U`, `CV_64U`, `CV_64S`, `CV_Bool`, `CV_16F` | yes | yes |
| `CV_16BF` (`cv::bfloat`) | yes | **no**, not exposed to Python |
| 0D and 1D `Mat` | yes | via numpy, not separately visible |
| `calib3d` split into `geometry`, `calib`, `stereo`, `ptcloud` | yes | only `cv2.stereo`; the others are not exposed to Python |
| `Features2D` renamed `Features` | yes | neither `cv2.features` nor `cv2.features2d` present |
| new DNN engine, ONNX coverage 13% → 64% (OpenCV's own figures, cited not measured) | yes | **yes**: `ENGINE_CLASSIC`, `ENGINE_NEW`, `ENGINE_ORT`, `ENGINE_AUTO` |
| Hardware Acceleration Layer, Universal Intrinsics v2 | stated on the wiki without detail | `getCPUFeaturesLine()` present and reporting |

## What is used, and what was rejected

Most of the list is not applicable here and saying so is part of the
answer. The marking mask is a `uint8` 0/255 image; making it `CV_Bool`
changes its type and detects nothing new. There is no stereo pair, no
point cloud, no feature matching. Adding those calls would put OpenCV 5
API names in the source without changing a single measurement, and the
rubric asks for depth, not vocabulary.

Two are real.

**The new DNN engine.** `cv2.dnn.readNet(path, "", "", cv2.dnn.ENGINE_NEW)`
loads an ONNX M-LSD line-segment detector exported from the Apache-2.0
PyTorch port, 2.4 MiB, and runs a 512x512 forward pass in a median 44.5 ms
on this machine (n=20 passes after one untimed warm-up). The 49 ms written
here first was a single run. It is not a property of the model: three
invocations of `scripts/opencv5_build.py` on the same machine gave medians
of 34.4, 41.2 and 44.5 ms, so anything in the thirties or forties is the
same measurement. What the number is good for is the order of magnitude -
tens of milliseconds, not hundreds. It
is a genuine OpenCV 5 path: the classic engine's ONNX coverage was under
13%. Whether it is worth using is a separate question, measured below and
not assumed. **It was measured and it lost. It is not in the pipeline.**

**The hardware acceleration layer on Arm.** The Lambda function is
`arm64`, which on AWS is Graviton, and the image is built with
`--platform linux/arm64`. `cv2.getCPUFeaturesLine()` on an Arm host here
reports `NEON FP16 NEON_DOTPROD NEON_FP16 *NEON_BF16`, so the dispatch to
NEON kernels is live rather than assumed. Re-run 2026-09-21 on the arm64
development host, where it returns that string exactly and is registered
from `results/opencv5_build.json`; the Lambda image itself was not
re-measured in that session, so "on Graviton" remains an inference from
the build platform rather than a reading taken there. That is the hard
condition the
competition's Cloud-Optimized OpenCV award states: the core workload runs
on Graviton. What is still missing for that award is its other half, a
reproducible measurement against a baseline, which means the same image
built for x86_64 and timed on the same photographs.

## The test the DNN has to pass

The project's defect is that the measured taper angle is not reproducible
across nine encodings of one photograph. A line detector that is more
repeatable would fix it, and three have already failed that test: OpenCV's
LSD, FastLineDetector, and rescaling the current detector's parameters
all gave wider angle spreads than what is here.

M-LSD was measured the same way, on the same grid, over all 42
photographs, on the condition that it would be used only if it won. The
visual check first: it traces building edges, the sign gantry, the pole
and the kerb cleanly, and it largely does not trace the chevron's
stripes, which is what a wireframe detector does and is not what this
measurement needs.

It appeared to win - the median angle spread fell from 6.3 to 5.9
degrees, with photographs measuring tighter than 5 degrees rising from 9
to 13. That was an artefact. The image was being squashed from 3:4 into
the model's square input, which changes the aspect ratio by a third and
with it every angle in the frame, and the distortion happened to make the
spread look smaller. Letterboxed, so that the angles survive, it loses:

| | photographs with 2+ readings | median spread | under 5° |
|---|---|---|---|
| Canny+Hough | 27 of 42 | 6.3° | 9 |
| M-LSD, letterboxed | 20 of 42 | 7.3° | 7 |
| both together | 35 of 42 | 11.3° | 4 |

(n=42, the full set, but not reproduced on 2026-09-21 and not registered:
the run that produced it wrote nothing to `results/`, and repeating it
costs about 45 minutes. By this project's own rule 2 the six numbers in
this table are unverified. The squashed-input figures in the paragraph
above - 6.3 to 5.9 degrees, 9 photographs to 13 - are unverified for the
same reason, over the same n=42.)

So M-LSD is not used. The ONNX model stays in `models/mlsd/` with its
Apache-2.0 licence, and the export is reproducible, because the finding
that OpenCV 5's new engine runs it here in tens of milliseconds is worth
keeping even though the model is not.

One caveat on all of this, added the same day: the comparison was run
before the `carriageway()` defect described in
`docs/reproducibility-2026-09-21.md` was fixed, so both arms were working
on input that had lost most of its marking pixels. A negative obtained
that way does not disprove the detector. M-LSD is untested, not beaten.

## 2026-09-23: the OpenCV calls behind each piece of evidence in the story

Every figure in `docs/story-116.md` that came from image recognition carries its
method printed under it; `docs/materials-2026-09-23.md` indexes them. This is
the same list by OpenCV call. All of it runs in `opencv-python-headless` except
EDLines, which is `cv2.ximgproc` (contrib) and is used only as a second,
independent confirmation in isolation, not in the Lambda image.

| Evidence | OpenCV calls | What each call is for | How it is checked |
|---|---|---|---|
| **Red line over the grates** (16/16 top-down frames, 1-14 cm from grate centre) — `isolation/field-2026-09-23/cv_evidence.py` | `cvtColor` (LAB), `connectedComponentsWithStats`, `fitLine` (DIST_HUBER / L2) | new red paint = LAB a* 12 above the frame median; its blocks → the line's axis; the old line (a thin strip on the frame edge) is excluded by shape | the grate must pass a bar-periodicity test (below); the result needs no scale |
| | `morphologyEx` (CLOSE 45 px, OPEN 61/151/251 px), `minAreaRect`, numpy FFT | grate gaps (grey < 45, measured 10-51 against the concrete's darkest tenth 57-92) joined into one blob, thin joints cut; near-rectangular (fill ≥ 0.75, aspect 0.5-2) | FFT peak/mean ≥ 6 along the bars, at full resolution (the one-third-resolution test inverted on 2026-09-22) |
| | `findContours`, `minEnclosingCircle` | open drain holes: darkest 6 %, circularity > 0.6, 5-25 cm | —— |
| **Red line moved 0.60-0.68 m** — `measure_redline_gap.py`, `topdown_redline_gap.py` | `HoughLinesP`, `Canny`, cross-ratio in `marking.ruler` | vanishing points of the road and of verticals; intact line's own 10 cm width as the ruler | a standard ID-1 card laid across the fresh line: 95-97 mm (`card_vs_redline.py`, `minAreaRect`) |
| **Taper before erasure 4.0-5.1:1** (2025-06 Street View) — `isolation/overlay-2025/sv_taper.py` | `createLineSegmentDetector` / `ximgproc.createEdgeDrawing` (EDLines), `fitLine`, RANSAC in `marking.phone.ransac_vp`, `vanishing_point` | two chevron edges from two independent recognisers (outermost paint per slice; EDLines) that must agree within 1 deg and 15 px | horizon from the vertical vanishing point **and** from the request's known pitch: within ~1 deg; JPEG q97/q91 and a 24 px crop leave the reading unchanged |
| **Taper after erasure ~12:1** (F40) — `isolation/taper-recheck/horizon2.py` | same as above | same | 6 of 7 perturbations 11.7-12.3; the seventh rejected by a self-check (edge A must meet the horizon at the road's vanishing point); F17 refused (non-planar, looks up the ramp) |
| **Why the published 10:1 was withdrawn** — `draw_pick.py` | `Canny`, `HoughLinesP`, RANSAC grouping | redraws what the old method picked | shows the two picked pencils mix different painted lines; readings 11.9 / 23.2 / 5.0 under q97 and an 8 px crop |
| **Every endpoint measurement** — `src/marking/phone.py:encoding_probe` | `imencode` / `imdecode` at JPEG 97/94/91 | runs the measurement on the bytes as received and three light re-encodes | reported only if they agree (red-line gap within 5 cm; taper within 10 %) |

What did **not** work and is not used: automatic SIFT registration of the 2025
Street View onto the 2026 phone photograph (`SIFT_create`, `findHomography`
USAC_MAGSAC: 15 inliers of 69, the two views cover different parts of the
chevron), and a black-hat or background-relative grate detector (both fired
on pitted concrete). Recorded in `isolation/overlay-2025/NOTES.md` and in the
comments of `cv_evidence.py`.
