> **Historical working note (content from 2026-09-22).** Numbers and status here may be superseded. The current account is [`technical-report.md`](technical-report.md); withdrawn figures are listed there.

# The corrected measurement pipeline

2026-09-21. Written after `docs/what-changed-2026-09-21.md` established that
every measurement in this project was made through a region step that
removed the object under inspection.

Nothing here is a measurement. Every number is arithmetic from first
principles or a quotation of a `results/` file with its n, and both are
labelled. Under rule 1 none of it is a finding.

Two derivations were re-checked independently before this was filed, per
rule 8. The duty-cycle estimator in §6 was verified numerically against a
16-period square wave: |c₂/c₁| came out 0.3079, 0.3427 and 0.2726 at duty
0.400, 0.388 and 0.412 against the analytic 0.3090, 0.3446 and 0.2730.
The datum ambiguity in §4 was verified against the registry: 46.41° to
the boundary and 57.47° to the road, an 11.06° gap, against a method
spread of 1.97° — the ambiguity is 5.6 times the precision.

![The corrected pipeline](figures/architecture.svg)

## The arithmetic this rests on

    f_px = f35 · 5120 / 43.267        5120 px = the 3072×4096 diagonal
    f35 = 24 mm → f = 2840 px         f35 = 46 mm → f = 5443 px

Ground sampling at f = 2840 px, camera height **assumed** 1.5 m — no
photograph records it, and that assumption is the whole of §2:

| distance | lateral mm/px | longitudinal mm/px | 20 cm across a 45° stripe | ±6 mm |
|---|---|---|---|---|
| 2 m | 0.70 | 0.94 | 251 px | 7.5 px |
| 3 m | 1.06 | 2.11 | 150 px | 4.5 px |
| 5 m | 1.76 | 5.87 | 84 px | 2.5 px |
| 10 m | 3.52 | 23.47 | 41 px | 1.2 px |
| 20 m | 7.04 | 93.90 | 20 px | 0.60 px |

**Pixels are not the binding constraint in the near field.** At 3 m a
20 cm stripe is 150 px and the tolerance is 4.5 px. Everything that fails
below fails for another reason.

Two more: deciding 20 cm against ±6 mm needs the scale to **3.0 %**
(30 cm gap: 2.0 %; 10 cm red line: 6.0 %). And 第02898章 §3.3.4's ±5 cm
lateral position is an angular tolerance of atan(√2·0.05/L): **4.04° at
L = 1 m, 2.02° at 2 m, 1.35° at 3 m.**

## 1. The order

**Neither of the two on offer. Paint → plane → semantics, with the
trafficable region an output rather than an input.**

Region-then-paint is wrong: the region is found by roughness and a
chevron's roughness *is* its paint. Paint-then-region is the same loop
backwards — a missed marking shrinks the road, which removes more
markings — and rule 9 bars any metric over that pair.

The physics settles it. Paint and asphalt differ in **albedo**, not
geometry: both flat, both grey, both smooth. A surface classifier built
on texture is reading the marking, and no preprocessing makes it read the
surface, because there is no surface signal there. What is geometric is
that all of it lies on one plane. So the load-bearing step is the
**ground plane**, recovered from the markings' own vanishing directions,
which needs only focal length and is invariant to camera rotation.

> **Stage 2 was built, held out, and dropped the same day.** Three
> versions of it - one vanishing point, two, then a consensus across
> pairs - all failed the check specified below. The last one is still
> 1256 px out on F05 and 2508 px on F22 in a frame 4096 tall. It is in
> `src/marking/pipeline.py`, it is not called, and `stages_built()`
> says so under `present_but_not_called`.
>
> The reason it was dropped rather than fixed is that **nothing here
> needs it.** The angle between two ground directions is
> `acos((K⁻¹v₁)·(K⁻¹v₂)/(|·||·|))`, a rotation invariant that has no
> parameter for a plane, a pitch or a horizon; the metric checks that
> would need a rectified plane are refused on all 42 anyway for want of
> a scale (§2c); and the one consumer left is a crop. `search_domain`
> is now a stated constant, below, and the crudeness is the finding.
>
> This paragraph is the check earning its cost. The stage was specified
> with a falsifier before it was written, the falsifier rejected it, and
> what replaced it is an approximation that says what it is.

    0  provenance     bytes, EXIF, date, native size, camera height?
    1  paint field    whole frame, no region, full resolution
    2  ground plane   from the paint's own vanishing directions
    3  scale          declared, sourced, or absent
    4  near-field IPM re-detect at the one correct width
    5  identification each marking class by its own § predicate
    6  two regions    both derived from stage 5, neither an input
    7  verdicts       with guard bands and explicit refusals
    8  stability      the original, perturbed around

