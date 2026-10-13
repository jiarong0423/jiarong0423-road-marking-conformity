# Technical report

**Seven drain grates on County Road 116: measuring one road's markings from a phone photo, with OpenCV 5 on AWS**

Entry for the OpenCV AI Competition 2026. One author. 23 September 2026; revised 14 October 2026.

Video: https://youtu.be/UkINgvk1z-E · Code and evidence: https://github.com/jiarong0423/jiarong0423-road-marking-conformity

---

## 1. Problem

On County Road 116 in Shulin, New Taipei, the lane approaching a bridge is squeezed from both sides along one short stretch:

- a double white line forbids changing lanes,
- a painted island narrows the lane from the left,
- on the right, a drain strip with seven steel grates runs the whole way, and in 2026 the red no-stopping line was repainted about 0.65 m further out, onto that strip.

None of these is obviously illegal on its own. Each sits near a limit that is written down somewhere: a marking rule, a design table, a statute on manhole covers. Checking any of them today means sending someone with a tape measure. The question this project asks is narrower than "is this road safe": **from ordinary phone photographs, what can be measured against those written limits, how sure can we be, and what should happen next?**

## 2. Users

- **A rider** who uses the road and wants to know whether what they feel can be shown, and what to ask for.
- **A reviewer at a traffic department** who receives that request and needs numbers with their method and uncertainty, not adjectives.

The output is written for both: a plain-language scenario, itemised findings with the rule behind each, and a list of documents to request.

## 3. Architecture

![Architecture](figures/architecture.png)

**Online** (`aws/handler.py` → `src/marking/situation.py:assess`), on AWS Lambda (arm64 container, `opencv-python-headless==5.0.0.93`) behind an API Gateway HTTP API:

1. **Is it a road?** The road region must cover at least 30% of the frame (random noise 0.0%). Otherwise the system measures nothing and asks for a retake.
2. **First-pass checks** (double white/yellow lines, kerbside red line, works fencing, patched surface, a rough taper ensemble). These point to regions worth opening; their counts are not cited as evidence.
3. **Measurements** (`src/marking/phone.py`): the red-line gap and the island's taper ratio (Section 4).
4. **Four-encoding gate** (`phone.encoding_probe`): each measurement runs on the photo as received and on JPEG re-encodes at quality 97, 94 and 91, and is reported only if at least three of the four measure and agree (red line within 5 cm, taper within 10%).
5. **Site notes**: the published numbers for this stretch are attached to every response, marked as not measured from the photo sent. They are generated from `results/` by `scripts/build_site_dossier.py`; a test fails if they drift.
6. **Next actions** (`src/marking/actions.py`): which document to request from which office, which box in the photo to open, and what the photo cannot answer. Document requests and "open this box" actions appear only when a finding in the photo calls for them, and each carries that finding. Two notes are always included: what a photo cannot answer, and that grates are not detected online.

**Offline** (`isolation/`): the evidence pipeline behind the story's figures. Every figure made by image recognition has its method printed under it and is indexed in [`materials-2026-09-23.md`](materials-2026-09-23.md).

## 4. Implementation

### 4.1 Red line over the grates (`isolation/field-2026-09-23/cv_evidence.py`)

