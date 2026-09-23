# What this project claims, and what it does not

Written 2026-09-21. This page exists because the project's distinguishing
feature is that it refuses to answer when it cannot, and a front page that
overstates destroys exactly that. Everything below is in one of four states.

| state | meaning |
|---|---|
| **stands** | measured, registry-pinned, and the check that pins it passes |
| **withdrawn** | was published, then found not to be a measurement; must not be quoted |
| **through the defect** | measured before the `carriageway()` fix of 2026-09-21, not re-run |
| **untested** | asserted or believed, never measured on a full population |

A claim not listed here is not a claim of this project.

## How to check this page

```
/opt/anaconda3/bin/python3 scripts/check_figures.py      # must exit 0
/opt/anaconda3/bin/python3 -m pytest tests/ -q
grep -l withdrawn results/*.json
git log --oneline origin/main..HEAD                      # what a judge cannot see yet
```

`results/figure_registry.json` is the authority on every measured number, and
it is growing: it held 7 published figures at 12:55 on 2026-09-21 and 24 at
13:10, as unregistered figures in older documents were given producing
scripts. Read the file, do not trust a count quoted anywhere — including on
this page.


Its own note is the rule: *a number that is not here is not verified,
wherever else it appears.* `check_figures.py` validates the registry against
the files that produced it. **It does not validate prose**, so a document can
quote a withdrawn figure and the check will still pass. The list of documents
that currently do is at the end of this page.

---

## 1. What stands

### 1.1 The accident series at the study site

At 116 縣道 樹林中正路, within 250 m of 25.0026917, 121.4237431, from
`data.gov.tw` datasets 12197 and 13139:

| | |
|---|---|
| A2 injury accidents, 12 months before works began | 1.00 per month |
| A2 injury accidents, 2026 months 1–8, during works | 2.62 per month |
| national A2 volume, same comparison | ×1.04 |
| one-sided Poisson against 8.3 expected from the national trend | p = 0.00016 |

Registry ids `accidents_before_per_month`, `accidents_during_per_month`,
`accidents_national_control_ratio`, `accidents_poisson_p`; source
`results/accidents.json`.

**What it does not establish.** One site, and correlation with a construction
period — not with any marking geometry this system measures. No causal claim
from the accidents to the taper is made and none is supportable. The
before-and-after across the marking change of 2026-05
(`marking_change_may_2026` in the same file) is four months against three and
is not registry-pinned; it is not quoted as a result.

**A caveat on reproducibility, and it is real.** These four entries name
`docs/accidents.md` and a spatial query as their `regenerate` path, not a
script in `scripts/`. Standing rule 2 requires the producing file to be a
script. It is not, so a reader cannot regenerate these four from this
repository by running a command. They are pinned but not reproducible here.

### 1.2 The chevron's stripe angle

`results/chevron_angle.json`, from `scripts/measure_chevron.py` over four
captures of one 2025-06 Street View panorama at fov 40/60/90 and pitch
−20/−35:

| | |
|---|---|
| stripe to the boundary line | 46.41° (registry `chevron_to_boundary_deg`) |
| stripe to the road's own direction | 57.47° (registry `chevron_to_road_deg`) |
| spread of the method across the four captures | 1.97° (registry `chevron_method_spread_deg`) |

§171 says 斜四五度 — 45 degrees — and **does not say 45 degrees to what**. On
a straight section the candidate datums agree; on a taper they do not, and
tapers are where chevrons mostly are. So both readings are reported together
and neither is presented as the law's meaning.
`regulation_does_not_state_the_datum: true` is in the result file and is
pinned by the registry's `expect` block.

This measurement does **not** go through the defect of §3:
`scripts/measure_chevron.py` imports only `marking.rectify.ground_angle` and
never calls `carriageway()`. Check:
`grep -n '^from\|^import' scripts/measure_chevron.py`.

n = 4 captures of **one** panorama at one location. It is a repeatability
check on the method, not a sample of roads.

### 1.3 That the system refuses

This is a claim about behaviour rather than about a road, and it is the one
the project is actually built on. It is checkable by running the tests and by
calling the endpoint: the pipeline returns `INDETERMINATE` when its nine
encodings of the same photograph disagree more widely than the corridor they
live in, and `CANNOT_MEASURE` when the frame does not carry the measurement.
The nine cells are `QUALITIES = (80, 90, 100)` × `WORK_PX = (1000, 1400,
1800)` in `src/marking/situation.py`.

