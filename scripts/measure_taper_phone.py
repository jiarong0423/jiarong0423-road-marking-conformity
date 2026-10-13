#!/usr/bin/env python3
"""The taper angle of the chevron from a handheld frame, against 表 4.2.7.

Point 4 of AXIS.md turns on a ratio, not on §171's 45 degrees: the
through-lane offset taper must be at least 16:1 at a design speed of
50 km/h, 23:1 at 60, and never shorter than 20 m (市區道路及附屬工程設計規範
113/09 修正, 表 4.2.7, docs/evidence.md L19). A ratio of L:1 is an angle
of atan(1/L): 16:1 is 3.58 degrees, 23:1 is 2.49, and the works-period
30 km/h figure of 5:1 is 11.31.

The chevron is the taper drawn on the ground. Its left edge diverges
from the lane at the taper angle; its right edge runs with the lane. So
the angle between the chevron's own two edges is the taper angle, and it
is a ground angle between two families of parallel lines - which
marking.vanishing measures from their vanishing points and K alone,
rotation-invariant, no pitch. No stripe is used: isolation/DETECTORS.md
records five stripe-selection strategies that did not converge.

The chevron polygon is found from the density of white paint, not from
a hand-set window: a 121 px box mean of the white mask, thresholded,
largest component, convex hull. Long white-edge segments whose midpoint
falls inside it are split into pencils by RANSAC; the two largest
pencils that meet at 1-15 degrees are the edges. The white mask stops at
38 % of frame height, because at 30 % the eaves and cables came through
as the largest pencils of all (drawn, 2026-09-22).

Refusals: each edge pencil at least 5 segments, jittered sd at most 1
degree, and the pair must be the two LARGEST pencils - a 14 degree
reading on F18 came from two short pencils at the far tip, and a 7.5 on
F19 from a five-member pencil with sd 8.

    /opt/anaconda3/bin/python3 scripts/measure_taper_phone.py --frames 17 37 40 --write
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
import measure_redline_gap as M                                  # noqa: E402
import measure_chevron_phone as C                                # noqa: E402
from marking.phone import taper_427, THRESHOLDS, SRC           # noqa: E402,F401  (moved 2026-09-23)



def run(path, frame_no):
    img = cv2.imread(str(path)); h, w = img.shape[:2]
    K, f35 = M.intrinsics(path, w, h)
    if K is None:
        return {"frame": frame_no, "ok": False, "why": "no focal length in EXIF"}
    core = taper_427(img, K, f35)
    if core.get("intrinsics"):
        return {"frame": frame_no, "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **core}
    return {"frame": frame_no, **core}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, nargs="+", default=[17, 18, 19, 20, 35, 36, 37, 38, 39, 40])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    files = sorted(glob.glob(M.FIELD)); outs = []
    for fr in a.frames:
        o = run(Path(files[fr - 1]), f"F{fr:02d}"); outs.append(o)
        if o["ok"]:
            t = o["thresholds"]
            print(f"  {o['frame']}: 漸變角 {o['taper_deg']}° sd {o['taper_uncertainty']['sd_deg']} 束 {[p['segments'] for p in o['edge_pencils']]} "
                  f"⇒ {o['taper_ratio']}:1  | 50 km/h 16:1 {'符合' if t['50 km/h']['meets'] else '不足'} · 30 km/h 5:1 {'符合' if t['30 km/h (works limit)']['meets'] else '不足'}")
        else:
            print(f"  {o['frame']}: 拒答 — {o['why']}")
    ok = [o for o in outs if o["ok"]]
    if ok:
        d = np.array([o["taper_deg"] for o in ok]); r = np.array([o["taper_ratio"] for o in ok])
        print(f"  → {len(ok)} 幀 漸變角 中位 {np.median(d):.2f}° 範圍 {d.min():.2f}–{d.max():.2f}  L/W 中位 {np.median(r):.1f}:1 範圍 {r.min():.1f}–{r.max():.1f}")
    if a.write:
        p = ROOT / "results" / "taper_phone.json"
        p.write_text(json.dumps({"frames": outs, "summary": None if not ok else {
            "frames_ok": [o["frame"] for o in ok], "taper_deg_median": round(float(np.median([o["taper_deg"] for o in ok])), 2),
            "taper_deg_min": round(min(o["taper_deg"] for o in ok), 2), "taper_deg_max": round(max(o["taper_deg"] for o in ok), 2),
            "ratio_median": round(float(np.median([o["taper_ratio"] for o in ok])), 1),
            "ratio_min": round(min(o["taper_ratio"] for o in ok), 1), "ratio_max": round(max(o["taper_ratio"] for o in ok), 1)},
            "source": SRC}, ensure_ascii=False, indent=1))
        print("  寫入", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
