"""How many pixels the regulation's centimetres are worth, at each working size.

docs/what-changed-2026-09-21.md argues that the ensemble's second error -
measuring nine degraded cells and never the original - matters because the
regulation is written in centimetres. It quotes five pixel figures to make
the point: a 10 cm line at 20 m is 14.2 px in the original, 4.9 px at the
1400 px working size and 3.5 px at 1000 px, and the +/-6 mm width tolerance
is 0.85 px in the original and 0.21 px at 1000. (This script gives the
middle two to two places, 4.85 and 3.47, and the document now quotes them
that way so prose, registry and artifact cannot drift apart.)

None of those five was in results/ when this script was written, which by
standing rule 2 made all five unverified. They are arithmetic, so this is
the cheap end of registrable: the only measurement involved is the camera's
own EXIF and the photographs' own dimensions.

Scope, stated because rule 1 requires it:

  * the dimension census is the full field set, n=42, all of
    data/field-2026-09-20/*.jpg;
  * the focal length is one camera's EXIF - the POCO F7 Ultra that took
    all 42 - and not a measurement of anything on the road;
  * 20 m is a stated reference distance, not a measured one. Nothing here
    claims that any particular marking is 20 m away. The figure answers
    "what would a 10 cm line be worth at 20 m", which is what the prose
    asks.

The 35 mm-equivalent focal length is converted on the **diagonal**, the
convention behind the 24 mm EXIF value: a 35 mm frame is 36x24 mm, so its
diagonal is 43.267 mm, and

    f_px = f_35mm * image_diagonal_px / 43.267

Over 3072x4096 that is 24 * 5120 / 43.2666 = 2840.1 px, and a 10 cm object
at 20 m subtends 0.10/20 * 2840.1 = 14.2 px. The long-side convention
(f_px = f_35 * long_side / 36 = 2730.7) gives 13.7 px instead, so the
convention is load-bearing and is recorded in the output rather than left
to be guessed at.

    /opt/anaconda3/bin/python3 scripts/pixel_budget.py --write
"""

from __future__ import annotations

import argparse
import glob
import json
import math
from collections import Counter
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base as ExifBase

ROOT = Path(__file__).resolve().parents[1]
FIELD = ROOT / "data" / "field-2026-09-20"
OUT = ROOT / "results" / "pixel_budget.json"

# 35 mm still frame, the datum FocalLengthIn35mmFilm is expressed against.
FRAME_MM = (36.0, 24.0)
FRAME_DIAGONAL_MM = math.hypot(*FRAME_MM)

# The reference distance the prose uses. Not measured; stated.
REFERENCE_DISTANCE_M = 20.0

# The working sizes the ensemble actually uses, from src/marking/situation.py
# (WORK_PX). The prose quotes 1400 and 1000 of them.
WORK_PX = (1000, 1400, 1800)

# 道路交通標誌標線號誌設置規則. Declared inputs, not measurements: they are
# quoted from the regulation and this script derives from them rather than
# verifying them. Where each is transcribed, checked 2026-09-21:
#   §171's 20 / 30 / 15 cm   docs/markings-regulation.md, the table at L14-16
#   §169's 10 cm red line    docs/evidence.md L13 (「線寬⋯⋯一○公分」)
#   the ±6 mm width tolerance  docs/tolerances.md L10 and L86
REGULATION_CM = {
    "s171_stripe_width_cm": 20.0,
    "s171_gap_cm": 30.0,
    "s171_border_line_cm": 15.0,
    "s169_red_line_cm": 10.0,
    "width_tolerance_mm": 6.0,
}


def census(paths: list[Path]) -> dict:
    """Every field photograph's pixel dimensions. Full population or nothing."""
    sizes = Counter()

    for path in paths:
        with Image.open(path) as image:
            sizes[image.size] += 1

    return {
        "n": len(paths),
        "distinct_sizes": [
            {"width": w, "height": h, "count": c}
            for (w, h), c in sorted(sizes.items(), key=lambda kv: -kv[1])
        ],
        "uniform": len(sizes) == 1,
    }


