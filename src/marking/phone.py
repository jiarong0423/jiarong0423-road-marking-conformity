"""Measurements from one handheld photograph, as the endpoint runs them.

Moved here from scripts/measure_redline_gap.py, measure_chevron_phone.py
and measure_taper_phone.py on 2026-09-23 so that aws/Dockerfile, which
copies src/ only, ships them. The scripts now call these functions and
add the file identity (name, sha256) themselves; the numbers are the
same bytes-for-bytes (checked against results/ at the move).

Each function takes the decoded image and the intrinsic matrix K. The
scripts build K from EXIF (FocalLengthIn35mmFilm); the endpoint builds it
from the caller's fov_deg with `K_from_fov`. No PIL here: the Lambda image
installs OpenCV and NumPy only.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from marking.ruler import length_ratio, measure
from marking.vanishing import angle_between, angle_uncertainty, vanishing_point

RULER_M, RULER_SRC = 0.10, "道路交通標誌標線號誌設置規則 §169 紅實線 線寬一○公分"
THRESHOLDS = {"50 km/h": 16.0, "60 km/h": 23.0, "30 km/h (works limit)": 5.0}
SRC = "市區道路及附屬工程設計規範 113/09/12 修正 表 4.2.7 直行車道偏移漸變長度及縮減車道寬度漸變比例 (docs/evidence.md L19)"


def K_from_fov(w: int, h: int, fov_deg: float) -> np.ndarray:
    """Pinhole K from the horizontal field of view, principal point centred."""
    f = (w / 2) / math.tan(math.radians(fov_deg) / 2)
    return np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])


def K_from_f35(w: int, h: int, f35: float) -> np.ndarray:
    """Pinhole K from the EXIF 35 mm-equivalent focal length (43.267 mm diagonal)."""
    f = f35 * math.hypot(w, h) / 43.267
    return np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])


def ang(s):
    return math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) % 180


def seglen(s):
    return math.hypot(s[2] - s[0], s[3] - s[1])


def dang(a, b):
    return min(abs(a - b), 180 - abs(a - b))

def hough(gray, thr, minlen, gap):
    e = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 120)
    L = cv2.HoughLinesP(e, 1, np.pi / 1440, thr, minLineLength=minlen, maxLineGap=gap)
    return [] if L is None else [tuple(map(float, s)) for s in L.reshape(-1, 4)]


def hline(s):
    l = np.cross([s[0], s[1], 1.0], [s[2], s[3], 1.0])
    return l / np.linalg.norm(l[:2])


def road_vp(gray, h, seed=0):
    cand = [s for s in hough(gray, 80, 180, 14)
            if max(s[1], s[3]) > h * 0.45 and seglen(s) > 220
            and 8 < ang(s) < 172 and abs(ang(s) - 90) > 10]
    lines = [hline(s) for s in cand]
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(4000):
        i, j = rng.choice(len(cand), 2, replace=False)
        v = np.cross(lines[i], lines[j])
        if abs(v[2]) < 1e-9:
            continue
        v = v / v[2]
        inl = np.array([abs(l @ v) for l in lines]) < 6.0
        sc = sum(seglen(cand[k]) for k in np.nonzero(inl)[0])
        if best is None or sc > best[0]:
            best = (sc, inl)
    segs = [cand[i] for i in np.nonzero(best[1])[0]]
    v, cond = vanishing_point(segs, [seglen(s) for s in segs])
    return v[:2] / v[2], len(cand), len(segs), cond


def vertical_vp(gray, h, K, d_road):
    Ki = np.linalg.inv(K)
    polar = Ki.T @ d_road                       # {v : (K^-1 v) . d_road = 0}
    pn = polar / np.linalg.norm(polar[:2])
    p0, tdir = -pn[2] * pn[:2], np.array([-pn[1], pn[0]])
    votes = []
    for s in hough(gray, 60, 150, 10):
        if dang(ang(s), 90) >= 20 or seglen(s) <= 150:
            continue
        x = np.cross(hline(s), polar)
        if abs(x[2]) < 1e-9:
            continue
        v = x[:2] / x[2]
        if v[1] < h:                            # pitched down: verticals meet below
            continue
        votes.append((float((v - p0) @ tdir), seglen(s)))
    if len(votes) < 3:
        return None, {}
    ts = np.array([t for t, _ in votes]); ws = np.array([l for _, l in votes])
    best = None
    for i in range(len(ts)):
        m = (ts >= ts[i] - 200) & (ts <= ts[i] + 200)
        if best is None or ws[m].sum() > best[0]:
            best = (ws[m].sum(), m)
    m = best[1]
    tm = float(np.average(ts[m], weights=ws[m]))
    return p0 + tdir * tm, {"votes": len(votes), "in_window": int(m.sum()),
                            "window_spread_px": round(float(ts[m].max() - ts[m].min()) / 2, 1)}


def red_masks(bgr):
    h = bgr.shape[0]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hue = (hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 168)
    strong = ((hue & (hsv[:, :, 1] > 70) & (hsv[:, :, 2] > 60)).astype(np.uint8) * 255)
    faint = ((hue & (hsv[:, :, 1] > 32) & (hsv[:, :, 2] > 80)).astype(np.uint8) * 255)
    strong[:int(h * 0.40)] = 0; faint[:int(h * 0.40)] = 0
    strong = cv2.morphologyEx(strong, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    faint = cv2.morphologyEx(faint, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return strong, faint


def axis_of(points):
    c = points.mean(0)
    _, _, vt = np.linalg.svd(points - c, full_matrices=False)
    d = vt[0] / np.linalg.norm(vt[0])
    pr = (points - c) @ d
    return c, d, float(pr.max() - pr.min())


def components(mask, min_area):
    n, lbl, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < min_area:
            continue
        ys, xs = np.nonzero(lbl == i)
        out.append((int(st[i, cv2.CC_STAT_AREA]), np.stack([xs, ys], 1).astype(float)))
    return sorted(out, key=lambda t: -t[0])


def runs_on(mask, p0, dd, lo, hi, w, h, min_run=4, join=10):
    ts = np.arange(lo, hi, 1.0)
    pts = p0[None, :] + ts[:, None] * dd[None, :]
    ok = (pts[:, 0] >= 0) & (pts[:, 0] < w) & (pts[:, 1] >= 0) & (pts[:, 1] < h)
    val = np.zeros(len(ts), bool)
    val[ok] = mask[pts[ok, 1].astype(int), pts[ok, 0].astype(int)] > 0
    out, i = [], 0
    while i < len(ts):
        if val[i]:
            j = i
            while j < len(ts) and val[j]:
                j += 1
            if j - i >= min_run:
                out.append([ts[i], ts[j - 1]])
            i = j
        else:
            i += 1
    m = []
    for r in out:
        if m and r[0] - m[-1][1] < join:
            m[-1][1] = r[1]
        else:
            m.append(r)
    return m

def ransac_vp(segs, tol, horizon_band=None, seed=0, trials=6000):
    lines = [hline(s) for s in segs]
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(trials):
        i, j = rng.choice(len(segs), 2, replace=False)
        v = np.cross(lines[i], lines[j])
        if abs(v[2]) < 1e-9:
            continue
        v = v / v[2]
        if horizon_band and not (horizon_band[0] < v[1] < horizon_band[1]):
            continue
        inl = np.array([abs(l @ v) for l in lines]) < tol
        sc = sum(seglen(segs[k]) for k in np.nonzero(inl)[0])
        if best is None or sc > best[0]:
            best = (sc, inl)
    if best is None:
        return None, []
    inl = [segs[i] for i in np.nonzero(best[1])[0]]
    v, cond = vanishing_point(inl, [seglen(s) for s in inl])
    return (v[:2] / v[2], float(cond)), inl

def redline_gap(img, K, f35=None):
    h, w = img.shape[:2]
    Ki = np.linalg.inv(K)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Fewer than two long lower-frame segments and road_vp's RANSAC has
    # nothing to pair (rng.choice raised on a flat grey frame, 2026-09-23).
    try:
        v_road, n_cand, n_inl, cond = road_vp(gray, h)
    except ValueError:
        return {"ok": False, "why": "fewer than two long road segments for the road's vanishing point"}
    d_road = Ki @ np.append(v_road, 1.0); d_road /= np.linalg.norm(d_road)
    v_vert, vinfo = vertical_vp(gray, h, K, d_road)
    if v_vert is None:
        return {"ok": False, "why": "too few vertical segments"}
    n = Ki @ np.append(v_vert, 1.0); n /= np.linalg.norm(n)
    q = K @ np.cross(n, d_road); v_cross = q[:2] / q[2]

    strong, faint = red_masks(img)
    live = components(strong, 3000)
    if not live:
        return {"ok": False, "why": "no saturated red component"}
    c0, d0, run0 = axis_of(live[0][1]); theta0 = math.degrees(math.atan2(d0[1], d0[0])) % 180

    worn_px = [p for a, p in components(faint, 2500)
               if p.mean(0)[0] < c0[0] - 300 and p.mean(0)[1] > h * 0.68
               and dang(math.degrees(math.atan2(*axis_of(p)[1][::-1])) % 180, theta0) <= 20]
    if not worn_px:
        return {"ok": False, "why": "no worn red line left of the intact one"}
    cw, dw, _ = axis_of(np.vstack(worn_px))
    worn_line = np.cross(np.append(cw, 1.0), np.append(cw + dw * 100, 1.0))

    stations = []
    for s in np.linspace(-0.45, 0.30, 6):
        p0 = c0 + d0 * s * run0
        dd = v_cross - p0; dd /= np.linalg.norm(dd)
        st = {"y_px": int(p0[1])}
        lv = [r for r in runs_on(strong, p0, dd, -200, 200, w, h) if abs((r[0] + r[1]) / 2) < 120]
        if not lv:
            st["refused"] = "intact line not on the cross-road line"; stations.append(st); continue
        la, lb = lv[0]
        if lb - la < 70:
            st["refused"] = f"intact line only {lb - la:.0f} px wide here: cut by the frame edge"
            stations.append(st); continue
        stl = np.cross(np.append(p0, 1.0), np.append(v_cross, 1.0))
        x = np.cross(stl, worn_line); tp = float((x[:2] / x[2] - p0) @ dd)
        cand = [r for r in runs_on(faint, p0, dd, tp - 160, tp + 160, w, h) if 12 <= r[1] - r[0] <= 140]
        if not cand:
            st["refused"] = "no worn paint within 160 px of where its axis predicts"; stations.append(st); continue
        r0 = min(cand, key=lambda r: abs((r[0] + r[1]) / 2 - tp)); tc = (r0[0] + r0[1]) / 2
        A, B, C = p0 + dd * lb, p0 + dd * la, p0 + dd * tc
        r = length_ratio(A, B, C, v_cross)
        mm = measure(A, B, C, v_cross, RULER_M, jitter_px=1.5, trials=300)
        st.update({"ruler_px": round(lb - la, 1), "worn_paint_px": round(r0[1] - r0[0], 1),
                   "edge_to_worn_centre_px": round(tc - lb, 1),
                   "affine_m": round(abs(tc - lb) / (lb - la) * RULER_M, 4),
                   "gap_m": None if r is None else round(abs(r) * RULER_M, 4),
                   "gap_m_5_95": None if not mm["ok"] else [round(abs(mm["m_hi"]), 4), round(abs(mm["m_lo"]), 4)]})
        stations.append(st)
    ok = [s["gap_m"] for s in stations if s.get("gap_m")]
    return {
                "ok": len(ok) >= 3,
        "intrinsics": {"f35_mm": f35, "focal_px": round(float(K[0, 0]), 1), "size": [w, h]},
        "v_road": {"px": [round(float(v), 1) for v in v_road], "candidates": n_cand,
                   "inliers": n_inl, "condition": round(float(cond), 4)},
        "v_vert": {"px": [round(float(v), 1) for v in v_vert], **vinfo,
                   "method": "1-D vote along v_road's polar line; perpendicular by construction"},
        "v_cross": [round(float(v), 1) for v in v_cross],
        "ruler": {"m": RULER_M, "source": RULER_SRC},
        "stations": stations,
        "summary": None if not ok else {
            "stations_measured": len(ok), "median_m": round(float(np.median(ok)), 3),
            "min_m": round(min(ok), 3), "max_m": round(max(ok), 3),
            "last_minus_first_m": round(ok[-1] - ok[0], 3),
            "affine_median_m": round(float(np.median([s["affine_m"] for s in stations if s.get("gap_m")])), 3)},
        "what_was_measured": "ground distance from the intact red line's inner edge (the edge nearer "
                             "the carriageway) to the centre of the worn red line on the asphalt",
        "trend_note": "the gap widens towards the camera across the stations. Tested and excluded as "
                      "causes: the worn line's fitted axis (replaced by direct paint search), roll error "
                      "in n (depth-independent on synthetic ground truth), v_road error up to 300 px "
                      "(zero effect on synthetic ground truth). The two lines are not parallel on the ground.",
    }



def taper_427(img, K, f35=None):
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white = cv2.inRange(hsv, (0, 0, int(lv)), (180, 60, 255)); white[:int(h * 0.38)] = 0
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    dens = cv2.blur((white > 0).astype(np.float32), (121, 121))
    n, lbl, st, _ = cv2.connectedComponentsWithStats((dens > 0.12).astype(np.uint8), 8)
    if n < 2:
        return {"ok": False, "why": "no dense white hatching"}
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    area_frac = float(st[big, cv2.CC_STAT_AREA]) / (w * h)
    ys, xs = np.nonzero(lbl == big)
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    inside = cv2.dilate((lbl == big).astype(np.uint8), np.ones((61, 61), np.uint8))

    e = cv2.Canny(white, 50, 150)
    L = cv2.HoughLinesP(e, 1, np.pi / 1440, 50, minLineLength=200, maxLineGap=12)
    longs = [tuple(map(float, s)) for s in (L.reshape(-1, 4) if L is not None else [])
             if math.hypot(s[2] - s[0], s[3] - s[1]) > 200]
    inhull = [s for s in longs if inside[int((s[1] + s[3]) / 2), int((s[0] + s[2]) / 2)] > 0]
    if len(inhull) < 6:
        return {"ok": False, "why": f"only {len(inhull)} long white segments inside the chevron"}

    rest, pens = list(inhull), []
    for _ in range(4):
        if len(rest) < 3:
            break
        r, inl = ransac_vp(rest, 6.0, (0, h * 0.60))
        if r is None:
            break
        pens.append({"vp": r[0], "cond": r[1], "segs": inl})
        X = {tuple(s) for s in inl}; rest = [s for s in rest if tuple(s) not in X]
    pens = [p for p in pens if len(p["segs"]) >= 3]
    if len(pens) < 2:
        return {"ok": False, "why": "fewer than two pencils inside the chevron"}
    a, b = pens[0], pens[1]                       # the two largest, by construction
    theta = angle_between(K, np.append(a["vp"], 1.0), np.append(b["vp"], 1.0))
    unc = angle_uncertainty(K, a["segs"], b["segs"], trials=200, jitter_px=1.5, seed=0)

    why = None
    # F36 is a close-up: the "polygon" was the whole lower frame (0.42 of
    # it) and the two pencils were scattered short strokes that happened
    # to meet at 5.8 degrees. A chevron seen whole is a sliver of a frame.
    if area_frac > 0.25:
        why = f"the dense-white region is {area_frac:.2f} of the frame: a close-up, not a chevron seen whole"
    elif min(len(a["segs"]), len(b["segs"])) < 5:
        why = f"an edge pencil has only {min(len(a['segs']), len(b['segs']))} segments; 5 needed"
    elif not (1.0 <= theta <= 15.0):
        why = f"the two largest pencils meet at {theta:.1f} degrees, outside 1-15: not the two edges of a taper"
    elif unc["sd_deg"] > 1.0:
        why = f"jittered sd {unc['sd_deg']:.2f} degrees exceeds 1.0"
    ratio = 1.0 / math.tan(math.radians(theta))

    return {
                "ok": why is None, "why": why,
        "intrinsics": {"f35_mm": f35, "focal_px": round(float(K[0, 0]), 1), "size": [w, h]},
        "chevron_polygon": {"hull_points": len(hull), "area_frac": round(area_frac, 4), "long_segments_inside": len(inhull)},
        "edge_pencils": [{"segments": len(p["segs"]), "condition": round(float(p["cond"]), 4),
                          "vp_px": [round(float(x), 1) for x in p["vp"]]} for p in (a, b)],
        "taper_deg": round(theta, 2),
        "taper_uncertainty": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in unc.items()},
        "taper_ratio": round(ratio, 1),
        "thresholds": {k: {"ratio": v, "deg": round(math.degrees(math.atan(1 / v)), 2),
                           "meets": (ratio >= v) if why is None else None} for k, v in THRESHOLDS.items()},
        "source": SRC,
        "reading": "angle between the chevron's two edge pencils on the ground; L/W = 1/tan. Which design speed "
                   "governs is a document question (posted 50 before the works, 30 during), not decided here",
    }


# The encoding probe. Added 2026-09-23 after re-encoding F40 once at
# JPEG quality 97 moved its taper from 11.9:1 to 23.2:1 - across the
# 16:1 line, the opposite verdict - and made F17 refuse. A reading that a
# near-lossless re-encode changes is not a property of the road. So each
# measurement is repeated on the bytes as received and on three light
# re-encodes, and is reported only if the readings agree.
PROBE_QUALITIES = (97, 94, 91)


def _reencode(img, q):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def encoding_probe(fn, img, K, value, *, abs_tol=None, rel_tol=None, min_ok=3):
    """Run `fn(img, K)` on the image and on light re-encodes of it.

    Returns (result on the image as received, probe record). `stable` is
    True only when at least `min_ok` of the four readings measured and
    their spread is within `abs_tol` (absolute) or `rel_tol` (of the
    median). The caller reports the measurement only when stable.
    """
    from concurrent.futures import ThreadPoolExecutor
    variants = [("as_received", img)] + [(q, _reencode(img, q)) for q in PROBE_QUALITIES]
    with ThreadPoolExecutor(max_workers=len(variants)) as ex:
        outs = list(ex.map(lambda v: fn(v[1], K), variants))
    readings = [{"encoding": name, "value": value(o) if o.get("ok") else None,
                 "why": None if o.get("ok") else o.get("why")}
                for (name, _), o in zip(variants, outs)]
    vals = [r["value"] for r in readings if r["value"] is not None]
    spread = (max(vals) - min(vals)) if vals else None
    if len(vals) < min_ok:
        why = f"only {len(vals)} of {len(readings)} encodings measured; {min_ok} needed"
    elif abs_tol is not None and spread > abs_tol:
        why = f"readings spread {spread:.3f}, more than {abs_tol}"
    elif rel_tol is not None and spread > rel_tol * float(np.median(vals)):
        why = f"readings spread {spread:.2f}, more than {rel_tol:.0%} of their median {float(np.median(vals)):.2f}"
    else:
        why = None
    return outs[0], {"readings": readings, "stable": why is None, "why": why,
                     "median": None if not vals else round(float(np.median(vals)), 3),
                     "spread": None if spread is None else round(float(spread), 3)}
