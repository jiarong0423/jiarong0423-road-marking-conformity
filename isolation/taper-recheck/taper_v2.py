"""taper_427 variant for the re-check (isolation, 2026-09-23).

Same white mask and chevron polygon as marking.phone.taper_427. Changes,
from the external answer (ASK 2026-09-23, candidate methods only):
  1. LSD (cv2.createLineSegmentDetector, core OpenCV) instead of Canny + HoughLinesP
  2. pencils whose vanishing points subtend < MERGE_DEG on the ground are merged
  3. pencils ranked by total segment length, not segment count - fragmenting
     one edge changes the count but barely the length
"""
import math, sys
import cv2, numpy as np
sys.path.insert(0, "src")
from marking import phone as P
from marking.vanishing import angle_between, vanishing_point

MERGE_DEG = 1.0
MIN_LEN = 120


def lsd_segments(img, inside, y0):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    L = lsd.detect(g)[0]
    out = []
    for s in ([] if L is None else L.reshape(-1, 4)):
        x1, y1, x2, y2 = map(float, s)
        if math.hypot(x2 - x1, y2 - y1) < MIN_LEN: continue
        mx, my = int((x1 + x2) / 2), int((y1 + y2) / 2)
        if my < y0 or not inside[my, mx]: continue
        out.append((x1, y1, x2, y2))
    return out


def taper_v2(img, K):
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white = cv2.inRange(hsv, (0, 0, int(lv)), (180, 60, 255)); white[:int(h * 0.38)] = 0
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dens = cv2.blur((white > 0).astype(np.float32), (121, 121))
    n, lbl, st, _ = cv2.connectedComponentsWithStats((dens > 0.12).astype(np.uint8), 8)
    if n < 2: return {"ok": False, "why": "no dense white hatching"}
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    area_frac = float(st[big, cv2.CC_STAT_AREA]) / (w * h)
    if area_frac > 0.25: return {"ok": False, "why": f"close-up ({area_frac:.2f} of frame)"}
    inside = cv2.dilate((lbl == big).astype(np.uint8), np.ones((61, 61), np.uint8))
    segs = lsd_segments(img, inside, int(h * 0.38))
    if len(segs) < 6: return {"ok": False, "why": f"only {len(segs)} LSD segments"}
    rest, pens = list(segs), []
    for _ in range(6):
        if len(rest) < 3: break
        r, inl = P.ransac_vp(rest, 6.0, (0, h * 0.60))
        if r is None: break
        pens.append({"vp": np.append(r[0], 1.0), "segs": inl})
        X = {tuple(s) for s in inl}; rest = [s for s in rest if tuple(s) not in X]
    # merge pencils whose vanishing points are < MERGE_DEG apart on the ground
    merged = True
    while merged:
        merged = False
        for i in range(len(pens)):
            for j in range(i + 1, len(pens)):
                if angle_between(K, pens[i]["vp"], pens[j]["vp"]) < MERGE_DEG:
                    ss = pens[i]["segs"] + pens[j]["segs"]
                    v, _ = vanishing_point(ss, [P.seglen(s) for s in ss])
                    pens[i] = {"vp": v / v[2], "segs": ss}; del pens[j]; merged = True; break
            if merged: break
    for p in pens: p["len"] = sum(P.seglen(s) for s in p["segs"])
    pens = sorted([p for p in pens if len(p["segs"]) >= 3], key=lambda p: -p["len"])
    if len(pens) < 2: return {"ok": False, "why": "fewer than two pencils after merging"}
    theta = angle_between(K, pens[0]["vp"], pens[1]["vp"])
    if not (1.0 <= theta <= 15.0):
        return {"ok": False, "why": f"two longest pencils meet at {theta:.1f} deg", "taper_deg": round(theta, 2)}
    return {"ok": True, "taper_deg": round(theta, 2), "taper_ratio": round(1 / math.tan(math.radians(theta)), 1),
            "pencils": [(len(p["segs"]), int(p["len"])) for p in pens[:4]]}