The only feedback edge is 1 → 2 → 4, broken by re-detection: stage 1's
mask reaches the plane fit as segments and reaches the measurement not at
all.

## 2. Scale

**(a) §182 dashed line, 4 m mark / 6 m gap.** The only non-circular
metric scale in the regulation; its paint is good to ~1.25 %. But
`results/dash_population.json` records the identification attempt
returning `share_at_regulated_size: 0.035` over 270 components against a
rule needing >0.5 — one run, failed. And the dashes are far: a 4 m dash
at 20 m, at 93.9 mm/px, costs ±1 px per end = **3.3 %**, over budget
before anything else; 7.5 % at 30 m.

**(b) EXIF focal length plus assumed height.** f35 is an integer, so
24 mm means 23.5–24.5: **±2.1 %** before anything. The height is fatal —
none recorded, handheld is 1.2–1.7 m, **±17 %** on every metric length.
What it *does* buy: the plane's shape needs f and pitch only, not h, so
stages 2 and 4 run on it and give correct ratios and angles. Geometry,
not the metre.

**(c) The chevron's own 50 cm pitch.** Circular for every §171 quantity.
`results/scale_stripe.json`: 7 captures, 2 usable, camera heights of
9.96, 4.21, 8.00, 2.25, 5.35, 2.56 m. **Forbidden as a scale for §171.**

**(d) No metric scale.** More is checkable scale-free than has been used:

| quantity | scale-free form | regulated |
|---|---|---|
| stripe vs gap | duty cycle | 0.400 |
| stripe vs border line | 20/15 | 1.333 |
| red line vs lane line | 10/10 | 1.000 |
| arm vs boundary | angle | 45°, datum undefined |

**Decision: scale-free by default.** `scale_source` is an explicit enum
on every metric output — `NONE | CAMERA_HEIGHT_RECORDED | DASH_182 |
RED_LINE_169 | STRIPE_171` — with `scale_rel_sd`, and a check whose
tolerance is tighter than 3·`scale_rel_sd` **refuses**. On the existing
42, `scale_source` is `NONE` and no metric check runs.

The cheapest fix is not an algorithm. **Record the camera height at
capture.** A tape against the phone moves the scale from ±17 % to what
the tape reads. The 42 photographs of 2026-09-20 cannot be repaired this
way and the surface has been worked since: they are permanently
scale-free evidence.

## 3. The two meanings of carriageway

**`search_domain`** — where a marking may be looked for. Everything below
40 % of the frame height. Geometric, no appearance term, not a function
of the paint. Under rule 9 this is the only defensible form, and under
the box above it is a **declared constant rather than an estimate**: a
handheld photograph of a road taken while standing puts the horizon
above that line, and a frame where it does not is one where the camera
was pointed at the sky.

`tests/test_pipeline.py` fails if the function's signature grows an
image, a mask or a horizon, and fails again if the same shape ever
returns two different domains. A region chosen by appearance is scored
by the appearance that chose it - that is precisely the defect
`carriageway()` had, and it cost 45 points of paint retention before
anyone noticed.

**`trafficable`** — where a vehicle may lawfully be. An **output** of
stage 5: bounded right by §169's red line (wherever it is painted - see
`isolation/REDLINE.md`) or §180's edge line,
left by §165/§167, minus §171's chevron polygon (禁止跨越), minus the
works hoarding.

The chevron is inside `search_domain` and outside `trafficable`. That is
the distinction one mask could not carry.

`carriageway()`'s three callers get three replacements:

| caller | wanted | replacement |
|---|---|---|
| `gate2._segments` | where to look | `search_domain`; the `bitwise_and` is deleted |
| `_kerbside_red` | outside the running surface | §169's own geometry |
| `_surface_types` | where to sample | `trafficable` |

`ROI_FRAC_MAX = 0.87` goes with `carriageway()`. Rule 5: its replacement
is re-derived on the same real and noise populations in the same commit,
or the commit says it was not and why.

## 4. What is measurable