| Step | OpenCV | Detail |
|---|---|---|
| Grate | `morphologyEx` (close 45 px, open 61/151/251 px), `connectedComponentsWithStats`, `minAreaRect` | gap pixels grey < 45 (measured: gaps 10–51, the concrete's darkest tenth 57–92); near-rectangular (fill ≥ 0.75, aspect 0.5–2) |
| Grate check | numpy FFT on row/column means | bar periodicity peak/mean ≥ 6, at full resolution (an earlier detector inverted this test at one-third resolution) |
| New red line | `cvtColor` to LAB, `connectedComponentsWithStats`, `fitLine` | a* at least 12 above the frame median; strips touching the frame edge or thinner than 1:6 are the old line and are excluded |
| Open holes | `findContours`, `minEnclosingCircle` | darkest 6%, circularity > 0.6, diameter 5–25 cm |

Result: in **all 16** top-down photos of 23 September (grates 1–6; grate 7 has no top-down photo) the new red line's axis crosses the grate, 1.0–14.3 cm from its centre (`results/grate_crossings_2026-09-23.json`, from `isolation/field-2026-09-23/cv_evidence.py`). This needs no scale.

### 4.2 The ruler, and the red-line gap (`src/marking/phone.py:redline_gap`)

A red no-stopping line is 10 cm wide by regulation (§169). The gap from the intact line's inner edge to the worn line's centre is measured with a cross-ratio against the vanishing point of the cross-road direction, using that 10 cm as the ruler. No camera pitch, roll or height is needed. The ruler was checked with an ID-1 card (85.60 mm) laid across the fresh paint: **95–97 mm** on P55 and P56; P59's reading failed (`isolation/field-2026-09-23/card_vs_redline.json`).

Result: **0.63–0.68 m** (the median gap, intact line's inner edge to the worn line's centre) on three photos of 20 September (F30–F32); single stations range 0.61–0.72 m. The card check was made at grate 7 on 23 September, a different place. These gaps use the legal 10 cm; if the line is really about 96 mm wide, each is about 4% smaller (about 0.61–0.65 m). Top-down shots of 23 September were also tried; their saved output is flagged as not verified to be square to the road, so they are not used here.

### 4.3 The island's taper (`isolation/taper-recheck/`)

The taper ratio is the ground angle between the island's two edges. In the offline analysis (not in the endpoint) two independent recognisers must agree on each edge: outermost white paint per 12 px slice with a RANSAC line, and EDLines (`cv2.ximgproc`), within 1° and 15 px. The horizon comes from the vertical vanishing point (poles, walls). A self-check requires the lane-side edge to meet the horizon at the road's own vanishing point.

| | Ratio | Reference only: 5:1 at 30 km/h in design table 4.2.7 (written for through-lane shifts at turning lanes) |
|---|---|---|
| Today (phone, F40, September 2026) | about 12 : 1 (11.7–12.3) | gentler than the reference |
| Near the cone (phone, P64, September 2026; top-down view, section 4.5) | about 6 : 1 (outer edge at 9.0°, 8.5–9.4°) | just gentler than the reference |

The two are different places on the island: it opens more steeply near the cone.


### 4.4 The island before it was painted over: what OpenCV did, what a person did, what is not done

No Street View is used for this. Inputs: field photograph F17 (20 September 2026), the taper measured today on F40, and one human mark. Script `scripts/erasure_ratio.py`, then `scripts/before_taper.py`; the erasure numbers are in `results/before_taper.json`, the slanted end edge's in `results/dash_ruler_P64.json` (`scripts/dash_ruler.py`), all in the figure registry. The hand-drawn edge is two points in F17's pixels, `data/annotations/user_line_F17.npy`, published so the erasure can be re-run.

| | |
|---|---|
| **OpenCV 5 did** | the paint mask (LAB colour, Gaussian blur, morphological opening), connected components for the far edge line and the stripes, line fits, and a cross-ratio against the vanishing point that turns each stripe's image distances into ground distances without a focal length |
| **A person did** | drew the chevron's former edge on the photograph (OpenCV could not find it: seven automatic attempts are recorded in the author's notes), and stated that the rough surface beside it is milled carriageway |
| **Result** | of the island's old width, about 35% is still painted and about 65% was painted over (median of 19 clean stripes, sd 6.5%; of 28 stripes, 5 were excluded as outliers and 4 more because they overran the band), measured in the full-width section on F17 (`results/before_taper.json`). An old taper is **not** given: the share was not shown to be the same at the island's start |
| **Milled surface** | the photograph shows road beyond the drawn edge for at least 2.6 island-widths, to the image edge: a lower bound on how much was milled, not a measurement of milled asphalt |
| **Not done** | detecting the former edge; detecting milled asphalt (a texture test separated nothing); the far edge of the milled surface (the photograph ends first); any distance in metres (nothing of known size is in the frame) |
| **Slanted end (old)** | the faint slanted edge from the corner where the lane-side edge line stops back to the base of the bridge wall is the island's **old** far end, now painted over (section 4.5). Measured on `IMG_20260923_063437.jpg` with the lane line's dashes as the ruler (§182: 4 m dash + 6 m gap; `scripts/dash_ruler.py`): about **11 m** long (8 to 15 m) at about **14 degrees** to the road axis (12 to 17 degrees). Ranges are the 10th to 90th percentile of 400 error draws (dash centres 2 px, corner 6 px, wall end 10 px). Not asserted to be the lane-shift taper of table 4.2.7. An earlier estimate (45 to 49 and 60 to 71 degrees) used a vanishing point read off hand-traced lines and is withdrawn |
| **Assumption** | an old taper would need the painted-over share to be the same along the whole island. A rough look at P62 (image pixels, not perspective-corrected, not saved as a result) suggested it is not, so no old taper is stated. The start point has not been located on a field photograph |
| **Open** | the drawn edge may be the milling boundary rather than the chevron's former edge; moving it by 20 px moves the painted-over share between 55% and 68% |

