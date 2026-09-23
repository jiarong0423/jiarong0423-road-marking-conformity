"""Find a chevron by what it is: a periodic pattern, not a set of bars.

§171 defines the marking as 斜紋線寬二○公分, 間隔三○公分, 斜四五度 - a
20 cm stripe, a 30 cm gap, at 45 degrees. That is a grating. The
project's extractor looks for isolated bright bars against dark flanks,
which is what a lane line is and what a chevron is not: a chevron stripe's
flanks are the neighbouring stripes.

So ask the question the regulation asks. Over a window, is there one
dominant spatial frequency, and is its direction about 45 degrees from
the road? A Gabor bank answers both at once, and a 2D DFT of the window
gives the period directly.

This does not decide anything. It measures whether the signal is there,
over every photograph, so that a later decision can be built on a number
rather than on the expectation that it should work.

Writes results/chevron_periodic.json.

    python3 scripts/chevron_periodic.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def gabor_bank(periods=(6, 9, 13, 19, 28), n_theta=12):
    bank = []
    for p in periods:
        sigma = 0.56 * p
        k = int(2 * round(3 * sigma) + 1)
        for i in range(n_theta):
            th = math.pi * i / n_theta
            bank.append((p, math.degrees(th),
                         cv2.getGaborKernel((k, k), sigma, th, p, 0.6, 0,
                                            ktype=cv2.CV_32F)))
    return bank


BANK = gabor_bank()


def periodic_field(gray):
    """Per pixel: the strongest Gabor response, its period and direction."""
    g = gray.astype(np.float32)
    best = np.full(g.shape, -1.0, np.float32)
    per = np.zeros(g.shape, np.float32)
    ang = np.zeros(g.shape, np.float32)
    for p, deg, k in BANK:
        r = np.abs(cv2.filter2D(g, cv2.CV_32F, k))
        take = r > best
        best[take], per[take], ang[take] = r[take], p, deg
    return best, per, ang


def main() -> int:
    paths = []
    idx = ROOT / "results" / "field_index_2026-09-20.csv"
    for row in csv.DictReader(idx.open()):
        p = ROOT / "data" / "field-2026-09-20" / row["file"]
        if p.exists():
            paths.append((row["no"], p))
    for name in ("e1_2022-11", "e2_2024-09", "e3_2025-06"):
        p = ROOT / "output" / "epochs" / f"{name}.jpg"
        if p.exists():
            paths.append((name, p))

    rows = []
    for label, path in paths:
        im = cv2.imread(str(path))
        if im is None:
            continue
        f = 1000 / max(im.shape[:2])
        if f < 1:
            im = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[:, :, 0]
        resp, per, ang = periodic_field(g)
        h, w = g.shape
        lower = np.zeros(g.shape, bool)
        lower[int(h * 0.45):] = True     # the road is below the horizon
        thr = float(np.percentile(resp[lower], 97))
        strong = lower & (resp >= thr)
        if strong.sum() < 200:
            continue
        rows.append({
            "id": label,
            "strong_px": int(strong.sum()),
            "response_p97": round(thr, 1),
            "response_median_lower": round(float(np.median(resp[lower])), 1),
            "contrast": round(thr / max(float(np.median(resp[lower])), 1e-6), 2),
            "period_px_median": float(np.median(per[strong])),
            "direction_deg_median": round(float(np.median(ang[strong])), 1),
            "direction_deg_iqr": round(float(np.percentile(ang[strong], 75)
                                             - np.percentile(ang[strong], 25)), 1),
        })

    c = np.array([r["contrast"] for r in rows])
    out = {
        "question": "is a chevron's periodicity measurable, and how "
                    "consistently",
        "method": "Gabor bank over 5 periods and 12 orientations on the L* "
                  "channel; per pixel the strongest response, its period and "
                  "its direction. The top 3% of responses below the horizon "
                  "are taken as the periodic population. Nothing is "
                  "classified; this counts whether the signal exists.",
        "n_images": len(rows),
        "contrast_median": round(float(np.median(c)), 2),
        "contrast_min": round(float(c.min()), 2),
        "contrast_max": round(float(c.max()), 2),
        "note": "contrast is the 97th percentile response over the median "
                "response below the horizon. A frame with no periodic "
                "structure has a small one.",
        "per_image": rows,
    }
    (ROOT / "results" / "chevron_periodic.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print(f"n = {len(rows)} images")
    print(f"  periodic contrast  median {out['contrast_median']}  "
          f"range {out['contrast_min']}-{out['contrast_max']}")
    import collections
    d = collections.Counter(int(r["direction_deg_median"]//15)*15 for r in rows)
    print("  dominant direction, 15-degree bins:")
    for k in sorted(d):
        print(f"    {k:>3}-{k+15:>3}°  {d[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