| quantity | § | tolerance | binding limit | verdict |
|---|---|---|---|---|
| stripe width 20 cm | 171 | ±6 mm | scale needs 3.0 %, best is 17 % or ≥3.3 %; camber alone ~4 % | **not measurable** |
| gap 30 cm | 171 | ±6 mm | scale needs 2.0 % | **not measurable** |
| stripe/gap ratio | 171 | ±0.012 | measurement spread | **measurable in principle** |
| 45° | 171 | paint gives 2.02° at L = 2 m | the undefined datum | **measurable, verdict blocked** |
| red line 10 cm | 169 | ±6 mm | scale 6.0 %; the line may be on the kerb face, off the plane | **not measurable** |
| taper length | 守則/§155 | 17–56 m | 94 mm/px at 20 m, 587 at 50 m; flat ground gone at a bridge | **not measurable from one frame** |

Three limits that are not resolution:

**Camber.** A 2 % crown over 3 m lateral is 6 cm of height. A point 6 cm
off the assumed plane at 5 m with h = 1.5 m is a range error of about
20 cm — **4 %**, larger than the whole budget, from geometry alone.

**Wear.** The regulated quantity is the width *as laid*; the observable
is the width *as worn*. A photograph cannot separate a stripe painted
193 mm from one painted 200 mm and worn 7 mm. Definitional, not
precision — no pipeline closes it.

**The datum.** §171 says 斜四五度 and not relative to what. The registry
carries `chevron_to_boundary_deg` 46.41 and `chevron_to_road_deg` 57.47,
n = 4 captures of one panorama — **11.06° between two lawful readings,
against a method spread of 1.97°.** Report both. Never emit a single 45°
verdict.

## 5. How each stage is evaluated

Rule 9: the metric must be something the stage can fail. Rule 10: both
errors, always.

**Stage 1, paint.** Hand-drawn polygons. **Per-frame recall and
precision**, full list and range, never a mean alone — a detector that
fires everywhere scores recall 1.0 and precision near 0, so the pair
cannot be won by construction. Stratify on f35 (24 mm ×39, 46 mm ×3) and
chevron-in-frame, crossed with lighting; two frames per non-empty
stratum, not fewer than ten; the rest are never annotated and never
fitted on.

**Stage 2, plane.** **Held-out prediction.** Fit the vanishing line from
two families, predict a third's vanishing point, report the angular
residual. The third is not in the objective, so the fit cannot suppress
it. Then permute the family assignment and confirm the residual grows.

> **Run 2026-09-21, and it failed.** Median held-out residual **9.33°**,
> range 0.42–87.69, over 20° on **17 of 37** frames that produced a
> plane at all; against an independent sky-edge estimate the fitted
> horizon is out by a median of **610 px** in a 4096 px frame.
> `results/plane_holdout.json`, `scripts/plane_holdout.py`.
>
> The diagnosis is the one this document predicted in *"the decision the
> architect was least sure of"*: searching the whole frame hands stage 2
> rooflines, wires and hoarding panels alongside the paint, and a
> chevron's stripes outnumber the lane lines that would have fixed the
> horizon correctly. The stage is withdrawn, not repaired. See the box
> in §2.

**Stage 3, scale.** Leave-one-out on the regulated lengths. Below three
intervals the scale is unvalidated and reported as such.

**Stage 4, IPM.** **Depth invariance.** Duty cycle in three depth bands.
A correct plane gives a duty cycle independent of depth; a plane error
gives a monotone drift, and the homography fit never sees the duty cycle
so it cannot flatten it.

**Stage 5, identification.** Confusion matrix, both errors per class. The
false positive to watch is recorded: `_grated_cover`, a periodic
low-saturation bar detector, found three periodic structures in three
frames — the chevron, an asphalt patch, the ghost of an erased chevron —
and no drain cover (n = 3, one site). Any periodicity test is evaluated
against that or it repeats it.

