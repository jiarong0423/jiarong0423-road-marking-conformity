#!/usr/bin/env python3
"""The chevron on a handheld frame: its ground angle to the road, and whether
its stripes can serve as a ruler ALONG the road.

Point 4 of AXIS.md needs lengths along the road - §155's straight run of at
least 20 m at the end of a 緩和區間線, the spacing of reductions. The
cross-road ruler (§169's 10 cm line, scripts/measure_redline_gap.py) does
not reach along the road. §171's stripes might: 線寬二○公分, 間隔三○公分,
so a 50 cm pitch perpendicular to the stripes, and a pitch of
0.50 / sin(theta) along the road, theta being the stripes' ground angle to
the road.

theta is measured here, per frame, with the rotation-invariant construction
in marking.vanishing - the angle between K^-1 v_stripe and K^-1 v_road -
so no datum is assumed and no pitch is needed. isolation/DETECTORS.md
records why the OLD taper reading on phone frames was worthless: it was
set by the parameters. This one carries its own spread from jittered
segments, and the equal-spacing test below is the check that the ruler is
a ruler.

Equal spacing: along a line through v_road, consecutive stripe crossings
A, B, C should give D(A,C)/D(A,B) = 2 on the ground. That ratio is the
cross-ratio with v_road, exact under projection (marking.ruler). Its
median over every crossing found is the answer; 2.00 says the stripes are
evenly spaced on the ground and the vanishing point is right, either
failing would move it.

    /opt/anaconda3/bin/python3 scripts/measure_chevron_phone.py --frame 37 --write
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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import measure_redline_gap as M                                     # noqa: E402
from marking.ruler import length_ratio                              # noqa: E402
from marking.vanishing import angle_between, angle_uncertainty, vanishing_point  # noqa: E402

PITCH_M, PITCH_SRC = 0.50, "設置規則 §171 斜紋線寬二○公分、間隔三○公分"


from marking.phone import ransac_vp  # noqa: E402,F401  (moved 2026-09-23)


def run(path, frame_no):
    img = cv2.imread(str(path)); h, w = img.shape[:2]
    K, f35 = M.intrinsics(path, w, h)
    if K is None:
        return {"frame": frame_no, "ok": False, "why": "no focal length in EXIF"}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Road: long segments only. With the default 180 px floor the RANSAC on
    # this frame locked onto the reinstated asphalt's texture - 923
    # candidates, 60 % of their length in one bearing bin, condition 0.6 -
    # and returned a point inside the lower frame. Road lines are long and
    # meet near the horizon; both are required here.
    long = [s for s in M.hough(gray, 100, 450, 14)
            if max(s[1], s[3]) > h * 0.40 and M.seglen(s) > 450
            and 8 < M.ang(s) < 172 and abs(M.ang(s) - 90) > 10]
    if len(long) < 4:
        return {"frame": frame_no, "ok": False, "why": f"only {len(long)} long segments"}
    road, road_inl = ransac_vp(long, 6.0, (0, h * 0.55))
    if road is None:
        return {"frame": frame_no, "ok": False, "why": "no road vanishing point in the horizon band"}
    v_road, road_cond = road

    # Stripes: mid-length segments at a chevron bearing, in the left band
    # where the chevron sits on these frames.
    stripes = [s for s in M.hough(gray, 40, 60, 6)
               if 25 < M.ang(s) < 70 and 60 <= M.seglen(s) <= 400
               and max(s[0], s[2]) < w * 0.62
               and h * 0.30 < min(s[1], s[3]) and max(s[1], s[3]) < h * 0.66]
    if len(stripes) < 6:
        return {"frame": frame_no, "ok": False, "why": f"only {len(stripes)} stripe segments"}
    stripe, stripe_inl = ransac_vp(stripes, 5.0)
    v_stripe, stripe_cond = stripe

    theta = angle_between(K, np.append(v_stripe, 1.0), np.append(v_road, 1.0))
    unc = angle_uncertainty(K, stripe_inl, road_inl, trials=200, jitter_px=1.5, seed=0)
    pitch_along = PITCH_M / math.sin(math.radians(theta))

    # The equal-spacing test further down validates v_road and nothing
    # else: crossings along the road are evenly spaced whatever v_stripe
    # was found, so it cannot catch a wrong theta. On F18 eight "stripe"
    # inliers gave 11 degrees and on F20 three gave 73 with sd 7.85, and
    # both passed equal spacing at 2.05 and 2.03. theta therefore needs
    # its own refusals: enough stripe inliers, a tight spread, and the
    # jittered band containing the point estimate.
    lo, hi = unc.get("p2.5", theta), unc.get("p97.5", theta)
    theta_refused = None
    if len(stripe_inl) < 12:
        theta_refused = f"only {len(stripe_inl)} stripe inliers; 12 needed"
    elif unc.get("sd_deg", 99) > 2.0:
        theta_refused = f"stripe-to-road spread sd {unc['sd_deg']:.2f} deg exceeds 2.0"
    elif not (lo - 0.5 <= theta <= hi + 0.5):
        theta_refused = f"point estimate {theta:.2f} outside its own jittered band {lo:.2f}-{hi:.2f}"

    # Equal spacing along the road.
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white = cv2.inRange(hsv, (0, 0, int(lv)), (180, 60, 255)); white[:int(h * 0.30)] = 0
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    ratios, lines_used = [], 0
    for y0 in np.linspace(h * 0.34, h * 0.64, 14):
        p0 = np.array([0.0, y0]); dd = v_road - p0; L = np.linalg.norm(dd); dd /= L
        runs = [r for r in M.runs_on(white, p0, dd, 0, L * 0.75, w, h, min_run=8, join=3)
                if 8 <= r[1] - r[0] <= 300]
        if len(runs) < 4:
            continue
        lines_used += 1
        mids = [(r[0] + r[1]) / 2 for r in runs]
        for i in range(len(mids) - 2):
            a, b, c = [p0 + dd * t for t in mids[i:i + 3]]
            r = length_ratio(a, b, c, v_road)
            if r is not None:
                ratios.append(float(r))
    rr = np.array(ratios) if ratios else None

    # A second, independent road point: the one that makes the stripe
    # crossings equally spaced. §171 fixes the stripes' pitch, so along
    # any line through the true road point the ground multiples of the
    # first pitch step by exactly one. The RANSAC point on this frame took
    # 9 long segments, one of them the reinstated asphalt's edge, and the
    # multiples stepped by 1.11 - not a missed stripe (that steps by 2) but
    # a monotone drift, which is what a wrong vanishing point does. Solved
    # for, the point moved 1064 px and theta by 7.4 degrees, while the
    # jittered sd had said 0.39. The sd measures pixel noise, not which
    # lines were chosen. So both estimates are reported and the frame is
    # refused when they disagree.
    chains = []
    for y0 in np.linspace(h * 0.34, h * 0.64, 14):
        p0 = np.array([0.0, y0]); dd = v_road - p0; L = np.linalg.norm(dd); dd /= L
        runs = [r for r in M.runs_on(white, p0, dd, 0, L * 0.80, w, h, min_run=8, join=3)
                if 8 <= r[1] - r[0] <= 300]
        if len(runs) < 6:
            continue
        mids = [(r[0] + r[1]) / 2 for r in runs]
        ok = []
        for i in range(1, len(mids) - 1):
            r = length_ratio(p0 + dd * mids[i - 1], p0 + dd * mids[i], p0 + dd * mids[i + 1], v_road)
            ok.append(r is not None and 1.6 <= r <= 2.5)
        best_run, cur, st = (0, 0), 0, 0
        for k, v in enumerate(ok):
            if v:
                if cur == 0:
                    st = k
                cur += 1
                best_run = max(best_run, (cur, st))
            else:
                cur = 0
        if best_run[0] >= 4:
            i0, i1 = best_run[1], best_run[1] + best_run[0] + 1
            chains.append([p0 + dd * mids[k] for k in range(i0, i1 + 1)])

    def drift(v):
        sl = []
        for pts in chains:
            m = [length_ratio(pts[0], pts[1], q, v) for q in pts]
            if any(x is None for x in m):
                return None
            sl.append(np.polyfit(np.arange(len(m)), m, 1)[0])
        return float(np.mean(np.abs(np.array(sl) - 1.0))), [float(x) for x in sl]

    v_eq, theta_eq, eq_info = None, None, {"chains": len(chains)}
    if len(chains) >= 2 and drift(v_road) is not None:
        best = (drift(v_road)[0], v_road)
        for step, span in ((200, 3000), (50, 600), (10, 120), (2, 24)):
            c = best[1]
            for dx in np.arange(-span, span + 1, step):
                for dy in np.arange(-span, span + 1, step):
                    v = c + np.array([dx, dy]); d = drift(v)
                    if d and d[0] < best[0]:
                        best = (d[0], v)
        v_eq = best[1]
        theta_eq = angle_between(K, np.append(v_stripe, 1.0), np.append(v_eq, 1.0))
        eq_info.update({"v_road_px": [round(float(x), 1) for x in v_eq],
                        "slopes": [round(x, 3) for x in drift(v_eq)[1]],
                        "ransac_slopes": [round(x, 3) for x in drift(v_road)[1]],
                        "moved_px": round(float(np.linalg.norm(v_eq - v_road)), 1),
                        "stripe_to_road_deg": round(theta_eq, 2)})
    if theta_refused is None:
        if theta_eq is None:
            theta_refused = "no second road-point estimate: fewer than 2 stripe chains"
        elif abs(theta_eq - theta) > 3.0:
            theta_refused = (f"two road points disagree: RANSAC gives {theta:.2f} deg, "
                             f"equal spacing gives {theta_eq:.2f}; the difference is the "
                             f"uncertainty the jitter sd does not see")

    return {
        "frame": frame_no, "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "ok": rr is not None and len(rr) >= 12 and theta_refused is None,
        "why": theta_refused if theta_refused else (None if (rr is not None and len(rr) >= 12) else
               f"only {0 if rr is None else len(rr)} stripe-crossing ratios; 12 needed for a median to mean anything"),
        "intrinsics": {"f35_mm": f35, "focal_px": round(float(K[0, 0]), 1), "size": [w, h]},
        "v_road": {"px": [round(float(x), 1) for x in v_road], "candidates": len(long),
                   "inliers": len(road_inl), "condition": round(road_cond, 4),
                   "note": "long segments (>450 px) meeting in the upper 55 % of the frame"},
        "v_stripe": {"px": [round(float(x), 1) for x in v_stripe], "candidates": len(stripes),
                     "inliers": len(stripe_inl), "condition": round(stripe_cond, 4)},
        "stripe_to_road_deg": round(theta, 2),
        "stripe_to_road_uncertainty": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in unc.items()},
        "datum": "the road's own vanishing direction on this frame; not §171's unnamed datum, "
                 "and not the chevron boundary the Street View figure used",
        "road_point_by_equal_spacing": eq_info,
        "pitch": {"perpendicular_m": PITCH_M, "source": PITCH_SRC,
                  "along_road_m": round(pitch_along, 4),
                  "formula": "0.50 / sin(stripe_to_road_deg)"},
        "equal_spacing": None if rr is None else {
            "sampling_lines": lines_used, "ratios": len(rr),
            "median": round(float(np.median(rr)), 3), "expected": 2.0,
            "iqr": [round(float(np.percentile(rr, 25)), 3), round(float(np.percentile(rr, 75)), 3)],
            "reading": "consecutive stripe crossings A,B,C along the road: D(A,C)/D(A,B) on the ground",
            "validates": "v_road only - not theta, see the refusals on stripe_to_road"},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=int, default=37)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    files = sorted(glob.glob(M.FIELD))
    out = run(Path(files[a.frame - 1]), f"F{a.frame:02d}")
    if out.get("ok"):
        u = out["stripe_to_road_uncertainty"]; e = out["equal_spacing"]
        print(f"  v_road {out['v_road']['px']} ({out['v_road']['inliers']}/{out['v_road']['candidates']}, cond {out['v_road']['condition']})")
        print(f"  v_stripe {out['v_stripe']['px']} ({out['v_stripe']['inliers']}/{out['v_stripe']['candidates']}, cond {out['v_stripe']['condition']})")
        print(f"  斜紋對路 {out['stripe_to_road_deg']}°  95%: {u.get('p2.5')}–{u.get('p97.5')}  sd {u.get('sd_deg')}")
        print(f"  沿路節距 {out['pitch']['along_road_m']} m   等距檢驗 {e['ratios']} 個比值 中位 {e['median']} (期望 2.0) IQR {e['iqr']}")
    else:
        print("  拒答:", out.get("why"), "" if out.get("equal_spacing") is None else out["equal_spacing"])
    if a.write:
        p = ROOT / "results" / f"chevron_phone_{out['frame']}.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1)); print("  寫入", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
