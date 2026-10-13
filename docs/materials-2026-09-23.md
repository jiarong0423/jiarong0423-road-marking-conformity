# Materials and methods (2026-09-23)

Every figure produced by image recognition carries its method printed underneath. This table lists, for each one, the script, what it checks, how it was verified, and its limits.

Evidence grades: **A** public document, quoted verbatim / **B** read by eye at full resolution / **C** measured by a program, with perturbation and self-checks / **D** rider's account or a calculation.

## 1. Image recognition

| # | Figure | Shows | Method (OpenCV) | Verified by | Limits | Script |
|---|---|---|---|---|---|---|
| M1 | `docs/figures/red-line-over-grates.jpg` (copy: `isolation/field-2026-09-23/cv_red_over_grates.jpg`) | The new red line is painted across the grates | Grate: grey threshold, morphological close/open, `minAreaRect`, bar periodicity by FFT. Red line: LAB a*, connected components, `fitLine`. Holes: circularity | All 16 top-down photos of grates 1–6: the line's axis crosses the grate, 1.0–14.3 cm from its centre | Grate sizes do not converge and are not cited; grate 7 has no top-down photo | `isolation/field-2026-09-23/cv_evidence.py` |
| M2 | Not published: Google's Street View terms prohibit screenshots, downloads and data derived from Street View | The taper before repainting (withdrawn) | — | — | — | — |
| M3 | `docs/figures/taper-2026-after-erasure.jpg` (copy: `isolation/taper-recheck/consensus_f17_f40_method.jpg`) | Taper today: F40 about 12 to 1; F17 refused | Two line recognisers that must agree (RANSAC on white paint, EDLines); horizon from the vertical vanishing point | 6 of 7 perturbations 11.7–12.3; one dropped by the self-check | One photo (F40) | `isolation/taper-recheck/consensus.py`, `horizon2.py` |
| M4 | `isolation/taper-recheck/f40_picks_method.jpg` | Why the withdrawn taper reading moved (diagnostic) | `HoughLinesP` + RANSAC grouping by vanishing point | — | The old method grouped different painted lines; the published 10 to 1 is withdrawn | `isolation/taper-recheck/draw_pick.py` |
| M5 | `isolation/field-2026-09-23/topdown_redline_gap.py`, `card_vs_redline.py` | Top-down attempt at grate 2 (not verified square to the road, not used for the published gap); fresh paint is about 95–97 mm wide | Top-down LAB a*, row by row; a card of ID-1 size (85.60 mm) compared at the same depth; P55 and P56 read, P59 failed (`card_vs_redline.json`) | The card checks the ruler | Top-down squareness not verified | `topdown_redline_gap.py`, `card_vs_redline.py` |
| M6 | `results/redline_gap_F30.json`, `F31`, `F32` (2026-09-20) | Red line moved 0.63–0.68 m | Cross-ratio against a vanishing point; ruler = the red line's 10 cm width | Single stations 0.61–0.72 m; the ruler assumes the legal 10 cm | — | `scripts/measure_redline_gap.py` |
| M7 | `docs/figures/erased-triangle-P64.jpg`, `docs/figures/erased-triangle-P64-topdown.jpg` | The island's old far end, painted over (red), where today's stripes stop (white), the old faint edge and today's edge line (green), one lane dash (yellow) | Top-down reprojection with the lane dashes as the ruler; paint share per row; HoughLinesP; contourArea | A lane dash reads 4.1 m against §182's 4 m | Dash centres, the old edge's ends and the tip line given by a person; ±10% | `scripts/erased_triangle.py` |

## 2. Other materials

| # | Material | Shows | Grade |
|---|---|---|---|
| N1 | `docs/figures/redline-gutter-kerb-P22.jpg` | 1 old red line, 2 drain strip and grate, 3 new red line, 4 kerb (**labelled by hand**, not by a program) | B |
| N5 | `evidence/field-2026-09-23/MANIFEST.csv` | 64 photos; top, front and side shots of each grate, placed by timestamp | B |
| N7 | `docs/figures/schematic.png` | Schematic drawn by the author; no distances along the road; no Street View pixels or Street View distances | — |

## 3. Regulations (`docs/evidence.md`)

| Clause | Used for | Row |
|---|---|---|
| Road Traffic Signs, Markings and Signals Rules §169 | A red line belongs on the kerb; with no kerb, within 30 cm of the road edge | L2 |
| Same rules §183 | Where a red line is drawn, the edge line may be omitted: the red line marks the road's outer edge | L20 |
| Urban Road and Ancillary Works Design Standard §2(1) | A lane is the part of the road delimited by markings | L21 |
| Urban Road Design Specification, table 4.2.7 | Reference only (written for through-lane shifts at turning lanes): 5:1 at 30 km/h, 16:1 at 50 km/h | L19 |
| Highway Act §72(4) | Covers restored flush; a skid-resistance floor for covers; repaired pavement within ±0.6 cm on a 3 m straightedge (whether that limit applies to these grates is not established) | L22 |
| New Taipei road excavation review rules 6.0 | Patch joints, 3 m straightedge ±0.6 cm | `docs/source-ntpc-excavation-6.0.txt` |
