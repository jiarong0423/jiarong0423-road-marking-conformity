"""2025 Street View -> F17 homography from two line correspondences and one arrow.

  SV lane-side boundary of the chevron  <->  the owner's pre-erasure edge on F17 (user_line)
  SV V-tip boundary                     <->  F17's upper painted line (still painted), R3 + EDLines
  SV arrow tip / tail                   <->  F17 arrow tip / tail (read off zoomed grids)
Point x on an SV line must map onto the F17 line: l . (H x) = 0, one equation per point.
"""
import sys, json, math, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from horizon2 import confirmed_edges

SV_IMG = "data/streetview/2025-06_before_erasure_CLY3P.jpg"   # owner screenshot of Street View; data/ is not in git
F17 = "evidence/field-2026-09-20/IMG_20260920_155843.jpg"
USER_LINE = [(-403.3435, 3394.9868), (3660.3918, 1045.7693)]
SV_LANE_SIDE = [(111, 1008), (374, 674), (478, 553), (640, 330)]       # EDLines segs 2 and 12
SV_VTIP = [(9, 581), (73, 532), (126, 498), (184, 460), (376, 335)]    # EDLines segs at 146-148 deg
ARROW = {"sv": [(726, 301), (721, 345)], "f17": [(2907, 1639), (2818, 1662)]}


def line_through(pts):
    P = np.float32(pts); vx, vy, x0, y0 = cv2.fitLine(P, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    l = np.cross([x0, y0, 1.0], [x0 + vx, y0 + vy, 1.0]); return l / np.linalg.norm(l[:2])


def solve(rows):
    A = np.array(rows); _, _, vt = np.linalg.svd(A); H = vt[-1].reshape(3, 3); return H / H[2, 2]


def point_rows(x, u):
    X, Y = x; U, V = u
    return [[X, Y, 1, 0, 0, 0, -U * X, -U * Y, -U], [0, 0, 0, X, Y, 1, -V * X, -V * Y, -V]]


def line_rows(x, l):
    X, Y = x; a, b, c = l
    return [[a * X, a * Y, a, b * X, b * Y, b, c * X, c * Y, c]]


def main(out):
    ph = cv2.imread(F17)
    L, why = confirmed_edges(ph)
    # the upper painted line = the one nearer the top of the frame at the image centre
    def y_at(l, x): return -(l[0] * x + l[2]) / l[1]
    upper = min(L.values(), key=lambda l: y_at(l, 1536)); upper = upper / np.linalg.norm(upper[:2])
    lane_f17 = line_through(USER_LINE)
    rows = []
    for x in SV_LANE_SIDE: rows += line_rows(x, lane_f17)
    for x in SV_VTIP: rows += line_rows(x, upper)
    for x, u in zip(ARROW["sv"], ARROW["f17"]): rows += [r for r in point_rows(x, u)]
    # weight: scale line rows so their residual is in F17 px like the point rows
    H = solve(rows)
    res = {"arrow_px": [float(np.linalg.norm(cv2.perspectiveTransform(np.float32([[x]]), H)[0, 0] - np.float32(u)))
                        for x, u in zip(ARROW["sv"], ARROW["f17"])],
           "lane_side_px": [float(abs(lane_f17 @ np.append(cv2.perspectiveTransform(np.float32([[x]]), H)[0, 0], 1))) for x in SV_LANE_SIDE],
           "vtip_px": [float(abs(upper @ np.append(cv2.perspectiveTransform(np.float32([[x]]), H)[0, 0], 1))) for x in SV_VTIP]}
    np.save(f"{out}/H_sv_to_F17_lines.npy", H)
    sv = cv2.imread(SV_IMG); mask = cv2.imread(f"{out}/2025_白漆_黑底.png", 0)
    wm = cv2.warpPerspective(mask, H, (ph.shape[1], ph.shape[0]))
    over = ph.copy(); sel = wm > 127
    over[sel] = (0.3 * over[sel] + 0.7 * np.array([200, 40, 255])).astype(np.uint8)
    cv2.imwrite(f"{out}/F17_overlay_lines.jpg", cv2.resize(over, (1536, 2048)), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(json.dumps({k: [round(v, 1) for v in vs] for k, vs in res.items()}))


if __name__ == "__main__":
    main(sys.argv[1])
