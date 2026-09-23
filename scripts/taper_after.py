"""The taper rate after the 2026-05 re-marking, with the horizon drawn by hand.

The earlier run of this script recovered the pitch from Hough lines and got
anything from -8.0° to +19.6° across eight frames, which put the taper rate
between 0.087 and 0.445. Twenty degrees of upward tilt in a photograph of a
road surface is a failed estimate, and the five-fold spread is what a failed
pitch does to everything downstream.

The pitch now comes from the horizon instead, and the horizon from lines the
site owner drew along things that run parallel on the ground. Six of them
meet at one point, most within half a degree of it. The along-horizon
position of that point is poorly constrained - near-parallel lines always
leave it so, and the pairwise intersections scatter across 1400 px in x - but
its height scatters over 100 px, and height is the whole of the pitch.

A second family fixes the horizon's tilt so that no zero-roll assumption is
needed: the chevron's own boundary lines run longitudinally and are long,
painted and unambiguous.

    pitch = atan((y_horizon - cy) / f),  f = f35 * diagonal_px / 43.267
"""
import sys, json, math
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marking.rectify import ground_angle   # noqa: E402

ANNOT = Path(__file__).resolve().parents[1] / "data" / "annotations"   # owner drawings; data/ is not in git
ANN = ANNOT / "annotation_6.webp"
F17 = Path("evidence/field-2026-09-20/IMG_20260920_155843.jpg")
F35 = 24.0

def homog(p): return np.array([p[0], p[1], 1.0])
def ln(a, b): return np.cross(homog(a), homog(b))
def vp(lines):
    A = np.array([l[:2] for l in lines]); b = np.array([-l[2] for l in lines])
    return np.linalg.lstsq(A, b, rcond=None)[0]

full = cv2.imread(str(F17)); H, W = full.shape[:2]
f = F35 * math.hypot(W, H) / 43.267
print(f"F17 {W}x{H}, f35 {F35:.0f} mm -> f {f:.0f} px, "
      f"fov {math.degrees(2*math.atan((W/2)/f)):.1f} deg")

# --- the drawn family, carried into full-resolution coordinates -------------
ann = cv2.imread(str(ANN))
small = cv2.resize(full, (ann.shape[1], int(ann.shape[1]*H/W)))
sift = cv2.SIFT_create(6000); bf = cv2.BFMatcher()
ka, da = sift.detectAndCompute(cv2.cvtColor(ann, cv2.COLOR_BGR2GRAY), None)
kb, db = sift.detectAndCompute(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), None)
mt = [x for x, y in bf.knnMatch(da, db, k=2) if x.distance < 0.7*y.distance]
Hm, inl = cv2.findHomography(
    np.float32([ka[x.queryIdx].pt for x in mt]).reshape(-1, 1, 2),
    np.float32([kb[x.trainIdx].pt for x in mt]).reshape(-1, 1, 2), cv2.RANSAC, 3.0)
print(f"annotation registered, {int(inl.sum())} inliers")

drawn = np.load(ANNOT / "drawn_lines.npy")
k = W / ann.shape[1]
def to_full(p):
    q = Hm @ homog(p)
    return (q[:2]/q[2]) * k
dl = [ln(to_full(s[:2]), to_full(s[2:])) for s in drawn]
V1 = vp(dl)
print(f"drawn family vanishing point ({V1[0]:.0f}, {V1[1]:.0f})")

# --- the chevron's boundary lines, the longitudinal family ------------------
ox, oy, sc = int(W*0.10), int(H*0.42), 0.55
crop = cv2.resize(full[oy:int(H*0.62), ox:int(W*0.80)], None, fx=sc, fy=sc,
                  interpolation=cv2.INTER_AREA)
Lc = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
paint = cv2.morphologyEx(
    ((Lc - cv2.GaussianBlur(Lc, (0, 0), 25)) > 14).astype(np.uint8),
    cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
n, lbl, st, _ = cv2.connectedComponentsWithStats(paint, 8)
big = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_AREA])
def princ(i, labels):
    ys, xs = np.nonzero(labels == i)
    p = np.stack([xs, ys], 1).astype(np.float32); m = p.mean(0)
    _, _, v = np.linalg.svd(p - m, full_matrices=False)
    d = v[0]/np.linalg.norm(v[0]); pr = (p - m) @ d
    return m + d*pr.min(), m + d*pr.max()
a, b = princ(big, lbl)
band_ang = math.degrees(math.atan2((b-a)[1], (b-a)[0]))
def line_se(length, ang):
    kk = np.zeros((length | 1, length | 1), np.uint8); c = length//2
    t = math.radians(ang)
    for s in np.linspace(-length/2, length/2, length*3):
        x, y = int(round(c+s*math.cos(t))), int(round(c+s*math.sin(t)))
        if 0 <= x < kk.shape[1] and 0 <= y < kk.shape[0]: kk[y, x] = 1
    return kk