**The limitation is in the same sentence.** 32 tests pass, and standing rule 6
records that every one of them tests a refusal — not one asserts that a
genuine road photograph is measured. A system that refused everything would
pass this suite.

### 1.4 That a photograph cannot carry the pavement-height claim

New Taipei's excavation rules fix ±0.6 cm (±0.3 cm in a no-dig zone) at a
new-to-old pavement joint and name the instrument: a 3 m straightedge. This
project does not report that height difference, and `docs/claim-surface.md`
records two attempts to reach it and why both fail — shadow photometry needs
directional light and the day's measured edge-orientation coherence was 0.19,
i.e. overcast. Declining is the claim here, and it stands.

---

## 2. What is withdrawn

**Do not quote any of these.** They were published figures; their sources
carry a `withdrawn` field saying why.

| withdrawn figure | source | why |
|---|---|---|
| taper angle 10.23° ± 0.55 | `results/taper_vanishing.json` | re-encoding one photograph moves the angle 11.5–17.3°; fires in 29 of 60 runs |
| taper rate 0.1806, 29.3 km/h equivalent | same | derived from the above |
| taper 11.4°, 27.8 km/h | `results/taper_rate.json` | same cause; kept in the registry's `withdrawn_figures` |
| taper 12.1°, 26.9 km/h | same | same cause |
| rate 0.202 and the 1.07 / 1.34 / 1.78 s exposure times | `results/reaction.json` | built on a withdrawn rate |
| every "N times steeper than required" multiple | — | derived from a withdrawn rate |
| band width ≈1.9 m | `results/band_width.json` | affine rectification was degenerate |
| erasure ratios 84.1%, 25%, 16% | `results/erasure.json`, `erasure_edges.json` | the imprint test fired on half of all non-paint pixels |
| 18.3 km/h, 18.7 km/h, 42.1 km/h | `results/epochs.json`, `taper_after.json` | line groups sorted by an assumed camera heading |
| 12.8% (milling) | — | see `docs/status-2026-09-20.md` |

The taper was the project's headline. Withdrawing it was the right call and
it is also the largest single loss: it is the quantity everything downstream
was tuned against.

The ±0.55 deserves its own line, because it was a real number answering the
wrong question. It was endpoint jitter over 200 draws on one fixed line — how
precisely a chosen line can be fitted, not whether the same line would be
chosen. The second is what moves.

---

## 3. Measured through a defect, and not re-run

On 2026-09-21 at 11:43, commit `47f08bf` fixed `carriageway()`. Before it,
the function's roughness test treated chevron hatching — a row of
high-contrast stripes — as "not road" and cut it out of the region the
markings were then searched for. On the one Street View frame showing the
chevron intact, the road region and the marking mask overlapped by 0.9%
where chance alone gives 9%.

Every result produced by the served pipeline before that commit was measured
through it. That is `src/marking/situation.py`, `gate2.py`, and the scripts
that import them. Check the scope:
`grep -rln carriageway src/ scripts/ aws/ tests/`.

Specifically **not** re-run since the fix, and therefore not claims:

- **Every detector comparison.** OpenCV LSD, FastLineDetector, MSAC against
  plain RANSAC, linear parameter scaling, and M-LSD through OpenCV 5's new
  DNN engine were all compared on input that had lost most of its marking
  pixels. All five lost. **A negative obtained that way does not disprove a
  detector.** They are untested, not beaten. `docs/comparisons-2026-09-21.md`
  is the register.
- **The 42-photograph verdict split** (38 `CANNOT_MEASURE` / 3
  `INDETERMINATE` / 1 `STEEPER_THAN_REFERENCE`) in
  `docs/reproducibility-2026-09-21.md`.
- **Every routing figure** in `src/marking/route.py`'s evaluation: the
  predicates-settle-9-of-42 count and the confidence rise from the 0.22–0.36
  band to 0.91 over eleven photographs. Post-fix the grid is denser, which
  changes both what the predicates catch and what the model is shown.
- **The pavement-surface counts** in `docs/evidence.md` M8 and
  `docs/claim-surface.md` (1, 3, 2, 1 in 2025 against 5, 5, 4, 3, 3, 3, 5 in
  2026). These are clustered after the markings are *median-filtered* away,
  and the fix exists precisely because the median filter barely removed them.
  They are also not registry-pinned and name no producing script.

