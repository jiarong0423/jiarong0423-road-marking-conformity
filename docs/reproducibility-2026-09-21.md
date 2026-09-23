# The taper angle is not reproducible

2026-09-21. This withdraws the project's headline measurement.

**Registration status, added the same day under standing rule 2.** Nothing
on this page is in `results/figure_registry.json`, because every figure
here is the output of an ensemble run over 4, 42 or 45 photographs and
none of those runs wrote to `results/`. Repeating one costs about 45
minutes and none was repeated. Each block is therefore marked below with
its n and "not reproduced", which by this project's own definition makes
the figures unverified - not withdrawn, and not disbelieved. Three things
on this page are worse than unverified and are marked withdrawn in place:
the method description immediately below, the `roi_frac > 0.75` gate, and
the standing of the router section.

## What was tested

The same photograph, re-encoded as JPEG at eight qualities (80-100) and
resampled to three long sides (1050, 1400, 1900 px), put through
`assess()`. Nothing about the road changes between runs. Any variation is
the method's, not the site's.

Four photographs: the 2025-06 Street View capture and field frames F05,
F17, F22.

**Withdrawn, 2026-09-21: that paragraph does not describe any grid that
exists.** Eight qualities by three resolutions is 24 cells, and every
count in the table below is out of 15. `src/marking/situation.py` has
`QUALITIES = (80, 90, 100)` and `WORK_PX = (1000, 1400, 1800)`, which is
nine cells at three resolutions none of which is 1050 or 1900 - and nine
is what `docs/what-changed-2026-09-21.md` says the ensemble measures.
Three mutually exclusive descriptions of the same harness: 24, 15 and 9.
The harness was ad hoc and was not saved, so which one produced the table
cannot now be established. Verify the grid before quoting this section:

    grep -n 'QUALITIES\|WORK_PX' src/marking/situation.py

## What came back

| photograph | taper fires | angle spread across encodings |
|---|---|---|
| 2025-06 街景 | 12/15 | 11.5-14.0° |
| F05 | 10/15 | 4.9-9.9°, median moves 7.6 → 14.5 with resolution |
| F17 | 1/15 | 15.8 / 17.9 / nothing, by resolution |
| F22 | 6/15 | up to 17.3°, median 6.3 → 14.2 → 19.8 with resolution |

(n=4 photographs, not reproduced, not registered. The conclusion - that a
value moving by more than its own magnitude is not a measurement - does
not depend on the exact figures, and the withdrawal below stands on it.)

A measurement whose value moves by more than its own magnitude when the
file is saved at a different quality is not a measurement.

## Root cause, two layers

**Selection ignores how much evidence a candidate has.** The rule takes
`max(arms × lopsided)` among the candidates that satisfy §171 - how much
hatching borders the line, and how one-sided it is. It does not look at
how many segments support the line at all. So at q=80 the chosen group
had 3 members while a bordering candidate with 30 members was passed
over; at q=92, 4 against 18; at q=100, 6 against 35. A line fitted to
three segments has hatching evidence just as computable as one fitted to
thirty, and on this score it can win. (The six membership counts and the
139-162 segment range below: n=1 photograph, not reproduced, not
registered.)

(An earlier version of this page said the rule takes the last candidate
satisfying §171. It does not; it takes the highest arms × lopsided. The
observation about membership stands, the description of the rule was
wrong.)

**Fixing that is not enough.** Taking the strongest bordering candidate
instead gives 19.3 / 14.2 / 6.7 / 16.9 / 12.3 / 5.3° across the same six
qualities. The candidate set itself moves. LSD returns 139-162 segments
depending on the encoding, and sequential RANSAC groups them differently
each time.

## Withdrawn

- 10.23° ± 0.55 (`results/taper_vanishing.json`)
- taper rate 0.1806, and 29.3 km/h equivalent
- every "N times steeper than required" multiple derived from it
- 12.1° and 26.9 km/h in `results/taper_rate.json`, same method
- 0.202 rate and the 1.07/1.34/1.78 s exposure times in `results/reaction.json`

All three source files carry a `withdrawn` marker, and
`scripts/check_figures.py` refuses any registry entry that cites a
withdrawn source, so these cannot quietly come back through the registry.
Checked by `/opt/anaconda3/bin/python3 scripts/check_figures.py`.

The ±0.55 was endpoint jitter over 200 draws on one fixed line. It was a
real number answering the wrong question: it measured how precisely a
chosen line could be fitted, not whether the same line would be chosen.

## A hypothesis that is now unnecessary

Two captures read 18.82° and 2.61° and were called outliers, with the
bridge's +5.9% grade proposed as the cause, to be tested by restricting to
the near field. Both values sit inside the spread that compression alone
produces on a single image. The grade hypothesis explains nothing that
needs explaining. Closed, untested, because there is no longer an anomaly.

