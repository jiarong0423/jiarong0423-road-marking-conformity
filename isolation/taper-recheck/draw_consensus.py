"""Draw confirmed edges, the horizon from v_vert, and the road vanishing point."""
import sys, math, glob, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from marking import phone as P
from horizon2 import confirmed_edges, run
from edge_extremes import chevron_region
FOV = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))
f = sorted(glob.glob("evidence/field-2026-09-20/IMG_*.jpg"))


def draw_hline(img, l, col, t):
    h, w = img.shape[:2]; pts = []
    for x in (-w, 2 * w):
        if abs(l[1]) > 1e-9: pts.append((x, -(l[0] * x + l[2]) / l[1]))
    cv2.line(img, (int(pts[0][0]), int(pts[0][1])), (int(pts[1][0]), int(pts[1][1])), col, t)


panels = []
for fr in (17, 40):
    im = cv2.imread(f[fr - 1]); h, w = im.shape[:2]
    K = P.K_from_fov(w, h, FOV); r = run(im, K); L, _ = confirmed_edges(im)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); _, region = chevron_region(im)
    g2 = gray.copy(); g2[cv2.dilate(region.astype(np.uint8), np.ones((81, 81), np.uint8)) > 0] = 0
    v_road = P.road_vp(g2, h)[0]
    Ki = np.linalg.inv(K); d = Ki @ np.append(v_road, 1); d /= np.linalg.norm(d)
    v_vert, _ = P.vertical_vp(gray, h, K, d); n = Ki @ np.append(v_vert, 1); horizon = Ki.T @ (n / np.linalg.norm(n))
    v = im.copy()
    draw_hline(v, L["side_a"], (0, 255, 255), 8); draw_hline(v, L["side_b"], (255, 0, 255), 8)
    draw_hline(v, horizon, (255, 255, 0), 6)
    cv2.circle(v, (int(v_road[0]), int(v_road[1])), 40, (0, 0, 255), 10)
    pad = 600; canvas = cv2.copyMakeBorder(v, pad, 0, pad, pad, cv2.BORDER_CONSTANT, value=(40, 40, 40))
    cv2.circle(canvas, (int(v_road[0]) + pad, int(v_road[1]) + pad), 40, (0, 0, 255), 10)
    draw_hline(canvas[:pad], np.array([horizon[0], horizon[1], horizon[2] - horizon[0] * pad - horizon[1] * pad]) , (255, 255, 0), 0) if False else None
    small = cv2.resize(canvas, (1000, int(canvas.shape[0] * 1000 / canvas.shape[1])))
    cv2.rectangle(small, (0, 0), (1000, 70), (0, 0, 0), -1)
    cv2.putText(small, f"F{fr}  {r['taper_ratio']}:1  edgeA-vs-road {r['edgeA_vs_road_deg']} deg", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
    panels.append(small)
hm = min(p.shape[0] for p in panels)
out = sys.argv[1]; cv2.imwrite(out, np.hstack([p[:hm] for p in panels])); print(out)
