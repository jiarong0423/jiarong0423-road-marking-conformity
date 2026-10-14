# How accurate is it?

2026-10-14. Every figure below is read from `results/accuracy_table.json`, which
`scripts/accuracy_table.py` gathers from the result files named in each row. Nothing new is
measured there.

**This is real data: one real road, photographed by one rider, in live traffic.** The road was
not closed. Every photograph was taken from the kerb or the roadside between passing vehicles,
so many angles could not be had, and no one stood in the carriageway with a tape. The ruler
is the markings themselves: their sizes are fixed by regulation (a red line is 10 cm wide,
a lane dash 4 m with a 6 m gap), and a card laid on the red line at the kerb is the one
physical reference. Accuracy is checked in the four ways that allows, and each has its limits.

## 1. Sizes fixed by law or by a standard, measured back

These are the only true values available: the markings have legal sizes, and an ID-1 card
(ISO/IEC 7810) is 85.60 mm long.

| What | Known size | Measured | Error | Source |
|---|---|---|---|---|
| New red line's width, with an ID-1 card laid across it as the scale, P55 | 100 mm (§169) | 96.85 mm | −3.2 % | `isolation/field-2026-09-23/card_vs_redline.json` |
| the same, P56 | 100 mm | 95.2 mm | −4.8 % | same |
| the same, P59 | 100 mm | reading failed (19.45 mm) | — | same |
| One lane dash, found by `HoughLinesP` in the top-down view of P64 | 4 m (§182) | 4.1 m | +2.5 % | `results/erased_triangle_P64.json`, `ruler` |
| Spacing of the dashes used as the ruler (dash + gap) | 10 m (§182) | spread 2.9–11.5 % for 4–7 dashes; scale 1.69–2.04 m per unit | about ±10 % | `results/dash_ruler_P64.json`, `subsets` |

What this means: the red-line ruler is good to about 5 %. If the line is really about 96 mm
wide rather than 100, every red-line gap is about 4 % smaller (0.63–0.68 m becomes about
0.61–0.65 m; the README says so). The top-down ruler on P64 is good to about 10 %, and every
P64 figure (the 8.5 m painted-over end, the 3.13 m merged lane) carries that.

## 2. The same thing on different photographs

| What | Photographs | Readings | Spread | Source |
|---|---|---|---|---|
| Red line moved (median gap) | F30, F31, F32 | 0.680, 0.669, 0.635 m | 4.5 cm | `results/redline_gap_F30.json`–`F32.json` |
| Red line's offset from the grate centre, grate 2 | P08, P09, P10 | 2.2, 2.2, 2.4 cm | 0.2 cm | `results/grate_crossings_2026-09-23.json` |
| the same, grate 3 | P19, P20, P21 | 7.4, 8.9, 9.2 cm | 1.8 cm | same |
| the same, grate 4 | P28, P29, P30 | 6.6, 6.4, 6.8 cm | 0.4 cm | same |
| the same, grate 5 | P37, P38, P39 | 14.2, 14.3, 13.7 cm | 0.6 cm | same |
| the same, grate 6 | P49, P50, P51 | 8.0, 7.5, 7.3 cm | 0.7 cm | same |
| The island's old end, angle to the road | P64 only | 13.3–14.0° across the four rulers; 11.7–17.3° (p10–p90) when the points a person gave are jittered | — | `results/dash_ruler_P64.json` |

What this means: where the same grate was photographed three times, the red line's offset
from its centre agrees to within 1.8 cm. The **size** of the box found around a grate does not
repeat (up to 17.4 cm apart on the same grate), so grate sizes are not published. The old end
of the island is seen from a usable angle on one photograph only; registering other photographs
onto it was tried with OpenCV 5's new matchers and failed (`docs/opencv5.md`, last section).

## 3. The same photograph, re-saved

When the number plates were masked, 23 photographs were re-encoded once (outside the masks,
pixels moved by 0.047 grey levels on average). `assess()` was run again on all 23:

| Speed limit assumed | Same findings as before | Changed |
|---|---|---|
| 30 km/h | 22 of 23 | F24 gains "taper too steep" |
| 50 km/h | 20 of 23 | F24, F29, F42 gain "taper too steep" |

What this means: the red-line, surface and works findings did not move; the taper verdict did.
That is the same weakness that made the published 10:1 a withdrawn figure. It is why the online
service measures every photograph four times (the bytes as received and three light
re-encodes) and reports a number only if at least 3 of the 4 agree.

## 4. How often it refuses, and whether it says why

`assess()`, the function behind the online service, on 20 photographs at full resolution
(10 from each field day, evenly spaced, 30 km/h; `results/agentic_evaluate_2026-09-23.json`):

| | |
|---|---|
| Red-line gap measured | 0 of 20 (these 20 are not the three close-ups where it can be measured) |
| Taper reported against design table 4.2.7 | 0 of 20 |
| Photographs with a "this photo can't answer that" action | 20 of 20 |
| Photographs with "open this box at full size and check" | 16 of 20 |
| Photographs with "request this document" | 15 of 20 |
| Every action carries its reason | yes |
| Median time per photograph | 116.7 s |

What this means: on an ordinary photograph it does not invent a measurement; it says what the
photograph cannot show and what to do next. Where a detector's count has been checked by a
person and found wrong, it asks a person to look instead (`docs/detectors.md`: for example, of
23 "red lines" opened, 13 were something else).

## Why no tape measure

Road markings have sizes fixed by regulation, so the markings themselves are the ruler, and
section 1 checks that ruler against them. The one physical reference is a card laid on the red
line at the kerb. Standing in the carriageway to measure is not safe for one person, and the
road stays open to traffic. The same limit decides which angles exist: the old end of the
island is seen from a usable angle on one photograph (P64), because that is where a rider
could stand.
