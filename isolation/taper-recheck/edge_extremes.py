"""Recognizer 3: the chevron's two boundary lines from its outermost white paint.

Different principle from Hough/LSD: no segments, no vanishing-point grouping.
The two boundary lines are the outer edges of the painted chevron, so slice
the chevron region along its main axis, take the outermost white pixel on
each side of every slice, and robust-fit one straight line per side
(straight in the image, since a projection keeps lines straight).
"""
import sys, math, cv2, numpy as np
sys.path.insert(0, "src")
from marking.vanishing import angle_between


def chevron_region(img):
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white = cv2.inRange(hsv, (0, 0, int(lv)), (180, 60, 255)); white[:int(h * 0.38)] = 0
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dens = cv2.blur((white > 0).astype(np.float32), (121, 121))
    n, lbl, st, _ = cv2.connectedComponentsWithStats((dens > 0.12).astype(np.uint8), 8)
    if n < 2: return None, None
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return white > 0, lbl == big


def ransac_line(pts, tol=6.0, trials=2000, seed=0):
    rng = np.random.default_rng(seed); best = None
    for _ in range(trials):
        i, j = rng.choice(len(pts), 2, replace=False)
        d = pts[j] - pts[i]; nrm = np.hypot(*d)
        if nrm < 50: continue
        nvec = np.array([-d[1], d[0]]) / nrm
        inl = np.abs((pts - pts[i]) @ nvec) < tol
        if best is None or inl.sum() > best.sum(): best = inl
    P = pts[best]
    vx, vy, x0, y0 = cv2.fitLine(P.astype(np.float32), cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
    return np.array([x0, y0]), np.array([vx, vy]), int(best.sum()), len(pts)


def edges(img, slice_px=12):
    white, region = chevron_region(img)
    if region is None: return {"ok": False, "why": "no chevron region"}
    ys, xs = np.nonzero(region)
    pts = np.stack([xs, ys], 1).astype(float); c = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False); ax = vt[0]; nv = np.array([-ax[1], ax[0]])
    wy, wx = np.nonzero(white & region)
    W = np.stack([wx, wy], 1).astype(float)
    t = (W - c) @ ax; s = (W - c) @ nv
    lo_pts, hi_pts = [], []
    for k in np.arange(t.min(), t.max(), slice_px):
        m = (t >= k) & (t < k + slice_px)
        if m.sum() < 20: continue
        i_lo, i_hi = np.argmin(s[m]), np.argmax(s[m])
        lo_pts.append(W[m][i_lo]); hi_pts.append(W[m][i_hi])
    if len(lo_pts) < 20: return {"ok": False, "why": "too few slices"}
    out = {}
    for name, P in (("side_a", np.array(lo_pts)), ("side_b", np.array(hi_pts))):
        p0, d, ninl, ntot = ransac_line(P)
        out[name] = {"p0": p0, "d": d, "inliers": ninl, "points": ntot}
    return {"ok": True, **out}


def line_vp(e1, e2):
    l1 = np.cross(np.append(e1["p0"], 1), np.append(e1["p0"] + e1["d"] * 1000, 1))
    l2 = np.cross(np.append(e2["p0"], 1), np.append(e2["p0"] + e2["d"] * 1000, 1))
    return l1, l2


def taper_edges(img, K):
    e = edges(img)
    if not e["ok"]: return e
    # each side's line direction -> its vanishing point is the line's point at infinity
    # projected: use the image line's intersection with the horizon of the ground plane is unknown,
    # so use the angle between the two ground directions via each line's vanishing point =
    # intersection with the other family is not defined; instead the angle between two ground
    # lines needs each line's own vanishing point. A single image line has no unique VP, but the
    # two boundary lines meet at the taper's apex ON THE GROUND; their ground angle follows from
    # the two lines and the ground plane's horizon. Here: horizon from the road's vanishing point.
    return e
