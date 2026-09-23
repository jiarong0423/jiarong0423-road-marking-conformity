"""Does the ground plane fit, and does its own held-out check say so?

Stage 2 of docs/architecture-2026-09-21.md recovers the horizon from two
of the markings' vanishing directions. The document specifies the
evaluation and specifies it to be non-circular: fit from two families,
predict a third that was never in the objective, and report how far off
the prediction lands. A fit cannot suppress a residual it never saw.

This runs both over every field photograph, and beside them an estimate
of the horizon that uses no line fitting at all - the first row from the
top that stops being sky. That estimate is crude and is not ground
truth; it is there so that a fit which is wrong by a thousand pixels
cannot look fine.

Writes results/plane_holdout.json.

    python3 scripts/plane_holdout.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]   # repo root: this file is isolation/scripts/
# isolation/src FIRST: these scripts serve the isolated modules, and
# isolation/src/marking/__init__.py extends the package path to the real
# src/marking so the shared parts still resolve. Moving these scripts
# into isolation/ on 2026-09-21 broke all three by leaving ROOT and this
# path pointing one directory too shallow; none was run afterwards.
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "isolation" / "src"))
from marking.pipeline import run                      # noqa: E402


def sky_edge(image, blur=5, sky_frac=0.35):
    """The first row that stops being mostly sky. Not ground truth."""
    hsv = cv2.cvtColor(cv2.GaussianBlur(image, (0, 0), blur), cv2.COLOR_BGR2HSV)
    sky = ((hsv[:, :, 2] > 150) & (hsv[:, :, 1] < 70)).mean(axis=1)
    below = np.where(sky < sky_frac)[0]
    return int(below[0]) if len(below) else None


def main() -> int:
    rows = list(csv.DictReader(
        open(ROOT / "results" / "field_index_2026-09-20.csv")))
    out = []
    for r in rows:
        p = ROOT / "evidence" / "field-2026-09-20" / r["file"]
        if not p.exists():
            continue
        im = cv2.imread(str(p))
        res, _, _ = run(im, path=str(p))
        pl = res["plane"]
        est = sky_edge(im)
        row = {"no": r["no"], "segments": res["segments"],
               "sky_edge_px": est, "height_px": im.shape[0]}
        if pl is None:
            row["plane"] = None
        else:
            row.update({
                "horizon_y_px": round(pl["horizon_y_px"], 1),
                "families": pl["families"],
                "support": pl["support_segments"],
                "held_out_offset_deg": (pl["held_out_check"] or {}).get("offset_deg"),
                "vs_sky_edge_px": (round(pl["horizon_y_px"] - est, 1)
                                   if est is not None else None),
            })
        out.append(row)

    fitted = [r for r in out if r.get("horizon_y_px") is not None]
    ho = np.array([r["held_out_offset_deg"] for r in fitted
                   if r.get("held_out_offset_deg") is not None])
    dv = np.array([abs(r["vs_sky_edge_px"]) for r in fitted
                   if r.get("vs_sky_edge_px") is not None])
    summary = {
        "question": "does stage 2's plane fit hold, by its own held-out check",
        "method": "fit the horizon from two vanishing directions of the "
                  "paint, predict a third family that was not in the fit, "
                  "and report the angular offset of that prediction. Beside "
                  "it, |horizon - the first non-sky row|, which uses no line "
                  "fitting and is a sanity bound rather than truth.",
        "n_photographs": len(out),
        "n_with_a_plane": len(fitted),
        "held_out_offset_deg": {
            "n": int(ho.size),
            "median": round(float(np.median(ho)), 2) if ho.size else None,
            "min": round(float(ho.min()), 2) if ho.size else None,
            "max": round(float(ho.max()), 2) if ho.size else None,
            "under_2_deg": int((ho < 2).sum()) if ho.size else 0,
            "over_20_deg": int((ho > 20).sum()) if ho.size else 0,
        },
        "abs_offset_from_sky_edge_px": {
            "n": int(dv.size),
            "median": round(float(np.median(dv)), 0) if dv.size else None,
            "max": round(float(dv.max()), 0) if dv.size else None,
            "within_300_px": int((dv < 300).sum()) if dv.size else 0,
        },
        "per_photograph": out,
    }
    (ROOT / "results" / "plane_holdout.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))
    h = summary["held_out_offset_deg"]
    d = summary["abs_offset_from_sky_edge_px"]
    print(f"n = {summary['n_photographs']}, a plane on {summary['n_with_a_plane']}")
    print(f"  held-out offset: median {h['median']}°  range {h['min']}-{h['max']}°"
          f"  under 2° on {h['under_2_deg']}  over 20° on {h['over_20_deg']}")
    print(f"  |horizon - sky edge|: median {d['median']} px  max {d['max']} px"
          f"  within 300 px on {d['within_300_px']} of {d['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
