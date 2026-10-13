"""F17/F40 taper by consensus of independent recognizers (isolation, 2026-09-23).

Owner's direction: other recognizers ASSIST; an edge counts only when two
agree. External answer (ASK) suggested EDLines, region outline, hatch ends.

  R3  outermost paint per slice + RANSAC line   (edge_extremes.py)
  R5  EDLines segments (cv2.ximgproc), clustered into collinear lines
  agree: angle <= 1 deg and every R5 endpoint within DIST_PX of the R3 line

Ground angle: a single image line has no vanishing point of its own. The
ground plane's horizon comes from the two arms of the V hatching - each arm
is a family of parallel ground lines, so each gives a vanishing point on the
horizon. Each edge's vanishing point is its intersection with that horizon.
"""
import sys, math, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from marking import phone as P
from marking.vanishing import angle_between, vanishing_point
from edge_extremes import edges, chevron_region

DIST_PX, ANG_DEG = 15.0, 1.0


def hom_line(p0, d):
    return np.cross(np.append(p0, 1.0), np.append(p0 + d * 1000.0, 1.0))


def seg_dist(l, s):
    l = l / np.linalg.norm(l[:2])
    return max(abs(l @ [s[0], s[1], 1.0]), abs(l @ [s[2], s[3], 1.0]))


def seg_ang(s):
    return math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) % 180


def dang(a, b):
    return min(abs(a - b), 180 - abs(a - b))


def edlines(gray, minlen=120):
    ed = cv2.ximgproc.createEdgeDrawing(); p = cv2.ximgproc_EdgeDrawing_Params()
    p.MinLineLength = minlen; ed.setParams(p); ed.detectEdges(gray)
    L = ed.detectLines()
    return [] if L is None else [tuple(map(float, s)) for s in L.reshape(-1, 4)]


def run(img, K):
    h, w = img.shape[:2]
    e = edges(img)
    if not e["ok"]: return {"ok": False, "why": "R3: " + e["why"]}
    white, region = chevron_region(img)
    near = cv2.dilate(region.astype(np.uint8), np.ones((81, 81), np.uint8)) > 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    segs = [s for s in edlines(gray) if near[int((s[1] + s[3]) / 2), int((s[0] + s[2]) / 2)]]
    res = {"ok": False}
    lines = {}
    for side in ("side_a", "side_b"):
        l3 = hom_line(e[side]["p0"], e[side]["d"]); a3 = math.degrees(math.atan2(e[side]["d"][1], e[side]["d"][0])) % 180
        match = [s for s in segs if dang(seg_ang(s), a3) <= ANG_DEG and seg_dist(l3, s) <= DIST_PX]
        mlen = sum(P.seglen(s) for s in match)
        res[side] = {"r3_inliers": e[side]["inliers"], "r5_segments": len(match), "r5_length_px": int(mlen)}
        if len(match) < 2 or mlen < 400:
            res["why"] = f"{side}: EDLines does not confirm the R3 line ({len(match)} segs, {mlen:.0f} px)"
            return res
        pts = np.array([[s[0], s[1]] for s in match] + [[s[2], s[3]] for s in match], np.float32)
        vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        lines[side] = hom_line(np.array([x0, y0]), np.array([vx, vy]))
        res[side]["r3_vs_r5_deg"] = round(dang(a3, math.degrees(math.atan2(vy, vx)) % 180), 3)
    # hatch arms: short segments inside the region, away from both edge lines
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(gray)[0]
    hs = []
    for s in ([] if lsd is None else lsd.reshape(-1, 4)):
        s = tuple(map(float, s))
        if not 30 <= P.seglen(s) <= 400: continue
        mx, my = int((s[0] + s[2]) / 2), int((s[1] + s[3]) / 2)
        if not region[my, mx]: continue
        if min(seg_dist(lines["side_a"], s), seg_dist(lines["side_b"], s)) < 25: continue
        hs.append(s)
    if len(hs) < 10:
        res["why"] = f"only {len(hs)} hatch segments"; return res
    angs = np.array([seg_ang(s) for s in hs])
    # two arms: 2-means on doubled angle
    z = np.stack([np.cos(np.radians(2 * angs)), np.sin(np.radians(2 * angs))], 1).astype(np.float32)
    _, lab, _ = cv2.kmeans(z, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4), 5, cv2.KMEANS_PP_CENTERS)
    vps = []
    for k in (0, 1):
        g = [hs[i] for i in range(len(hs)) if lab[i, 0] == k]
        if len(g) < 5: res["why"] = f"hatch arm {k} has {len(g)} segments"; return res
        rest, best = list(g), None
        r, inl = P.ransac_vp(g, 4.0)
        if r is None: res["why"] = f"hatch arm {k}: no vanishing point"; return res
        vps.append(np.append(r[0], 1.0)); res[f"hatch_arm_{k}"] = {"segments": len(g), "inliers": len(inl)}
    horizon = np.cross(vps[0], vps[1])
    va = np.cross(lines["side_a"], horizon); vb = np.cross(lines["side_b"], horizon)
    theta = angle_between(K, va, vb)
    # check: the two arms should meet the edges at ~45 deg on the ground (§171 斜四五度)
    arm_edge = [round(angle_between(K, v, va), 1) for v in vps]
    res.update({"ok": 1.0 <= theta <= 15.0, "taper_deg": round(theta, 2),
                "taper_ratio": round(1 / math.tan(math.radians(theta)), 1),
                "arm_to_edge_a_deg": arm_edge, "hatch_segments": len(hs)})
    if not res["ok"]: res["why"] = f"angle {theta:.2f} outside 1-15"
    return res
