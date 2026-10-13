#!/usr/bin/env python3
"""The gap between the two kerbside red lines, in metres, from one phone photograph.

F31 shows two red lines: one on the asphalt, worn to pink; one on the
concrete gutter strip, intact, running through the row of drain covers.
This measures the ground distance from the intact line's inner edge to the
worn line's centre, using the intact line's own width - §169, 一○公分 -
as the ruler, and the cross-ratio construction in `marking.ruler`.

Nothing here needs the camera's pitch, roll or height. What it needs:

    K        from EXIF (FocalLengthIn35mmFilm), as assess_field.py reads it
    v_road   RANSAC over long lower-frame segments, refined by SVD
    v_vert   a 1-D vote along v_road's polar line - every near-vertical
             segment meets that line at one candidate, and the weighted
             mode is taken. Two-dimensional RANSAC on verticals returned
             a consensus 57 degrees from perpendicular on this frame;
             the polar line makes perpendicularity a constraint, not a
             check that fails afterwards.
    v_cross  K (n x d_road), n = K^-1 v_vert, d_road = K^-1 v_road

and then at each station: the intact line's two edges from a saturated red
mask (A, B), the worn line's centre from a faint red mask searched near
where the worn line's fitted axis predicts it (C). No extrapolation: a
station with no worn paint on the cross-road line is refused, not filled.

Error budget, measured on synthetic ground truth (scratch, 2026-09-22):
  roll error in n of 1/3/5/8 deg  ->  +0.5/+1.4/+2.4/+4.0 cm on 58 cm,
                                      identical at every depth
  v_road error up to 300 px       ->  0.00 cm at every depth
  1.5 px jitter on A, B, C        ->  about +-2 cm (reported per station)
  a 10 cm ruler at 3 m is ~90 px; +-1 px per endpoint is +-4 cm at 95 %

    /opt/anaconda3/bin/python3 scripts/measure_redline_gap.py --write
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from marking.phone import K_from_f35, RULER_M, RULER_SRC  # noqa: E402,F401

# The 42 photographs of 2026-09-20. evidence/ holds them with five plates redacted
# (MANIFEST.csv `redacted`); none of the five is a frame this script publishes.
# RMC_FIELD_GLOB points it at unredacted originals kept outside the repository.
import os  # noqa: E402
FIELD = os.environ.get("RMC_FIELD_GLOB", str(ROOT / "evidence" / "field-2026-09-20" / "IMG_*.jpg"))


# The helpers and the measurement itself live in src/marking/phone.py
# (moved 2026-09-23 so the endpoint image ships them). Re-exported here
# because measure_chevron_phone.py and draw_recognition.py use them as M.*.
from marking.phone import (ang, seglen, dang, hough, hline, road_vp,  # noqa: E402,F401
                           vertical_vp, red_masks, axis_of, components, runs_on,
                           redline_gap)


def intrinsics(path, w, h):
    d = {TAGS.get(k, k): v for k, v in (Image.open(path)._getexif() or {}).items()}
    f35 = d.get("FocalLengthIn35mmFilm")
    if not f35:
        return None, None
    return K_from_f35(w, h, f35), f35


def run(path, frame_no):
    img = cv2.imread(str(path)); h, w = img.shape[:2]
    K, f35 = intrinsics(path, w, h)
    if K is None:
        return {"frame": frame_no, "ok": False, "why": "no focal length in EXIF"}
    core = redline_gap(img, K, f35)
    if "file" not in core and core.get("intrinsics"):
        return {"frame": frame_no, "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **core}
    return {"frame": frame_no, **core}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=int, default=31)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    files = sorted(glob.glob(FIELD))
    out = run(Path(files[a.frame - 1]), f"F{a.frame:02d}")
    if out.get("summary"):
        s = out["summary"]
        for st in out["stations"]:
            print(f"  y≈{st['y_px']}: " + (f"拒答 — {st['refused']}" if "refused" in st else
                  f"尺 {st['ruler_px']:.0f}px  邊→舊線中心 {st['edge_to_worn_centre_px']:.0f}px  "
                  f"仿射 {st['affine_m']:.3f}  修正 {st['gap_m']:.3f} m  5–95% {st['gap_m_5_95']}"))
        print(f"  → {s['stations_measured']} 站  中位 {s['median_m']} m  範圍 {s['min_m']}–{s['max_m']}  "
              f"末-首 {s['last_minus_first_m']:+.3f}  仿射中位 {s['affine_median_m']}")
    else:
        print("  拒答:", out.get("why"))
    if a.write:
        p = ROOT / "results" / f"redline_gap_{out['frame']}.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1)); print("  寫入", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