**The fix made the measurement worse, and that is recorded rather than
buried.** Over 42 photographs the median angle spread went from 6.3° to
14.2° and the count of photographs agreeing to within 5° went from 9 to 0.
The explanation that suggests itself — that the defect was working as an
accidental filter, discarding the chevron and leaving the long stable lane
and kerb lines — is a story and is written down as a story. None of these
numbers is registry-pinned; they are reported with their n (42) as
hypotheses, per the rule at the end of `docs/working-rules.md`.

**The deployed endpoint still runs the pre-fix image.** Anything it returns
today was measured through the defect.

---

## 4. Untested, unestablished, or asserted without a full run

- **That the taper reference binds this road.** `L = W·V²/155` comes from
  施工之交通管制守則, written by the freeway authority for national freeways.
  New Taipei's own chain — 使用道路交通維持作業規定, 設置規則,
  道路挖掘作業審查原則 — names no taper length at all. The project's own
  `docs/what-binds-this-road.md` records this as unestablished. Any
  `TAPER_TOO_STEEP` finding is measured against a document whose
  applicability here has not been shown.
- **The stripe-to-pitch ratio.** §171 fixes a 20 cm stripe and a 30 cm gap,
  so the ratio is 0.400 and needs no scale (registry
  `regulation_stripe_to_pitch_ratio`). Measured on the original of one
  photograph over 14 adjacent pairs: 0.366 ± 0.134. **Hypothesis, n = 1
  photograph, 14 pairs.** The measured value is not registry-pinned; only
  the regulation's own ratio is. It is consistent with the
  regulation and nowhere near sharp enough to detect a deviation that would
  matter; 12 of 26 candidate stripes were rejected because the extractor
  merged or split them. Worth recording because it is the first quantity
  measured directly against a number the regulation states, with no hand
  annotation and no scale.
- **The ensemble never measures the original photograph.** The originals are
  3072×4096; the grid tops out at 1800 px. The regulation is in centimetres:
  at 20 m a 10 cm red line is 14.2 px in the original and the ±6 mm width
  tolerance is 0.85 px (registry `red_line_px_at_20m_original`,
  `width_tolerance_px_at_20m_original`, from `scripts/pixel_budget.py`). A
  conformity check against those numbers is only conceivably possible on the
  original and in the near field, and it is not being taken. This is an open
  design question, not a result.
- **No held-out evaluation, and no ground truth for the taper.** `AGENTS.md`
  states the evaluation rule — beat predicting the training mean, on subjects
  not fitted on — and it has not been applied to any measurement here,
  because no measured truth exists for the site. What exists is a
  reproducibility study, which is a weaker and different thing.
- **The routing module is not connected.** `src/marking/route.py` is imported
  by nothing: `grep -rn route_ensemble src/ aws/ scripts/ tests/` returns only
  the file itself. The deployed function has no model key. As shipped, no
  vision result drives any action.
- **The routing decision is not stable.** One photograph returned confidence
  0.65 on one run and 0.59 on the next, either side of the threshold that
  decides whether a person is asked. The measurement is averaged over nine
  encodings; the decision on top of it is averaged over nothing.
- **Arm dispatch is verified on the wrong host.**
  `cv2.getCPUFeaturesLine()` returning `NEON FP16 NEON_DOTPROD NEON_FP16
  *NEON_BF16` is registry-pinned (`cv5_cpu_features_line`) — and the run that
  produced it was on the local Darwin arm64 machine, not on Graviton. Same
  package version, different wheel. The deployed function does not report its
  CPU feature line, so NEON dispatch inside Lambda is inferred from the
  architecture flag, not read there.
- **No benchmark against any baseline exists.** None has been run.
- **Whether this build is "COOL" at all.** The image installs the stock
  `opencv-python-headless` wheel from PyPI. `docs/status-2026-09-20.md`
  records two irreconcilable accounts of what the Cloud-Optimized OpenCV
  Library is. Unsettled.
- **The two motivating figures on the sidewalk problem — a 0.252 m mean
  absolute error, and 34.6% of real sidewalks within half a metre of the
  1.5 m threshold — name no publication anywhere in this repository**, and
  the dataset that would let the second be recomputed (Zenodo 22699523) is
  not present in `data/`. They were in the README until today and are removed
  from it. Until a citation is added they are unsupported.

---

## 5. What is deliberately not claimed

