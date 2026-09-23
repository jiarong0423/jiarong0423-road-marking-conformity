"""Horizon for F17/F40 from three independent ground vanishing points.

  v_road   long lane lines outside the chevron (phone.road_vp, as the red-line
           gap already uses) - the road direction, parallel to edge A
  v_armX   each arm of the V hatching, LSD segments inside the chevron
Accept the horizon only if the three are collinear (angle of the third
point off the line through the other two, in the image, small) and each
arm meets edge A at 45 +- 8 deg on the ground (§171 斜四五度).
Horizon = total-least-squares line through the accepted VPs.
"""
import sys, math, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from marking import phone as P
from marking.vanishing import angle_between
from edge_extremes import edges, chevron_region
import consensus as C


def horizon_run(img, K):
    h, w = img.shape[:2]
    base = C.run(img, K)          # edges confirmed by R3 + EDLines
    if "side_a" not in base or "r3_vs_r5_deg" not in base.get("side_b", {}):
        return {"ok": False, "why": base.get("why")}
    e = edges(img); white, region = chevron_region(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # rebuild the confirmed edge lines exactly as consensus does
    segs = [s for s in C.edlines(gray)]
    L = {}
    for side in ("side_a", "side_b"):
        l3 = C.hom_line(e[side]["p0"], e[side]["d"]); a3 = math.degrees(math.atan2(e[side]["d"][1], e[side]["d"][0])) % 180
        m = [s for s in segs if C.dang(C.seg_ang(s), a3) <= C.ANG_DEG and C.seg_dist(l3, s) <= C.DIST_PX]
        pts = np.array([[s[0], s[1]] for s in m] + [[s[2], s[3]] for s in m], np.float32)
        vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        L[side] = C.hom_line(np.array([x0, y0]), np.array([vx, vy]))
    # v_road from long segments OUTSIDE the chevron region
    g2 = gray.copy(); g2[cv2.dilate(region.astype(np.uint8), np.ones((81, 81), np.uint8)) > 0] = 0
    try:
        v_road, nc, ni, cond = P.road_vp(g2, h)
    except ValueError:
        return {"ok": False, "why": "no road vanishing point"}
    v_road = np.append(v_road, 1.0)
    # hatch arms
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(gray)[0]
    hs = []
    for s in ([] if lsd is None else lsd.reshape(-1, 4)):
        s = tuple(map(float, s))
        if not 30 <= P.seglen(s) <= 400: continue
        mx, my = int((s[0] + s[2]) / 2), int((s[1] + s[3]) / 2)
        if not region[my, mx]: continue
        if min(C.seg_dist(L["side_a"], s), C.seg_dist(L["side_b"], s)) < 25: continue
        hs.append(s)
    angs = np.array([C.seg_ang(s) for s in hs])
    z = np.stack([np.cos(np.radians(2 * angs)), np.sin(np.radians(2 * angs))], 1).astype(np.float32)
    _, lab, _ = cv2.kmeans(z, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4), 5, cv2.KMEANS_PP_CENTERS)
    arms = []
    for k in (0, 1):
        g = [hs[i] for i in range(len(hs)) if lab[i, 0] == k]
        if len(g) < 5: continue
        r, inl = P.ransac_vp(g, 4.0)
        if r is None: continue
        va = np.append(r[0], 1.0)
        arms.append({"vp": va, "n": len(g), "inl": len(inl), "to_road_deg": round(angle_between(K, va, v_road), 1)})
    good = [a for a in arms if abs(a["to_road_deg"] - 45) <= 8]
    info = {"arms": [{k: v for k, v in a.items() if k != "vp"} for a in arms], "road_vp_inliers": ni}
    if not good:
        return {"ok": False, "why": "no hatch arm at 45+-8 deg to the road direction", **info}
    pts = np.array([v_road[:2] / v_road[2]] + [a["vp"][:2] / a["vp"][2] for a in good])
    if len(pts) == 2:
        horizon = np.cross(np.append(pts[0], 1), np.append(pts[1], 1)); resid = None
    else:
        c = pts.mean(0); _, _, vt = np.linalg.svd(pts - c); d = vt[0]
        horizon = np.cross(np.append(c, 1), np.append(c + d * 1000, 1))
        hn = horizon / np.linalg.norm(horizon[:2]); resid = float(max(abs(hn @ np.append(p, 1)) for p in pts))
    va_ = np.cross(L["side_a"], horizon); vb_ = np.cross(L["side_b"], horizon)
    theta = angle_between(K, va_, vb_)
    edge_a_to_road = angle_between(K, va_, v_road)
    return {"ok": 1.0 <= theta <= 15.0, "taper_deg": round(theta, 2), "taper_ratio": round(1 / math.tan(math.radians(theta)), 1),
            "arms_used": len(good), "collinear_resid_px": None if resid is None else round(resid, 1),
            "edge_a_to_road_deg": round(edge_a_to_road, 2), **info}
