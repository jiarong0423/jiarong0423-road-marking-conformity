import sys, math, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck"); sys.path.insert(0, "isolation/overlay-2025")
import sv_taper
from sv_taper import UP
import horizon2 as H2
from marking import phone as P


def draw_hline(img, l, col, t):
    h, w = img.shape[:2]
    p = [(x, -(l[0] * x + l[2]) / l[1]) for x in (-w, 2 * w)]
    cv2.line(img, (int(p[0][0]), int(p[0][1])), (int(p[1][0]), int(p[1][1])), col, t)
tiles = []
for name, f, fov, pitch, label in [("+35.5", "output/seq/+0035.5.jpg", 90, -25, "2025-06 +35.5 m  4.8-5.1:1"),
                                   ("+45.4", "output/seq/+0045.4.jpg", 90, -25, "2025-06 +45.4 m  4.0-4.7:1")]:
    im = cv2.resize(cv2.imread(f), (UP, UP), interpolation=cv2.INTER_CUBIC); K = P.K_from_fov(UP, UP, fov)
    L, _ = H2.confirmed_edges(im); v = im.copy()
    draw_hline(v, L["side_a"], (0, 255, 255), 16); draw_hline(v, L["side_b"], (255, 0, 255), 16)
    t = math.radians(-pitch); hz = np.linalg.inv(K).T @ np.array([0, math.cos(t), math.sin(t)])
    draw_hline(v, hz, (255, 255, 0), 10)
    s = cv2.resize(v, (900, 900)); cv2.rectangle(s, (0, 0), (900, 56), (0, 0, 0), -1)
    cv2.putText(s, label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2); tiles.append(s)
cv2.imwrite(sys.argv[1], np.hstack(tiles)); print(sys.argv[1])
