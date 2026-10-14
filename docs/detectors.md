# What the detectors are allowed to say

2026-09-22, published 2026-10-14 (an English summary of the author's working notes).

The detectors in `src/marking/` still run, and `assess()` still calls them. What was taken
away on 2026-09-22 is their right to be cited as evidence. A person opened their output photo
by photo, and most of the counts did not survive.

## Detector counts against a person who opened the photographs

Over the 42 photographs of 20 September:

| Detector | What it reported | After a person opened the photographs |
|---|---|---|
| `_kerbside_red` (red line, §169) | 25 of 42 | of 23 opened, **13 were not red lines**: yellow water barriers ×4, double yellow lines ×3, plain grey concrete ×4, one shop sign |
| `_works_hoarding` | 9 of 42 | 3 opened, all right, but the box was only **31.8 % hoarding by area**; "68 % of the frame width" measured the bounding box |
| `_double_white` (§167) | 1 of 42 | **that one hit was a false positive**, and the line that does exist was missed |
| `_surface_types` | 34 of 42 | without a fixed seed, the same photograph gave different answers; seeded now, spread across seeds not measured |
| `taper_ensemble` | 5 of 42 at 50 km/h | the verdict depends on the speed limit squared, and the works-period limit rests on a witness and two painted "30"s |
| drain grates | — | **no detector** in the pipeline; the grate finding is a separate script checked photo by photo (`isolation/field-2026-09-23/cv_evidence.py`) |

So a detector's job here is **to point at what a person should open, not to decide what is
there.** A red-line count with 13 wrong out of 23 is useless as a statistic, but "open these
25" still saves opening 42. That is why the online service answers with `HUMAN_LOOK`
("open this one at full size and check the box") rather than with a count
(`src/marking/actions.py`).

## When a count may be cited again

All four at once:

1. every decision behind the count has been drawn on the full-resolution photograph and seen by a
   person, with agree / disagree recorded;
2. two full runs are compared photo by photo, not only by total (once, the totals matched and one
   photograph did not);
3. a mutation test shows the test guarding it is not empty;
4. the output of the full run is committed, with the code that produced it.

## The taper angle on phone photographs: set by the parameters, not by the road

One photograph through two marking masks × two line-finder settings × two scales:
the taper angle came out anywhere from 3.3° to 19.0° across those eight combinations. Over the
search range of 1-20°, six readings of 4.0 / 8.5 / 10.1 / 14.1 / 17.7 / 19.1° filled it. The sets of photographs where a
reading "held" barely overlapped between settings (31 of 42, 9 of 42, and only 6 in common).
`results/assess_2026-09-22.json` shows the same from the other side: one photograph at nine
encodings (three JPEG qualities × three working sizes) gives 2°-20°.

**Any single taper number from a phone photograph is therefore not citable.** A cleaner mask
(Otsu) changed which photographs report, not whether the numbers mean anything.

What came next (`scripts/measure_chevron_phone.py`, `scripts/measure_taper_phone.py`):
measure the angle between two families of lines from their vanishing points, which needs no
camera pitch. The geometry checks out on synthetic ground truth. What does not converge is
choosing, automatically, which lines in a phone photograph are the stripes and which are the
edge: five selection strategies over ten photographs gave answers that disagree. Each script
refuses when its own checks fail (F37: two estimates of the road direction disagree by
more than 3°, so it reports a range, not a number).

The figures that survive are listed in `docs/accuracy.md` with the check each one passed.
