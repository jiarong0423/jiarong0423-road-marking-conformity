"""Horizon from the vertical vanishing point (the red-line-gap method), not the hatching.

v_road  long segments outside the chevron (phone.road_vp)
v_vert  phone.vertical_vp: poles and facades, voted along v_road's polar line
n       ground normal = K^-1 v_vert;   horizon = K^-T n
va, vb  each confirmed edge line (R3 + EDLines) meets the horizon
check   edge A runs with the lane, so va should sit on v_road: report the angle
"""
import sys, math, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from marking import phone as P
from marking.vanishing import angle_between
from edge_extremes import edges, chevron_region
import consensus as C


def confirmed_edges(img):
    e = edges(img)
    if not e["ok"]: return None, e["why"]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    segs = C.edlines(gray); L = {}
    for side in ("side_a", "side_b"):
        l3 = C.hom_line(e[side]["p0"], e[side]["d"]); a3 = math.degrees(math.atan2(e[side]["d"][1], e[side]["d"][0])) % 180
        m = [s for s in segs if C.dang(C.seg_ang(s), a3) <= C.ANG_DEG and C.seg_dist(l3, s) <= C.DIST_PX]
        tot = sum(P.seglen(s) for s in m)
        # two pieces, or one unbroken line of 800 px (Street View draws the edge whole)
        if tot < 400 or (len(m) < 2 and tot < 800): return None, f"{side} not confirmed by EDLines"
        pts = np.array([[s[0], s[1]] for s in m] + [[s[2], s[3]] for s in m], np.float32)
        vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        L[side] = C.hom_line(np.array([x0, y0]), np.array([vx, vy]))
    return L, None


def run(img, K):
    h, w = img.shape[:2]
    L, why = confirmed_edges(img)
    if L is None: return {"ok": False, "why": why}
    _, region = chevron_region(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g2 = gray.copy(); g2[cv2.dilate(region.astype(np.uint8), np.ones((81, 81), np.uint8)) > 0] = 0
    try:
        v_road, _, n_inl, _ = P.road_vp(g2, h)
    except ValueError:
        return {"ok": False, "why": "no road vanishing point"}
    Ki = np.linalg.inv(K)
    d_road = Ki @ np.append(v_road, 1.0); d_road /= np.linalg.norm(d_road)
    v_vert, vinfo = P.vertical_vp(gray, h, K, d_road)
    if v_vert is None: return {"ok": False, "why": "too few vertical segments"}
    n = Ki @ np.append(v_vert, 1.0); n /= np.linalg.norm(n)
    horizon = Ki.T @ n
    va = np.cross(L["side_a"], horizon); vb = np.cross(L["side_b"], horizon)
    theta = angle_between(K, va, vb)
    a_road = angle_between(K, va, np.append(v_road, 1.0))
    return {"ok": 1.0 <= theta <= 15.0, "taper_deg": round(theta, 2),
            "taper_ratio": round(1 / math.tan(math.radians(theta)), 1),
            "edgeA_vs_road_deg": round(a_road, 2), "road_inliers": n_inl, "vert": vinfo}