The sentence that scooters and cars would both ride partly over the painted chevrons during the works is the rider's own observation, not a measurement.

### 4.5 Top-down view of P64: the old far end, and the lane everyone merges into (`scripts/erased_triangle.py`)

Standing on the road, the island's far end is foreshortened to a sliver, so the old and new paint cannot be compared in the photograph. OpenCV reprojects the road plane of P64 to a top-down view, with the lane line's dashes as the ruler, and everything below is measured there (`results/erased_triangle_P64.json`, ±10% from the ruler).

| | |
|---|---|
| **OpenCV 5 did** | `fitLine` on the dash centres for the road direction; `getPerspectiveTransform` and `warpPerspective` for the top-down view; LAB lightness and `adaptiveThreshold` for the paint; `HoughLinesP` for the lane-side edge line, a lane dash (4.1 m, which checks the 4 m ruler) and the island's outer edge; `connectedComponentsWithStats` to mask the painted arrow; then, on those OpenCV masks and images, the share of paint per row to find where today's stripes stop and line brightness to tell today's edge from the old one; `contourArea` for the triangle; `perspectiveTransform`, `fillPoly` and `polylines` to draw it back on the photograph |
| **A person did** | the dash centres and the old edge's two ends (confirmed by the owner on the photograph); the line the old triangle's tip touches (X = −4.3 m, confirmed by the owner; OpenCV's wall-side line is at −4.54 m); the reading that the faint diagonal is the old edge and that the arrow is painted on erased stripes |
| **The island opens** | before the cone, the outer edge opens at **9.0°** to the road (8.5–9.4°, 59 Hough segments, length-weighted): about **6 : 1**. The lane-side edge is straight |
| **Today's end** | past the cone the stripes run on beside the bridge wall and stop at **30 m** from the camera (the paint share falls to zero and stays there; the same at a second threshold) |
| **The old end, painted over** | a triangle from there to where the old slanted edge meets the wall: about **8.5 m** along the wall, **2.1 m** wide at its base, about **8.9 m²**. The old edge reads 12.4 on the brightness scale, today's edge line 30.4. The left lane's straight-ahead arrow is painted on it |
| **After the island** | two lanes; the right one is painted to merge left. The left lane, which everyone merges into, is **3.13 m** (wall-side line to lane line, median over 30–39 m). Before the merge the right lane is 4.05 m to the asphalt edge; beyond it is the drain strip with the grates |
| **Side by side, after the merge** | a typical car (1.78 m) + 0.5 m + a scooter (0.75 m) needs 3.03 m, leaving about 0.1 m, inside the error; a bus or truck (2.5 m) is about 0.6 m short (`results/width_budget.json`). The 3.03 m sum is mine, using §101's 0.5 m clearance; it is not a lane-width rule |
| **Not measured** | wet grip, night visibility, and where the right lane finally ends (beyond the photograph). In rain or at night the risk is the rider's experience plus published reference values (2.5 s to react; at least 3.65 s of preview at night, `docs/evidence.md` M5) |

![The old end, painted over, in P64's top-down view](figures/erased-triangle-P64-topdown.jpg)

## 5. Evaluation, including what failed

**A published number was withdrawn.** The project first reported the taper as "about 10:1 (9.2–11.9)". On 23 September the measurement was repeated on 13 photos under seven variants (the original, three JPEG qualities, three crops). The original method produced a reading on 7 of 91 runs, ranging 5.0–23.2. Drawing what it picked showed why: the two "edges" it measured were mixtures of different painted lines grouped by a shared vanishing point, not the island's two edges (`isolation/taper-recheck/f40_picks.jpg`). The 10:1 is withdrawn. The consensus method in 4.3 replaced it in the offline analysis. The online endpoint still runs the older single-method check (`phone.taper_427`, Hough lines and a vanishing point); what changed there is the four-encoding gate, so a number that moves with a re-save is not reported.

**Refusals are counted, not hidden.** F17 (looking up the bridge ramp) fails the self-check on every perturbation and is refused: the ground there is not a plane. On F40, one of seven perturbations fails the self-check and is dropped.

**Perturbation results** (F40, after repainting): as received 12.1; JPEG 97, 91: 11.8, 11.7; crops of 8, 16, 24 px: 12.3, 12.2, 11.7. One run rejected (JPEG 94: 8.4, self-check off by 29°).

**Other things tried and dropped**, each recorded in the notes: SIFT registration of an earlier view onto the phone photos (too few inliers), LSD in place of Hough (less stable), the horizon from the stripe pattern (stripes too short), black-hat and background-relative grate finders (fooled by rough concrete).

**Provenance.** `results/figure_registry.json` pins each published figure to the file and key that produced it; `scripts/check_figures.py` checks every registered figure against its source and must report that all match; the test suite must pass in full.

**What is not measured.** The step between grate and road and its skid resistance (the Highway Act §72 sets ±0.6 cm for the flatness of repaired pavement, checked with a 3 m straightedge, and a skid-resistance floor for covers; measuring either needs a straightedge and a pendulum tester on site), anything at night, and the lane width a scooter can actually use. No figure has field-measured ground truth; the card is the only physical reference.

## 6. Deployment and reproduction

```sh
pip install -r requirements.txt                                    # opencv-python 5.0.0.93, numpy 2.4.4, scipy 1.17.1
python3 -B -m pytest -q -p no:cacheprovider                        # all pass
python3 -B scripts/check_figures.py                                # every figure vs. its source
AWS_REGION=ap-southeast-2 ACCOUNT=<account> ./aws/build-and-push.sh v16
```

The container pins `opencv-python-headless==5.0.0.93` and `numpy==2.5.3` (`aws/Dockerfile`). The local interpreter that produced `results/` has numpy 2.4.4; the container was tested separately with 2.5.3 (below).

**Measured in the v12 container** (arm64, 2 CPUs, locally): a 2000 px photo takes 14.3 s and the new measurements refuse (they need full resolution); a full-resolution photo (JPEG 90, 2.2 MB) takes 52.5 s and returns the red-line gap 0.668 m on F31. That exceeds API Gateway's 30 s limit. A 10 GB memory request (more vCPUs) was refused, so the live function runs at 3008 MB, the account's cap, and full-size photos go through the Function URL instead (below). Error paths return clear answers: malformed JSON or a missing photo 400, over 3 MB 413, a non-road photo `NOT_A_ROAD_PHOTOGRAPH`. Since 14 October: a second door, a Lambda Function URL (`https://cjy6l22ni2mh5gtc6wgjltz7bu0ehjjb.lambda-url.ap-southeast-2.on.aws/`) with no 30 s limit; on image v14 a full-size F31 took **145.5 s** live (3008 MB, the account's cap) and returned the red-line gap **0.668 m**, the same as the local container; images v15 and v16, live since, change only the interface and site text. Before that, from 23 September to 14 October, image v13 ran only behind API Gateway: a 2000 px photo took 25.6 s and the new measurements refused, and a full-resolution photo timed out. POST requires an access token (`x-access-token`), given to judges with the submission; the API is throttled to 1 request/s with bursts of 3, and a $5 budget alert is set. See [`deployment.md`](deployment.md).

## 7. Regulations used

The Chinese originals are quoted word for word from the national law database in [`evidence.md`](evidence.md); the database states that where English and Chinese differ, the Chinese prevails. Highway Act §72 has an official English translation, which the story quotes; the other clauses have none that I could find, and their English wording here and in the story is my own, unofficial translation.

- Road Traffic Signs, Markings and Signals Rules §169 (red line on the kerb; 10 cm wide), §183 (a red line stands in for the road edge line), §167 (no lane change)
- Urban Road and Ancillary Works Design Standard §2(1) (a lane is what markings delimit)
- Urban Road Design Specification, table 4.2.7 (through-lane shift at turning lanes: 5:1 at 30 km/h, 16:1 at 50 km/h), used only as a reference
- Highway Act §72(4) (repaired pavement flat within ±0.6 cm on a 3 m straightedge; skid resistance not below the ministry's standard); whether it covers these grates is not established
- New Taipei road excavation review rules 6.0 (patch joints ±0.6 cm)

Two clauses quoted by an AI assistant during this work (Design Standard §14 and §16 on gutters and flush covers) do not exist in the official text and are not used.

## 8. Perceive, decide, act (Agentic Vision)

![Perceive, decide, act](figures/agent-workflow.png)

The vision result decides what the system returns next (`src/marking/actions.py`, called inside `assess()`). It is a deterministic rule set over the OpenCV output, not a learned or LLM agent; the loop closes through a person, who decides whether to retake the photo, request a document or open a flagged box.

**Trace** (`isolation/agentic/trace.py`, 30 km/h, the endpoint's own function):

| Input | What OpenCV found | Next actions produced |
|---|---|---|
| Random noise | not a road | RETAKE only |
| F31, full size | two red lines, gap 0.673 m (MEASURED) | request marking plans; request drain records; which distances need a tape |
| F31, the same photo at 2000 px | red-line gap CANNOT_MEASURE; patched surface | request traffic plan; check dig permit; no distance can be answered from this photo |
| F40, full size | double white line; patched surface | request traffic plan and marking plans; check dig permit; HUMAN_LOOK at the line's box |

The F31 gap reads 0.673 m in this trace, 0.668 m from the local container and 0.669 m from the measurement script: three separate runs that differ in the third decimal, all inside 0.63–0.68 m.

The same scene at two resolutions gives different next steps, because the measurement held at one and not the other: the vision output, not a fixed script, decides.

**Failure handling and observability.** A non-road photo stops at the first gate and asks for a retake. A measurement that moves when the photo is re-saved is refused with its reason, and the refusal becomes a CANNOT_FROM_PHOTO action instead of a number. Every action carries `why` (the finding that caused it), `basis` (the rule) and `to` (who acts). Document requests and HUMAN_LOOK appear only when a finding calls for them; two notes (what a photo cannot answer, and that grates are not detected online) are always added. The system files nothing and contacts no one.

**Evaluation on 20 evidence photos** (`isolation/agentic/evaluate.py 10`: every k-th photo, 10 from each field batch, full resolution, 30 km/h):

| | Result |
|---|---|
| Photos assessed (none refused as non-road) | 20 / 20 |
| Photos with a document request / a record check / HUMAN_LOOK | 15 / 15 / 16 of 20 (`results/agentic_evaluate_2026-09-23.json`) |
| Every action carries a `why` | yes |
| Distinct sets of next actions produced | 4 |
| Red-line gap or taper reported | 0 / 20 |

What this shows and does not: the decision step follows the vision output exactly, and different photos lead to different next steps. It does **not** show the findings themselves are correct: the first-pass red-line detector fires on 16 of 20, and opened by eye it has often been wrong on earlier frames, which is why its action is "HUMAN_LOOK: open this box" and never a conclusion. None of the 20 sampled photos is one of the three frames (F30–F32) where the red-line gap was measured, and the close-ups of 23 September are not the geometry that measurement is built for, so the new measurements refuse on all 20; they are demonstrated in the trace above instead. Run time on this machine with four photos in parallel: median 117 s per photo (a single photo alone takes about 36 s). The full 106-photo run was stopped after 34 minutes and is not reported.

## 9. Responsible use

- **It describes, it does not accuse.** The output never says a rule was broken. It reports what was measured, against which written limit, how sure the measurement is, and what it could not measure; deciding which rule applies is left to the documents it asks for.
- **It refuses rather than guesses.** A photo that is not a road gets no measurement. A measurement that changes when the photo is re-saved is not reported. Every refusal says why.
- **Privacy.** Uploaded photos are processed in memory and not stored; nothing from a request is written to logs beyond Lambda's standard request record. In the published evidence, licence plates are covered (82 boxes on 26 photos), no photo carries a GPS fix, and close-ups show pavement only.
- **Data rights.** Google Street View was used only privately, to compare with the author's own photos while working. Google's terms don't allow sharing Street View images or data derived from them, so nothing from it is published in this report or repository: no image, no distance along the road, and no before-repainting figure (those were withdrawn on 2026-10-13). The schematic shows no distances along the road. The published photos are the author's own.
- **Operation.** POST requires an access token on both doors; API Gateway is throttled (1 request/s, bursts of 3), and the function's reserved concurrency of 3 caps the Function URL; the account's Lambda concurrency limit was 10 when this was written (raised to 1000 on 13 October 2026); logs are kept 14 days; a budget alert is set. The token is not in the repository.
- **Human in the loop.** The system's last step is a list of documents for a person to request and boxes for a person to look at; it takes no action on its own.

## 10. Limitations and data rights

- One road, one author, 106 photos. The method is general; the evidence is local.
- The before-repainting taper was measured on Google Street View imagery and has been withdrawn (2026-10-13): Google's terms prohibit sharing screenshots or data derived from Street View. The schematic shows no distances along the road.
- 26 photos have licence plates covered (82 boxes); no photo carries a GPS fix.
- The taper after repainting rests on one photo at each place: F40 (about 12:1) and P64 near the cone (about 6:1). The P64 measurements use one photo, a ruler good to about ±10%, and points given by a person (section 4.5).
- Which red line is official, and which design speed applies, are questions for documents. The system's last step is to request them.