bnd = cv2.morphologyEx(paint, cv2.MORPH_OPEN, line_se(91, band_ang))
nb, lb, sb, _ = cv2.connectedComponentsWithStats(bnd, 8)
up = lambda p: np.array([p[0]/sc + ox, p[1]/sc + oy])
bl = []
for i in range(1, nb):
    if sb[i, cv2.CC_STAT_AREA] < 400: continue
    p, q = princ(i, lb)
    bl.append(ln(up(p), up(q)))
print(f"{len(bl)} painted boundary lines")
V2 = vp(bl) if len(bl) >= 2 else None
if V2 is not None:
    print(f"boundary family vanishing point ({V2[0]:.0f}, {V2[1]:.0f})")

# --- the horizon, and the pitch --------------------------------------------
if V2 is not None and abs(V2[1] - V1[1]) < H*0.25 and abs(V2[0]-V1[0]) > W*0.05:
    hz = np.cross(homog(V1), homog(V2))
    y_h = -(hz[0]*(W/2) + hz[2]) / hz[1]
    roll = math.degrees(math.atan2(-hz[0], hz[1]))
    src = "two families"
else:
    y_h = V1[1]; roll = 0.0; src = "the drawn family alone, roll assumed zero"
    if V2 is not None:
        print(f"  the two vanishing points disagree in height by "
              f"{abs(V2[1]-V1[1]):.0f} px; falling back")
pitch = math.degrees(math.atan((y_h - H/2)/f))
fov = math.degrees(2*math.atan((W/2)/f))
print(f"\nhorizon at y={y_h:.0f} ({src}), roll {roll:+.2f} deg")
print(f"pitch {pitch:+.2f} deg   (the automatic run gave -8.0 to +19.6)")

# --- the bearings ----------------------------------------------------------
g = cv2.createCLAHE(2.0, (8, 8)).apply(cv2.cvtColor(full, cv2.COLOR_BGR2GRAY))
e = cv2.Canny(cv2.GaussianBlur(g, (5, 5), 0), 50, 150)
e[:int(y_h)+40] = 0
ls = cv2.HoughLinesP(e, 1, np.pi/720, 90, minLineLength=int(W*0.08), maxLineGap=14)
bearings = []
for x1, y1, x2, y2 in ls.reshape(-1, 4):
    Lp = math.hypot(x2-x1, y2-y1)
    ang = ground_angle((x1, y1, x2, y2), fov, pitch, (W, H))
    if ang is not None and np.isfinite(ang):
        bearings.append((abs(ang) % 180, Lp))
ang = np.array([b[0] for b in bearings]); wt = np.array([b[1] for b in bearings])
hist, edges = np.histogram(ang, bins=180, range=(0, 180), weights=wt)
hist = np.convolve(hist, np.ones(7)/7, "same")
road = float(np.argmax(hist)) + 0.5
mask = np.abs(((np.arange(180) - road + 90) % 180) - 90) > 5
edge = float(np.argmax(np.where(mask, hist, 0))) + 0.5
rel = abs(((edge - road + 90) % 180) - 90)
rate = math.tan(math.radians(rel))
print(f"\n{len(bearings)} ground bearings")
print(f"  road {road:.1f} deg, taper edge {edge:.1f} deg, relative {rel:.2f} deg")
print(f"  taper rate {rate:.3f}  ->  {3.0/rate:.1f} m on a 3.0 m lane, "
      f"equivalent {math.sqrt(155/rate):.1f} km/h")
before = json.load(open("results/taper_rate.json"))["measured"]
print(f"\nbefore (2025-06 Street View)  rate {before['taper_rate']}  "
      f"taper {3.0/before['taper_rate']:.1f} m  "
      f"{before['equivalent_design_speed_kmh']} km/h")
print(f"after  (2026-09 field F17)    rate {rate:.3f}  taper {3.0/rate:.1f} m  "
      f"{math.sqrt(155/rate):.1f} km/h")
json.dump({"horizon_y": round(float(y_h), 1), "horizon_from": src,
           "roll_deg": round(roll, 2), "pitch_deg": round(pitch, 2),
           "fov_deg": round(fov, 2), "focal_px": round(f, 1),
           "road_deg": round(road, 2), "edge_deg": round(edge, 2),
           "relative_deg": round(rel, 2), "taper_rate": round(rate, 3),
           "taper_m_on_3m_lane": round(3.0/rate, 1),
           "equivalent_kmh": round(math.sqrt(155/rate), 1),
           "before_rate": before["taper_rate"],
           "before_taper_m": round(3.0/before["taper_rate"], 1),
           "before_kmh": before["equivalent_design_speed_kmh"]},
          open("results/taper_after.json", "w"), indent=2)
