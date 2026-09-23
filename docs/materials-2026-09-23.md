# Materials and methods (2026-09-23)

Every figure produced by image recognition carries its method printed underneath. This table lists, for each one, the script, what it checks, how it was verified, and its limits.

Evidence grades: **A** public document, quoted verbatim / **B** read by eye at full resolution / **C** measured by a program, with perturbation and self-checks / **D** rider's account or a calculation.

## 1. Image recognition

| # | Figure | Shows | Method (OpenCV) | Verified by | Limits | Script |
|---|---|---|---|---|---|---|
| M1 | `docs/figures/red-line-over-grates.jpg` (copy: `isolation/field-2026-09-23/cv_red_over_grates.jpg`) | The new red line is painted across the grates | Grate: grey threshold, morphological close/open, `minAreaRect`, bar periodicity by FFT. Red line: LAB a*, connected components, `fitLine`. Holes: circularity | 16 of 16 photos: the line's axis crosses the grate, 1–14 cm from its centre | Grate sizes do not converge and are not cited; grate 7 has no top-down photo | `isolation/field-2026-09-23/cv_evidence.py` |
| M2 | Not published: Google's Street View terms prohibit screenshots, downloads and data derived from Street View. Kept locally in the untracked `output/streetview-derived/` | Taper before repainting: 4.0–5.1 to 1 | Two edge recognisers must agree (outermost paint + EDLines, `cv2.ximgproc`); horizon computed twice (vertical vanishing point, and the request's known pitch); angle from the vanishing points and K | Unchanged under re-encoding and cropping; the two horizons agree within about 1° | Edge A is 2.8–3.9° off the road direction, unresolved | `isolation/overlay-2025/sv_taper.py`, `sv_check.py` |
| M3 | `docs/figures/taper-2026-after-erasure.jpg` (copy: `isolation/taper-recheck/consensus_f17_f40_method.jpg`) | Taper today: F40 about 12 to 1; F17 refused | As M2, horizon from the vertical vanishing point | 6 of 7 perturbations 11.7–12.3; one dropped by the self-check | One photo (F40) | `isolation/taper-recheck/consensus.py`, `horizon2.py` |
| M4 | `isolation/taper-recheck/f40_picks_method.jpg` | Why the withdrawn taper reading moved (diagnostic) | `HoughLinesP` + RANSAC grouping by vanishing point | — | The old method grouped different painted lines; the published 10 to 1 is withdrawn | `isolation/taper-recheck/draw_pick.py` |
| M5 | `isolation/field-2026-09-23/NOTES.md` §2–3 | Red line moved about 0.60 m (grate 2); fresh paint is 95–97 mm wide | Top-down LAB a*, row by row; a bank card (ID-1, 85.60 mm) compared at the same depth | The card checks the ruler | Top-down squareness not verified | `topdown_redline_gap.py`, `card_vs_redline.py` |
| M6 | `results/redline_gap_F3x.json` (2026-09-20) | Red line moved 0.63–0.68 m | Cross-ratio against a vanishing point; ruler = the red line's 10 cm width | Four encodings agree (endpoint probe) | — | `scripts/measure_redline_gap.py` |

## 2. Other materials

| # | Material | Shows | Grade |
|---|---|---|---|
| N1 | `docs/figures/redline-gutter-kerb-P22.jpg` | 1 old red line, 2 drain strip and grate, 3 new red line, 4 kerb (**labelled by hand**, not by a program) | B |
| N2 | `isolation/glare/sun_glare.py` | Heading to the bridge, about 86 days a year (mid-November to end of January, 07:00–08:00) the low sun is within ±25° of straight ahead | D (calculation; the threshold is this project's own) |
| N3 | `results/solid_line_extent.json` | 35 m solid line + 50 m island; seven grates at 8/16/28/44/58/74/82 m | B |
| N4 | `results/merge_window.json` | At 30 km/h the island takes 5.9 s; after 2.5 s reaction, 3.4 s remain | D (arithmetic) |
| N5 | `evidence/field-2026-09-23/MANIFEST.csv` | 64 photos; top, front and side shots of each grate, placed by timestamp | B |
| N6 | Street View June 2025, +15.7 m: a yellow "30" painted on the road | Speed limit 30 km/h | B |
| N7 | `docs/figures/schematic-85m.png` | Plan view drawn from this project's own measurements (no Street View pixels) | — |

## 3. Regulations (`docs/evidence.md`)

| Clause | Used for | Row |
|---|---|---|
| Road Traffic Signs, Markings and Signals Rules §169 | A red line belongs on the kerb; with no kerb, within 30 cm of the road edge | L2 |
| Same rules §183 | Where a red line is drawn, the edge line may be omitted: the red line marks the road's outer edge | L20 |
| Urban Road and Ancillary Works Design Standard §2(1) | A lane is the part of the road delimited by markings | L21 |
| Urban Road Design Specification, table 4.2.7 | Lane shift 5:1 at 30 km/h, 16:1 at 50 km/h | L19 |
| Highway Act §72(4) | Covers flush, skid resistance, 3 m straightedge ±0.6 cm | L22 |
| New Taipei road excavation review rules 6.0 | Patch joints, 3 m straightedge ±0.6 cm | `docs/source-ntpc-excavation-6.0.txt` |