## What survived the same test

| finding | where present | fires | value spread |
|---|---|---|---|
| `CARRIAGEWAY_OCCUPIED` | F05 | 15/15 | width 0.434-0.439 |
| `SURFACE_IN_PIECES` | F05 / F17 / F22 | 15/15, 14/15, 15/15 | 5; 3-4; 3-4 |
| `EDGE_NOT_CARRIAGEWAY` | F22 | 15/15 | — |
| `NO_LANE_CHANGE` | 街景 | 12/15 | — |
| `TAPER_TOO_STEEP` | all four | 29/60 | not reproducible |

(n=4 photographs, not reproduced, not registered - the twelve counts in
the table, its 0.434-0.439 width spread, and the 43.7% frame width and 44
of 45 runs in the paragraph that follows. What the table is for is the
shape of the result, which is that the composite claim does not rest on
the taper.)

The composite claim does not rest on the taper. The hoarding takes 43.7%
of the frame's width at travel height and that number does not move; the
right-hand edge is not carriageway in every encoding of F22; the surface
is in pieces in 44 of 45 runs where it is present. What fails is the one
quantity that had been leant on hardest.

## Not yet decided

Whether `TAPER_TOO_STEEP` is removed or rebuilt around an ensemble - run
the frame at several encodings and report the spread as the uncertainty,
returning INDETERMINATE when it is wide. The guard-band discipline already
in this project says the second, but it has not been built or agreed.

## What the gates do over all 42 photographs

Added 2026-09-21, after wiring the refusal to a router - which it was
not; see the router section below, where that claim is withdrawn.

| | |
|---|---|
| CANNOT_MEASURE | 38 |
| INDETERMINATE | 3 |
| STEEPER_THAN_REFERENCE | 1 (F39) |

(n=42, the full set, not reproduced, not registered.)

F39 is the photograph that shows the chevron most plainly, which is the
behaviour wanted: refuse on the frames that do not carry the marking, and
on the one that does, report a bound rather than a number.

### Three corrections to what this page said before

**carriageway() does not reject noise.** This page and a commit message
claimed it separated noise cleanly from road, on the strength of one noise
image it refused. Over 24 noise images it refuses 5 and accepts 19,
covering 85 to 97% of the frame. What does separate them is that coverage:
21 photographs of real roads give 0.179 to 0.614, because a road
photograph has sky, buildings and verge in it.

**Withdrawn, 2026-09-21: the sentence that used to end this paragraph said
"the gate is now `roi_frac > 0.75`, and over those 45 images it refuses
every noise frame and no real one". That gate no longer exists and the
0.75 was wrong within hours of being written.** Fixing `carriageway()`
enlarged the region it was calibrated against, and 7 of 12 real
photographs were then refused as not being road photographs - standing
rule 5, exactly. Commit 4a72826 re-measured over 24 real and 16 noise
frames (not the 21 and 24 quoted above), found real at 0.128-0.819 and
noise at 0.923-0.977, and set the constant to 0.87. Read it from the
source, not from here:

    grep -n 'ROI_FRAC_MAX' src/marking/situation.py

The 24-noise and 21-road counts above, and their coverage ranges, are
themselves not reproduced: the noise frames were generated without a
recorded seed, so that population cannot be rebuilt.

**The corridor was not enforced after refinement.** `corridor_direction`
samples inside 1-20 degrees, then refits by SVD and returned the refined
separation without rechecking. That is how a 75-degree spread appeared on
a search whose entire range is 19 degrees wide. Readings outside the
corridor are not tapers by the corridor's own definition and are now
dropped.

**The magnitude was being reported and is not reportable.** F03's readings
run 6.35 to 19.17 degrees, so "the geometry suits 22.5 km/h", taken from
the median, is a number the measurement cannot support. Every one of those
readings exceeds the requirement, though, and that the conclusion does not
depend on which reading is taken is the thing worth saying. The verdict is
now a bound from the mildest reading: F39 is at least 1.46 times steeper
than required, suiting at most 41.4 km/h. A bound that holds across the
whole ensemble is a stronger claim than a median that holds nowhere.

A bound is only a bound on one quantity, so readings that scatter wider
than the corridor itself are refused: they are measurements of different
objects and the mildest bounds nothing.

## The router, and what the model is contributing

**Withdrawn, 2026-09-21, on standing rule 7: this section describes a
component that is not connected to anything.** `route_ensemble` is
defined in `src/marking/route.py` and imported by nothing:

    grep -rn 'route_ensemble' --include='*.py' . | grep -v __pycache__