> **Built 2026-09-21. The predicates hold; §171 has no locator.**
>
> The predicates are in `pipeline.identify` and each section is a
> **conjunction**, which is the lesson from `_grated_cover`: §171 does
> not say "periodic", it says 20 cm stripes at 30 cm intervals at 45
> degrees, in paint. Four properties. The recorded false positives fail
> on the ones periodicity cannot see — an erasure imprint is *darker*
> than its surround, an asphalt patch is at neither 0.400 nor 45° — and
> `tests/test_pipeline.py` asserts exactly those three cases, including
> that periodicity alone does not pass.
>
> Feeding §171 is the part that failed. `scripts/stage5_predicate.py`
> tried to locate the chevron by unsupervised periodicity over the 42
> field photographs and the 3 epochs. **44 of 45 returned no measurable
> profile.** The one that did is `e3_2025-06`, the frame where the
> chevron had been **erased**; the two epochs that do contain a chevron
> measured nothing. And the period came back at the Gabor bank's
> largest kernel on every frame — 28 px, and then 80 px after the bank
> was extended to 80. It is a ceiling, not a period. The strongest
> periodic response on a road surface is shadow, kerb and hoarding.
>
> Two by-products worth keeping. The duty estimator was calibrated and
> two gates were rejected before one worked: energy above the
> fundamental scored a noisy sinusoid at 0.487, inside the band real
> square waves occupy, and cosine similarity of the harmonic series
> gives a pure sinusoid 0.932 *structurally*. What works is a
> **held-out** prediction — the duty comes from `c2/c1`, so harmonics
> 3, 4 and 5 are not in the estimate and a square wave must put
> `|sin(nπD)|/(n·|sin(πD)|)` into each. Square 0.004–0.045, sinusoid
> 0.101–0.178, noise 1.589. The same principle as the plane hold-out,
> one stage down.
>
> And `results/chevron_periodic.json` reports `period_px_median` 28.0
> on **45 of 45**, which is that bank's ceiling. Its contrast figure
> stands; its period column is withdrawn. Nothing published moves — it
> was never in the figure registry.

**Stage 6, the two regions.**

*`search_domain` gets no score.* Its paint recall is 1.0 by construction,
which is why the metric is worthless. Enforce it **structurally**: a test
asserts the function does not take a paint mask, a marking response map
or the colour channels as arguments, and a dataflow test asserts no
output of stage 1 reaches it. An invariant a test can break is worth more
than a number that cannot go down.

*`trafficable` against human polygons.* An annotator sees the photograph
and the text of §165, §167, §169, §171, and draws where a vehicle may
lawfully be, without seeing the output. Score **two numbers, never their
harmonic mean**: truth missed, and area outside truth.

*The falsifier needs no annotation.* `output/epochs/` holds 2022-11,
2024-09 and 2025-06 of one location, and `results/erasure*.json` records
the chevron erased between epochs. So the chevron's ground area is known
to have moved from not-trafficable to trafficable. Two predictions, in
opposite directions:

    trafficable   must GROW by about the chevron's area across the erasure
    search_domain must NOT CHANGE across the erasure

No preprocessing satisfies both. A step that erases paint before judging
the surface already had the chevron inside `trafficable`, so it does not
grow. A step that uses paint to bound the road moves `search_domain`. The
old pipeline fails the first; the review's inversion fails the second.
**This is the non-circular evaluation, available today at zero annotation
cost.** n = 3 epochs at one location, so it is a falsifier and a
hypothesis, not a score.

**Stage 7, verdicts.** Wrong-verdict rate among verdicts given, and
refusal rate, together. And the honest statement: **there is no ground
truth for any metric verdict.** No stripe at this site has been measured
with a tape. The remedy is a field task, not a code task: tape five
stripe widths and five gaps, photograph the tape in place, record the
camera height. That one visit converts stages 3, 4 and 7 from unvalidated
to validated and is the highest-value item in this plan.

## 6. Migration

| module | fate |
|---|---|
| `extract.dark_light_dark`, `markings` | **survive** → `paint.py`, declared candidate generation, not measurement |
| `extract.carriageway` | **deleted**, three callers, three replacements |
| `rectify.py` | **survives**; gains `plane_from_vanishing_line`, `homography_ground`, and a mandatory `scale_source` argument so no caller obtains a metre without saying where it came from |
| `vanishing.py` | **survives whole** — the soundest code here. `angle_uncertainty` is demoted to one diagnostic: endpoint jitter answers how precisely a chosen line was fitted, not whether the same line would be chosen |
| `sequential` direction estimation | **survives** for stage 2 |
| `sequential.hatched_side` | **replaced** by the spectral test below |
| `sequential.taper*` | **retired** with the taper-from-one-photograph claim |
| `gate.py`, `gate2.py` | **retired** |
| `situation.assess` | **survives**; `TAPER_TOO_STEEP` becomes a refusal with a reason |
| `route.py` | **rule 7.** Nothing imports it. Either wire it in *in the same commit as a test asserting it is called*, or delete it. No further tuning before one of those |