def focal_px(path: Path, diagonal_px: float) -> dict:
    """f in pixels, from EXIF's 35 mm equivalent on the diagonal."""
    with Image.open(path) as image:
        exif = image.getexif()
        ifd = exif.get_ifd(0x8769)

    f35 = ifd.get(ExifBase.FocalLengthIn35mmFilm.value)
    f_mm = ifd.get(ExifBase.FocalLength.value)

    if f35 is None:
        raise SystemExit(f"{path} has no FocalLengthIn35mmFilm; "
                         f"the conversion below has nothing to stand on")

    return {
        "source": str(path.relative_to(ROOT)),
        "focal_length_35mm_equiv_mm": float(f35),
        "focal_length_mm": float(f_mm) if f_mm is not None else None,
        "convention": "diagonal: f_px = f_35mm * diagonal_px / 43.2666",
        "f_px": round(float(f35) * diagonal_px / FRAME_DIAGONAL_MM, 1),
        "f_px_long_side_convention": round(
            float(f35) * max(WIDTH_HEIGHT) / FRAME_MM[0], 1),
    }


def subtends_px(size_m: float, distance_m: float, f_px: float) -> float:
    """Small-angle: an object of `size_m` at `distance_m`, in pixels."""
    return size_m / distance_m * f_px


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help=f"write {OUT.relative_to(ROOT)}")
    args = parser.parse_args()

    paths = sorted(Path(p) for p in glob.glob(str(FIELD / "*.jpg")))

    if not paths:
        raise SystemExit(f"no photographs in {FIELD}; "
                         f"see docs/field-2026-09-20.md")

    dimensions = census(paths)

    if not dimensions["uniform"]:
        raise SystemExit("the field photographs are not one size; every "
                         "figure below assumes they are")

    global WIDTH_HEIGHT
    WIDTH_HEIGHT = (dimensions["distinct_sizes"][0]["width"],
                    dimensions["distinct_sizes"][0]["height"])
    diagonal_px = math.hypot(*WIDTH_HEIGHT)
    long_side = max(WIDTH_HEIGHT)

    camera = focal_px(paths[0], diagonal_px)
    f_px = camera["f_px"]

    red_line_m = REGULATION_CM["s169_red_line_cm"] / 100.0
    tolerance_m = REGULATION_CM["width_tolerance_mm"] / 1000.0

    def at(size_m: float, work_px: int | None) -> float:
        px = subtends_px(size_m, REFERENCE_DISTANCE_M, f_px)

        if work_px is not None:
            px *= work_px / long_side

        return round(px, 2)

    result = {
        "question": "what the regulation's centimetres are worth in pixels, "
                    "in the original photograph and at each working size",
        "reference_distance_m": REFERENCE_DISTANCE_M,
        "reference_distance_is": "stated, not measured - the distance the "
                                 "prose reasons about, not a distance to any "
                                 "particular marking",
        "field_photographs": dimensions,
        "camera": camera,
        "work_px": list(WORK_PX),
        "regulation_cm": REGULATION_CM,
        "regulation_cited_from": "道路交通標誌標線號誌設置規則 §169, §171. "
                                 "§171's 20/30/15 cm from "
                                 "docs/markings-regulation.md, §169's 10 cm "
                                 "from docs/evidence.md, the \u00b16 mm "
                                 "tolerance from docs/tolerances.md. "
                                 "Declared inputs, not measurements.",
        "red_line_10cm_at_20m_px": {
            "original": at(red_line_m, None),
            **{str(w): at(red_line_m, w) for w in WORK_PX},
        },
        "width_tolerance_6mm_at_20m_px": {
            "original": at(tolerance_m, None),
            **{str(w): at(tolerance_m, w) for w in WORK_PX},
        },
        "stripe_to_pitch_ratio": round(
            REGULATION_CM["s171_stripe_width_cm"]
            / (REGULATION_CM["s171_stripe_width_cm"]
               + REGULATION_CM["s171_gap_cm"]), 3),
        "stripe_to_pitch_ratio_is": "20 / (20 + 30) from §171. Scale-free, "
                                    "which is why it can be checked against a "
                                    "photograph with nothing annotated.",
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.write:
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(f"\nwrote {OUT.relative_to(ROOT)}")

    return 0


WIDTH_HEIGHT = (0, 0)

if __name__ == "__main__":
    raise SystemExit(main())