returns one line, its own definition. "Added 2026-09-21, after wiring the
refusal to a router" is not true of the code in this repository; the
router was exercised from a session that was not saved. Everything below
therefore describes a component that is not in the pipeline, and its
confidences are single observations from a non-deterministic model - the
subsection at the end of it says so itself. None of it is reproducible and
none of it is registered. The 0.27-to-0.91 improvement is real work on a
part that is not connected, which is the instance rule 7 was written from.

`route_ensemble` turns a refusal into an action. Predicates first, as the
project's own rule requires: no road in the frame, or no candidate in the
corridor in any encoding, or no candidate bordering hatching in any of
them, are each settled without asking. Over the 42 photographs the
predicates settle 9 and pass 33 to the model.

The model is not earning its call. On the cases that reach it the
confidences are 0.22 to 0.36, and chance on a four-way choice is 0.25. The
abstain band was 0.4 to 0.6, which passed a 0.19 answer through as
decisive; that band came from a two-option pilot where a low confidence
means confidence in the other option. Anything at or below 0.6 now goes to
a person, which is every case the model has seen here. Whether the
question is wrong for it or the counts do not discriminate is not yet
established.

## The router was starved, not stupid

The first version handed the model eight aggregate counts over the nine
encodings and it answered at 0.22 to 0.36 on a four-way choice, where
chance is 0.25. The reading was that the model could not do the job. The
reading was wrong, and the fault was in what it was given.

Aggregating the grid destroys the thing that discriminates. A photograph
that fails only at low working resolution and one that fails in all nine
cells produce similar totals and call for opposite actions - retake the
photograph, or accept there is no marking here. The grid's shape is the
evidence, so the grid now goes, one row per encoding.

`unclear` was also removed as an option. It is a state of the model, not
of the road or the photograph, and mixing it in with physical states blurs
all of them. Not knowing is the confidence gate's job. The three that
remain are what can be true of the photograph: nothing there,
photograph inadequate, scene ambiguous.

| photograph | counts, 4 options | grid, 3 states |
|---|---|---|
| F05 | 0.27 | 0.38 |
| F17 | 0.22 | 0.65 |
| F22 | 0.32 | 0.89 |
| F01 | - | 0.95 |

Over eleven photographs the median confidence is 0.91 and eight of ten
asked clear the 0.6 needed to act. F22's grid - nothing at 1000 px, every
cell at 1400 px, falling away at 1800 - is read as an inadequate
photograph at 0.92, which is what that pattern means.

F05 stays at 0.38 and goes to a person. Its grid has three rows, because
the ensemble exits early once the readings straddle the reference, so
there is genuinely less to read.

### The router is not deterministic

F17 returned 0.65 on one run and 0.59 on the next, which is either side of
the threshold that decides whether a person is asked. The verdict that
follows from a measurement is therefore not stable even when the
measurement is. Nothing here averages the router over repeats the way the
ensemble averages the measurement, and it should.

## Scaling the detector's parameters makes it worse, not better

The detector's gap and vote threshold are absolute pixel constants, so
over 42 photographs the median segment count falls 50% from 1000 to
1800 px. The resolution axis of the grid was therefore partly measuring
the parameters rather than the road, which if true would contaminate the
reproducibility argument the whole ensemble rests on.

A line of fixed physical length contributes proportionally more edge
pixels at higher resolution and a gap of fixed physical width spans
proportionally more, so both should scale linearly. On 14 photographs
across two JPEG qualities that looked right: the median angle spread fell
from 8.4 to 2.9 degrees.

On all 42 across three qualities it reverses.

| | photographs with 2+ readings | median angle spread | under 5° |
|---|---|---|---|
| absolute, as written | 27 of 42 | 6.3° | 9 |
| gap scaled | 22 of 42 | 9.1° | 5 |
| gap and vote threshold scaled | 24 of 42 | 9.4° | 5 |

(n=42, not reproduced, not registered - nine numbers, plus the -50% and
+55% segment-count movements below.)

Both variants were run, in case scaling the gap without the accumulator
threshold was the incoherent half of the change. It was not: scaling both
is worse too.

So the change was reverted. The sample of 14 was too small and used two
qualities where the pipeline uses three, and I read a three-fold
improvement out of it that does not exist. That is the same error as the
one this page opens with, made again while fixing it.

The finding that stands: the detector is scale-dependent, and linear
scaling is not the correction. Scaling the gap alone overshoots in the
other direction - median segment count moves from -50% to +55% across the
same range - so the relationship between resolution and edge-chain
fragmentation is not linear, and no single multiplier fixes it. Fixing it
properly means a detector with fewer scale-bound parameters, which was
tested earlier: LSD and FastLineDetector both gave wider angle spreads
than what is here.

Left as a known defect, measured and written down rather than patched.
