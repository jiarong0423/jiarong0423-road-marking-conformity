# The night the premise turned out to be wrong

2026-09-21. Written after a long session of tuning, to record what the
tuning was standing on.

**Registration status, added the same day under standing rule 2.** Seven
figures on this page are now produced by `scripts/pixel_budget.py` into
`results/pixel_budget.json` and are in `results/figure_registry.json`: the
originals' dimensions over all 42 photographs, the four pixel budgets, and
§171's stripe-to-pitch ratio. Everything else here comes from a run over
42 or 46 photographs that wrote nothing to `results/`, and repeating one
costs about 45 minutes. Those are marked in place as not reproduced, with
their n. A number so marked is unverified by this project's own
definition; it is not thereby withdrawn, and nothing here says the run did
not happen.

## One paragraph

The pipeline finds the road, then finds the markings on it. Finding the
road used a roughness test, on the reasoning that asphalt is smooth. A
chevron is not smooth - it is a row of high-contrast stripes, deliberately
so - and the test therefore marked the chevron as "not road" and cut it
out. On the one Street View frame showing the chevron intact, the marking
mask and the road region overlapped by 0.9% where chance alone gives 9%:
the region was punching holes exactly where the paint was. (n=1, not
reproduced. The 0.9% is a property of the *pre-fix* `carriageway()`, so
re-deriving it means reverting `src/marking/`, which was not done.) Every
measurement in this project was made through that. A whole night was spent
comparing detectors, scoring functions and thresholds downstream of a step
that had removed 95% of the evidence.

## What was compared, and what it was standing on

| compared | result | valid? |
|---|---|---|
| OpenCV LSD vs Canny+Hough | LSD wider spread | void - before the fix |
| FastLineDetector vs Canny+Hough | FLD wider spread | void - before the fix |
| MSAC vs plain RANSAC | 12.0° vs 12.2°, no difference | void - before the fix |
| linear parameter scaling | worse, 6.3° to 9.1° | void - before the fix |
| M-LSD via OpenCV 5 DNN | loses once letterboxed | void - before the fix |
| inpaint vs median filter in `carriageway` | 88.6% vs 43.3%, 46 of 46 | **the fix itself** |

None of the six numbers in that table is registered, and none was
reproduced on 2026-09-21. The five marked void are void on their own
terms, which is a stronger statement than unverified; the sixth is the
subject of the next section.

Five detector comparisons, all negative, all run on input that had lost
most of its signal. A negative result obtained that way says nothing about
the detectors. They are not disproved; they are untested.

## The fix, and what it did

`carriageway()` claimed in its own comment to remove the markings before
judging the surface, and implemented that with a median filter. Measured
over 46 photographs at matched frame retention, the median filter keeps
43.3% of marking pixels where doing no preprocessing at all keeps 35.3% -
it was doing almost nothing, and after it the markings were still 3.6
times rougher than the road. Inpainting the marking mask keeps 88.6%, and
wins on all 46, worst case 67.4%.

(n=46, the full set for that comparison, and not reproduced: no script in
`scripts/` writes those five numbers to `results/`, so by rule 2 they are
unverified. This is the figure it would be most worth building a script
for, because the fix rests on it.)

On the chevron block of `e3_2025-06.jpg` the road region went from 45.9%
to 94.4% coverage, and its overlap with the marking mask from 0.9% to
19.1% against a mask that is itself 19.5% - from 5% of the paint
surviving to 98%.

(n=1 photograph, not reproduced. The "after" half could be re-derived
cheaply from the current `carriageway()`; the "before" half cannot without
reverting `src/marking/`, and a pair is only a pair if both halves are
measured the same way, so neither was registered.)

## And then the measurement got worse

| over 42 photographs | before the fix | after |
|---|---|---|
| line segments, median | 50 / 39 / 29 by scale | 157 |
| photographs with 2+ readings | 27 of 42 | 42 of 42 |
| readings, median | 2 of 9 | 7 of 9 |
| **angle spread, median** | **6.3°** | **14.2°** |
| **photographs under 5°** | **9** | **0** |
| taper asserted | 1 | 5 |

