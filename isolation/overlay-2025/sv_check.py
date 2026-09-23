"""Street View taper: two independent horizons and both edges against the road direction."""
import sys, math, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck"); sys.path.insert(0, "isolation/overlay-2025")
import sv_taper
from sv_taper import FRAMES, UP, paint_region
import horizon2 as H2
from marking import phone as P
from marking.vanishing import angle_between

for name, f, fov, pitch in FRAMES:
    im = cv2.resize(cv2.imread(f), (UP, UP), interpolation=cv2.INTER_CUBIC); h, w = im.shape[:2]
    K = P.K_from_fov(w, h, fov); Ki = np.linalg.inv(K)
    L, why = H2.confirmed_edges(im)
    if L is None: print(name, "edges:", why); continue
    _, region = paint_region(im); gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    g2 = gray.copy(); g2[cv2.dilate(region.astype(np.uint8), np.ones((81, 81), np.uint8)) > 0] = 0
    v_road = np.append(P.road_vp(g2, h)[0], 1.0)
    # horizon 1: vertical vanishing point
    d = Ki @ v_road; d /= np.linalg.norm(d); v_vert, info = P.vertical_vp(gray, h, K, d)
    hz = {}
    if v_vert is not None:
        n = Ki @ np.append(v_vert, 1.0); hz["verticals"] = Ki.T @ (n / np.linalg.norm(n))
    # horizon 2: the request's pitch, roll 0 -> ground normal in camera coords
    t = math.radians(-pitch)            # camera looks down by t
    n_pitch = np.array([0.0, math.cos(t), math.sin(t)])   # world up expressed in camera (y down, z forward)
    hz["pitch"] = Ki.T @ n_pitch
    for k, horizon in hz.items():
        va = np.cross(L["side_a"], horizon); vb = np.cross(L["side_b"], horizon)
        th = angle_between(K, va, vb)
        row = -(horizon[0] * w / 2 + horizon[2]) / horizon[1]
        print(f"{name:28} horizon={k:9} row@centre={row:7.0f}  taper {1/math.tan(math.radians(th)):5.1f}:1 ({th:5.2f} deg)"
              f"  A-road {angle_between(K, va, v_road):4.1f}  B-road {angle_between(K, vb, v_road):4.1f}")