### The ensemble under rule 4

1. **The measurement is on the original.** 3072×4096, the file's own
   bytes. That is the reported value.
2. **The grid becomes a check around it.** Cell zero is the original.
   Resolution and JPEG quality are *not* the interesting axes — they
   change the question rather than the answer (a 10 cm line is 14.2 px in
   the original and 3.5 px at 1000 px). The honest axes are the unknowns:
   **focal length** over the EXIF quantisation ±2.1 %, **horizon
   position** over its fit residual, **scale** over `scale_rel_sd`.
3. **The spread is the uncertainty, not the verdict.** The value is the
   original's; the spread sets the guard band. The current code reports a
   bound from the mildest degraded cell and no value at all, which
   discards the best measurement in favour of the worst.
4. **`ROI_FRAC_MAX`, `CORRIDOR_WIDTH_DEG`, `ANGLE_SD_DEG`** are all
   calibrated against the old behaviour; rule 5 applies to each.
   `ANGLE_SD_DEG = 0.55` carries n = 4 in its own comment and that n does
   not grow by being re-used.

### The chevron as a periodic pattern

Accepted in substance, rejected in form. A Gabor bank at 45° **in the
frontal frame** fails for the same reason the fixed width bank fails: a
50 cm pitch varies several-fold across one frame, so a fixed-frequency
filter is tuned to one depth. A 2-D bank also has four free parameters
and a correspondingly large false-positive surface, which this project
has already paid for once.

The constrained form: in the near-field IPM plane, with the band
direction known from the boundary, take the **1-D power spectrum of the
paint profile along the band**. The chevron is a square wave and the
regulated duty cycle is read from the harmonic ratio

    |c₂/c₁| = |cos(πD)|

    D = 0.400 → 0.3090      D = 0.388 → 0.3446      D = 0.412 → 0.2730

so ±6 mm maps to a harmonic band of 0.273–0.345, sensitivity −2.99 per
unit duty. **Scale-free**, and it uses every stripe at once rather than
14 adjacent pairs. The pairwise approach returned 0.366 ± 0.134 over 14
pairs of one photograph against a tolerance band of ±0.012 — eleven times
too wide.

Set the target before running it: the spectral duty cycle is an
improvement if its standard error over the population is below 0.012, and
it is a hypothesis with its n either way.

### Angles stay in the frontal original

The review asks for angles in the warped plane. Refuse, twice over.
**Circularity**: the homography is fitted from two families' vanishing
points, so measuring the angle between those families after warping by
that fit is measuring the fit. The frontal construction uses only K and
is rotation invariant — it needs no plane, so a plane cannot contaminate
it. **Resampling**: `warpPerspective` magnifies the far field, where
longitudinal sampling is already 94 mm/px at 20 m, and interpolates the
edges that carry the angle.

**Angles in the frontal original at full resolution; metric and
periodicity in the near-field IPM**, whose extent is set by a stated
bound on longitudinal ground sampling — at f = 2840 px and h = 1.5 m, a
5 mm/px bound puts the far edge at about 5 m — not by a pixel constant.

## What this plan refuses to deliver

- No stripe-width, gap or red-line-width verdict from any of the 42
  photographs of 2026-09-20: none records a camera height and no §182
  dash is near enough for a 3 % scale.
- No single 45° verdict ever, because the clause does not state the datum.
- No taper length from one photograph.
- No metric verdict validated against truth until someone stands at the
  site with a tape.

What it does deliver on today's evidence: the two regions, the scale-free
duty cycle, the two-datum angle pair with its uncertainty, and a refusal
with a reason everywhere else.

## The decision the architect was least sure of, recorded as given

Making `search_domain` the whole ground plane below the horizon, with no
appearance narrowing, defended by a structural test rather than a metric.
It is right that any appearance narrowing is unscoreable under rule 9 and
that the current one destroyed the evidence. But dropping it hands stage
2 every line in the frame — rooflines, power lines, hoarding panels, the
bridge parapet, the opposite carriageway — and RANSAC picks the most
redundant direction, which on F17 might be the workshop roofline. The
plane fit and the §-cited predicates are relied on to reject those and
that has not been demonstrated; `_grated_cover` finding three wrong
periodic structures in three frames is a warning that predicates at this
site are less discriminating than they look. If this plan fails anywhere
it fails here, and the two-epoch falsifier is where it will show first.
