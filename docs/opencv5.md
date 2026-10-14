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

Re-derived: `python3 scripts/opencv5_build.py`. Every
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
changes its type and detects nothing new. There is no stereo pair and no
point cloud; feature matching was tried on 2026-10-14 (last section). Adding those calls would put OpenCV 5
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
not assumed. **It is not in the pipeline:** it lost the comparison below, and that comparison turned out not to be a fair test (see the caveat at the end).

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
across re-encodings of one photograph (nine in the test below; the endpoint now uses four). A line detector that is more
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
the author's notes was fixed, so both arms were working
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
| **Red line over the grates** (all 16 top-down photos of grates 1–6, 1.0–14.3 cm from grate centre) — `isolation/field-2026-09-23/cv_evidence.py` | `cvtColor` (LAB), `connectedComponentsWithStats`, `fitLine` (DIST_HUBER / L2) | new red paint = LAB a* 12 above the frame median; its blocks → the line's axis; the old line (a thin strip on the frame edge) is excluded by shape | the grate must pass a bar-periodicity test (below); the result needs no scale |
| | `morphologyEx` (CLOSE 45 px, OPEN 61/151/251 px), `minAreaRect`, numpy FFT | grate gaps (grey < 45, measured 10-51 against the concrete's darkest tenth 57-92) joined into one blob, thin joints cut; near-rectangular (fill ≥ 0.75, aspect 0.5-2) | FFT peak/mean ≥ 6 along the bars, at full resolution (the one-third-resolution test inverted on 2026-09-22) |
| | `findContours`, `minEnclosingCircle` | open drain holes: darkest 6 %, circularity > 0.6, 5-25 cm | —— |
| **Red line moved 0.63-0.68 m** (F30-F32) — `measure_redline_gap.py` | `HoughLinesP`, `Canny`, cross-ratio in `marking.ruler` | vanishing points of the road and of verticals; intact line's own 10 cm width as the ruler | a standard ID-1 card laid across the fresh line: 95-97 mm (`card_vs_redline.py`, `minAreaRect`) |
| **Taper before erasure** | withdrawn 2026-10-13: it was measured on Street View, whose terms do not allow sharing derived data | — |
| **Taper after erasure ~12:1** (F40, offline only) — `isolation/taper-recheck/consensus.py`, `horizon2.py` | outermost paint per slice + RANSAC, and EDLines (`cv2.ximgproc`); both must agree | horizon from vertical vanishing point | 6 of 7 perturbations 11.7-12.3; the seventh rejected by a self-check (edge A must meet the horizon at the road's vanishing point); F17 refused (non-planar, looks up the ramp) |
| **The old far end, painted over, and the merged lane** (P64, top-down view) — `scripts/erased_triangle.py` | `fitLine`, `getPerspectiveTransform`, `warpPerspective`, `cvtColor` (LAB), `adaptiveThreshold`, `HoughLinesP`, `connectedComponentsWithStats`, `contourArea`, `perspectiveTransform`, `fillPoly`, `polylines` | the top-down view is what makes old and new comparable at all; a lane dash found by Hough reads 4.1 m against §182's 4 m | island opens at 9.0° (about 6:1) before the cone; today's stripes stop 8.5 m short of the old end (a 2.1 m, 8.9 m² triangle, painted over); the lane everyone merges into is 3.13 m. A person gave the dash centres, the old edge's two ends and the tip line |
| **Why the published 10:1 was withdrawn** — `draw_pick.py` | `Canny`, `HoughLinesP`, RANSAC grouping | redraws what the old method picked | shows the two picked pencils mix different painted lines; readings 11.9 / 23.2 / 5.0 under q97 and an 8 px crop |
| **Every endpoint measurement** — `src/marking/phone.py:encoding_probe` | `imencode` / `imdecode` at JPEG 97/94/91 | runs the measurement on the bytes as received and three light re-encodes | reported only if at least 3 of the 4 measure and agree (red-line gap within 5 cm; taper within 10 %) |

What did **not** work and is not used: automatic SIFT registration of an earlier
view onto the 2026 phone photograph (`SIFT_create`, `findHomography`
USAC_MAGSAC: too few inliers), and a black-hat or background-relative grate detector (both fired
on pitted concrete). Recorded in the author's notes and in the
comments of `cv_evidence.py`.

## 2026-10-14: OpenCV 5's new matchers, tried on my own photographs

The question was whether OpenCV 5's ALIKED keypoints with its LightGlue matcher, or its
new multi-scale ECC alignment, could register two of my photographs on the road surface,
so that one thing could be measured twice. The one measurement that most needs it is the
island's old end: only P64 sees it from a usable angle. F34 and F35 (20 September) show the
same spot from the kerb beside the cone. The photographs taken further back on 23 September
(P62, P63) were checked first and dropped: there, the old end is a few dozen pixels.

`scripts/opencv5_matchers_trial.py`, written to `results/opencv5_matchers_trial.json`.
ALIKED and LightGlue run as ONNX through the new DNN engine. The weights are the two files
OpenCV's own tests use (`scripts/fetch_aliked.sh` checks their SHA-1; ALIKED is BSD-3-Clause,
LightGlue Apache-2.0). Homographies from matches use MAGSAC. ECC starts from the identity on
quarter-size images. Inliers on the road are those below the horizon. "Disagreement" is the
median distance between where two methods put the same grid of road points.

| pair | kind | SIFT inliers (on road) | ALIKED+LightGlue inliers (on road) | ECC correlation | SIFT vs LightGlue, px | SIFT vs ECC, px |
|---|---|---|---|---|---|---|
| F30 / F31 | same direction, 1 s apart | 1939 (640) | 510 (104) | 0.995 | 2.9 | 2.2 |
| F31 / F32 | same direction, 1 s apart | 1859 (516) | 615 (185) | 0.994 | 1.5 | 2.4 |
| F30 / F32 | same direction, 2 s apart | 1617 (418) | 525 (122) | 0.993 | 7.4 | 8.9 |
| P64 / F34 | across views, 3 days apart | 9 (0) | 6 (0) | 0.73 | 1727 | 1821 |
| P64 / F35 | across views, 3 days apart | 8 (0) | 7 (1) | 0.70 | 4710 | 3607 |

What it shows:

- **Across views, nothing registers.** All three methods fail, the new ones included: no
  inliers on the road, and the methods put the same points thousands of pixels apart. The
  angle between the two views, three days of different light and the repeating chevrons are
  too much. So the old end stays measured on one photograph, and the docs keep saying so.
- **ECC said it had converged when it had not.** On the across-view pairs it returned a
  correlation of 0.70-0.73 and no error; the comparison with the other two methods shows
  the result is meaningless. So ECC's convergence cannot be trusted on its own. Its
  correlation, though, did separate the cases: 0.70-0.73 across views against
  0.993-0.995 a second apart. (Revised the same day: this sentence first said the
  correlation was not enough either. On these pairs it is; see the next section for how
  the pipeline uses it and what guards it.)
- **A second apart, all three agree** to within 1.5-8.9 px on the road. Here SIFT finds about
  four times as many road inliers as ALIKED+LightGlue, so the new matcher buys nothing on
  these photographs. ECC took 0.0-0.1 s against 2.4-3.1 s for SIFT (this machine, one run).
  That speed is the one finding worth keeping: it lets the online service line up a
  burst of photographs and check that the red-line gap reads the same on each. Built the
  same day; next section.

ALIKED's network takes a fixed 640 x 640 input; asking for a larger one fails inside the
model. Cutting the photograph into tiles raised the road inliers across views only to 4-11
(a scratch test, not in the script), still too few to trust.

ALIKED and LightGlue are not used in the pipeline. Nothing here changes a published
measurement.

## 2026-10-14: ECC in the pipeline, for a burst

`src/marking/burst.py`, called by `aws/handler.py` after the first measurement. When the
red-line gap is refused on the photo sent but the red-line pair was seen by at least one
re-encoding, or when it was measured and can be confirmed, the photos taken within 3 s are
found by capture time (or taken from the caller), fetched, and each is registered to the
first with `cv2.findTransformECCMultiScale` (`cv2.ECCParameters`, homography, 768 px wide
greys). A photo is used only if the correlation reaches 0.90: convergence alone is not a
gate, for the reason above. The 0.90 is set on few pairs (0.70-0.75 for another view of the spot or another place,
0.993-0.996 for the same view, in this trial and in `results/agentic_burst_2026-10-14.json`),
so it is not the only guard: the gap is reported only if two or more photos measure it and
all read within 5 cm of each other. At most 2 extra photos are used, each only if about 45 s
of the function's 300 s remain; a gap measured on the first photo stands when no other
photo can confirm it. Registration takes 0.0-0.3 s a photo on this machine.

| case | first photo | ECC correlation | gaps | decision |
|---|---|---|---|---|
| F31 sent whole | measured 0.673 m | F30 0.996, F32 0.994 | 0.673, 0.680, 0.635 | confirmed, 0.673 m |
| F31 at 2000 px, F30 and F32 attached | refused | F30 0.996, F32 0.994 | 0.680, 0.635 | measured across the burst, 0.657 m |
| F31 at 2000 px, P64 and F30 attached | refused | P64 0.753 (refused), F30 0.996 | 0.680 | too few photos: retake asked for |