(n=42 in both columns, not reproduced, not registered - twelve numbers.)

Three times the signal and twice the disagreement. The explanation that
suggests itself is that the broken region was working as an accidental
filter: by removing the chevron it left the long stable lines - the lane
line, the kerb - so the few readings it produced agreed with each other
while measuring the wrong thing. That is a story and it is not yet
evidence. What is certain is that the selection problem was being hidden,
and every threshold and score in this project was tuned against a signal
that was 5% of what it should have been.

## A second error, of the same kind

The ensemble measures nine cells: three downscales crossed with three JPEG
qualities. **It never measures the original photograph.** The originals
are 3072x4096; every measurement was made on something smaller and
re-compressed.

That matters because the regulation is written in centimetres. §171 gives
a 20 cm stripe, a 30 cm gap, a 15 cm border line; §169 gives a 10 cm red
line; the tolerance on marking width is ±6 mm. At 20 m from the camera a
10 cm line is 14.2 px in the original, 4.85 px at the 1400 px working
size and 3.47 px at 1000 px. The ±6 mm tolerance is 0.85 px in the
original and 0.21 px at 1000. A conformity check against those numbers is
only conceivably possible on the original, and only in the near field.

(Registered. `/opt/anaconda3/bin/python3 scripts/pixel_budget.py` rebuilds
all four from the photographs' own EXIF: 24 mm 35 mm-equivalent on the
diagonal over a 3072x4096 frame is f = 2840.1 px. The 20 m is a stated
reference distance, not a measurement of anything on this road, and the
regulation's centimetres are quoted from §169 and §171 rather than
measured. The long-side convention would give 13.7 px instead of 14.2, so
which convention is used is recorded in the artifact. The prose said 4.9
and 3.5; those are the same numbers rounded, and they are written here to
the precision the artifact holds so that the two cannot drift apart.)

Perturbation was supposed to be a check on a measurement. It became the
measurement, and the measurement was never taken.

Over 22 photographs where both can be had, the original sits at relative
position 0.18 in the perturbed range with a median difference of +0.76°,
so degradation tends to read steeper - toward this project's own claim -
but modestly, and on only 12 of 22 individually (n=22, not reproduced, not
registered). An earlier version of
this page said the effect was dramatic on the strength of four
photographs. It is not.

## The first measurement made against the regulation itself

§171 fixes a 20 cm stripe and a 30 cm gap, so the ratio of stripe to pitch
is 0.400. A ratio needs no scale and perspective affects both terms
equally at one depth, so it can be measured from a single photograph with
nothing hand-annotated.

On the original of `IMG_20260920_155843.jpg`, over 14 adjacent pairs:
**0.366 ± 0.134**. Consistent with the regulation, and not sharp enough to
detect a deviation that would matter. Twelve of 26 candidate stripes were
rejected because the extractor merged or split them.

(Hypothesis, n=14 pairs on one photograph, not reproduced. The extractor
that produced it was not saved to `scripts/`, so there is nothing to
re-run, and rebuilding it would be a new measurement that might not agree.
The 0.400 it is compared against *is* registered, because that one is
arithmetic on §171. This is the most recoverable figure on the page: one
photograph, no pipeline, and it is the first quantity measured against a
number the regulation states.)

It is worth recording because it is the first quantity this project has
measured directly against a number the regulation states, with no hand
annotation and no scale - and it is measurable only on the original.

## The pattern worth keeping

Four times in one session a claim was generalised from a sample that
happened to agree, and four times the full run reversed it:

- 2000 px publication was "lossless" on 2 photographs; over 42 it changes
  17 findings and 10 taper verdicts
- scaled detector parameters improved the spread three-fold on 14; over 42
  they made it worse
- M-LSD won on the grid; letterboxed correctly it loses
- degradation bias was dramatic on 4; over 22 it is +0.76°

None of those eight numbers is registered either. The pattern is the point
of the section and it survives; the figures in it are unverified.

Each was caught, and each was caught by running the full set rather than
by thinking harder. The measurements that survived this session are the
ones with a stated n and a full-population run behind them.