- That any particular road is in breach of anything. A verdict from this
  system is not an inspection, binds nobody, and in the taper's case is
  measured against a document that may not apply.
- That the method generalises. It has been run on one road on one afternoon
  and on Street View captures of the same place.
- That classical CV beats a learned detector here. Five comparisons were run
  and all five are void (§3). The argument for Canny and Hough in
  `docs/thesis.md` is an argument from auditability, not a measured win.
- That anyone uses this. No agency runs it; the endpoint has no caller other
  than its author.

---

## 6. Documents that currently contradict this page

Found on 2026-09-21 by reading the set. `check_figures.py` validates the
registry, not prose, so none of these fails a check. They are listed so a
reader knows which document to distrust, and they are **not** fixed here —
this page changes nothing outside itself.

| document | what it says | what is the case |
|---|---|---|
| `docs/evidence.md` §四 M1–M3 | presents 10.23° ± 0.55, rate 0.1806 and 29.3 km/h as current measurements | all three are withdrawn (§2); the same file's §六 lists other withdrawn numbers but not these |
| `docs/thesis.md` evidence table and §120 | quotes 11.4° and 27.8 km/h | both are in `withdrawn_figures` in the registry. The file does carry a bracketed withdrawal note after the table; the numbers above it are unmarked |
| `docs/timeline-116.md` lines 86, 97 | quotes 11.4°, rate 0.20, 27.8 km/h | withdrawn |
| `docs/thesis.md` OpenCV table | lists `cv2.dnn` segmentation, `findContours` with convexity defects, `warpPerspective`, and Otsu thresholding as what OpenCV does here | none of `findContours`, `convexityDefects` or a segmentation `dnn` call appears anywhere in `src/` or `scripts/`; `warpPerspective` and `THRESH_OTSU` appear only in `scripts/`, not in the served path. The served mask is `cv2.filter2D` with a dark-light-dark kernel (`src/marking/extract.py`). That table describes intent |
| `docs/what-changed-2026-09-21.md` | "Every measurement in this project was made through that" | too broad. `scripts/measure_chevron.py` never calls `carriageway()`, and `results/accidents.json` uses no imagery. Most registered figures are unaffected; the scope is `grep -rln carriageway src/ scripts/ aws/` |
| `docs/reproducibility-2026-09-21.md` | "The gate is now `roi_frac > 0.75`" | `src/marking/situation.py` has `ROI_FRAC_MAX = 0.87`, recalibrated by commit `4a72826` after the fix |
| `docs/deployment.md` lines 71–72 | 2048 MB, image `v2` | `docs/competition.md` §7 records 3008 MB and `v11`. **Not re-derived here** — the AWS CLI in this session has no valid credentials, so this is a disagreement between two documents, not a verdict on which is right |
| `evidence/field-2026-09-20/README.md` | "201 MB for the set. The largest single file is 7.5 MB" | measured: 42 files, 210,300,377 bytes, largest 7,899,011 bytes |
| `evidence/field-2026-09-20/README.md` | the manifest carries "the SHA-256 of the untouched original and of the published copy, both sizes and both byte counts", and gives a snippet reading `published_sha256` | `MANIFEST.csv` columns are `no, file, captured, size, f35_mm, bytes, sha256`. That snippet raises `KeyError` as written. The first snippet on the page works: 0 of 42 differ |
| `docs/competition.md` §6, §10 | `origin/main` is five commits behind local `a5e6f24` | seven, as of 13:05 on 2026-09-21. `git ls-remote origin main` → `a429e8c`; `git log --oneline origin/main..HEAD` → 7 |
| `docs/competition.md` §6 | `scripts/check_stage.sh` "has been replaced in the working tree by a two-line shim" | no longer true. The working-tree file runs the project's own refusals and then chains the workspace gate, and `tests/test_hook_chain.py` is staged to fail if either half is missing. Still uncommitted |
| the deployed endpoint's `GET` | documents five finding codes | `src/marking/situation.py` can emit six. `CARRIAGEWAY_OCCUPIED` is missing from the endpoint's own description |

One more, recorded because it is the check working rather than failing: at
13:00:13 on 2026-09-21 `results/figure_registry.json` was edited to say 46.42
where `results/chevron_angle.json` says 46.41, and `check_figures.py` refused
with *1 of 7 published figures no longer stand*. Fifteen seconds later the
registry was corrected and the check passed again. The source file was never
touched. That is the mechanism doing its job.
