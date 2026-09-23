"""How much of the right-hand edge is not carriageway.

The site owner marks the outermost strip - drain covers and the red kerbside
line - and says the real edge of the running surface is the line inside it.
That changes the width budget: the earlier sum gave a motorcycle the side of
a lane to sit in, and if that side is grating and a no-stopping line then it
was never lane to begin with.

The strip's width is measurable. The Street View request fixes fov and pitch,
so pixel to ground is exact up to the camera's height, and §182 puts a lane
dash at 4 m, which supplies the height.
"""
import sys, json, math
import cv2, numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image   # noqa: E402

ANNOT = "data/annotations/"   # owner drawings; data/ is not in git
STEM = "before_p-25"
meta = json.load(open(f"output/api/{STEM}.json"))
base = cv2.imread(f"output/api/{STEM}.jpg"); H, W = base.shape[:2]
ann = cv2.imread(ANNOT + "annotation_7.webp")
small = cv2.resize(base, (ann.shape[1], int(ann.shape[1]*H/W)))
sift = cv2.SIFT_create(6000); bf = cv2.BFMatcher()
ka, da = sift.detectAndCompute(cv2.cvtColor(ann, cv2.COLOR_BGR2GRAY), None)
kb, db = sift.detectAndCompute(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), None)
mt = [x for x, y in bf.knnMatch(da, db, k=2) if x.distance < 0.72*y.distance]
Hm, inl = cv2.findHomography(
    np.float32([ka[x.queryIdx].pt for x in mt]).reshape(-1, 1, 2),
    np.float32([kb[x.trainIdx].pt for x in mt]).reshape(-1, 1, 2), cv2.RANSAC, 3.0)
k = W/ann.shape[1]
def to_base(p):
    q = Hm @ np.array([p[0], p[1], 1.0]); return (q[:2]/q[2])*k
print(f"annotation registered to {STEM}, {int(inl.sum())} inliers; "
      f"fov {meta['fov']}, pitch {meta['pitch']}")

hsv = cv2.cvtColor(ann, cv2.COLOR_BGR2HSV)
red = (((hsv[:, :, 0] < 10) | (hsv[:, :, 0] > 170)) &
       (hsv[:, :, 1] > 110) & (hsv[:, :, 2] > 110)).astype(np.uint8)*255
# the two long dashed lines run steeply; the arrows are short. Bridge along
# the line direction only, so arrowheads do not merge into them.
best = None
for ang in range(100, 171, 2):
    se = np.zeros((81, 81), np.uint8)
    t = math.radians(ang)
    for s in np.linspace(-40, 40, 240):
        x, y = int(round(40+s*math.cos(t))), int(round(40+s*math.sin(t)))
        se[y, x] = 1
    # close, not open: a dashed line has gaps, and opening deletes it
    c = cv2.morphologyEx(red, cv2.MORPH_CLOSE, se)
    o = cv2.morphologyEx(c, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    # score by how much of the mask ends up in long thin components
    nn2, ll2, ss2, _ = cv2.connectedComponentsWithStats(o, 8)
    score = sum(ss2[i, cv2.CC_STAT_AREA] for i in range(1, nn2)
                if max(ss2[i, cv2.CC_STAT_WIDTH],
                       ss2[i, cv2.CC_STAT_HEIGHT]) > 150)
    if best is None or score > best[1]:
        best = (ang, score, o)
ang, _, joined = best
print(f"annotation line direction {ang} deg")
n, lbl, st, _ = cv2.connectedComponentsWithStats(joined, 8)
lines = []
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < 200: continue
    ys, xs = np.nonzero(lbl == i)
    p = np.stack([xs, ys], 1).astype(np.float32); c = p.mean(0)
    _, _, v = np.linalg.svd(p - c, full_matrices=False)
    d = v[0]/np.linalg.norm(v[0]); pr = (p - c) @ d
    if pr.max()-pr.min() < 150: continue
    lines.append((to_base(c + d*pr.min()), to_base(c + d*pr.max()),
                  float(pr.max()-pr.min())))
lines.sort(key=lambda s: -s[2])
print(f"{len(lines)} long red lines")
for i, (a, b, L) in enumerate(lines):
    print(f"  {i}: ({a[0]:5.0f},{a[1]:5.0f}) -> ({b[0]:5.0f},{b[1]:5.0f})")
if len(lines) < 2:
    sys.exit("need both edges of the strip")

# --- the scale: a lane dash in the unannotated capture ---------------------
L = cv2.cvtColor(base, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
paint = cv2.morphologyEx(
    ((L - cv2.GaussianBlur(L, (0, 0), 21)) > 16).astype(np.uint8), cv2.MORPH_OPEN,
    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
paint[:int(H*0.45)] = 0
nn, ll, ss, cc = cv2.connectedComponentsWithStats(paint, 8)
dashes = []
for i in range(1, nn):
    a = ss[i, cv2.CC_STAT_AREA]
    if a < 60: continue
    ys, xs = np.nonzero(ll == i)
    p = np.stack([xs, ys], 1).astype(np.float32); c = p.mean(0)
    _, _, v = np.linalg.svd(p - c, full_matrices=False)
    d = v[0]/np.linalg.norm(v[0]); pr = (p - c) @ d
    Lp = pr.max()-pr.min()
    th = np.abs((p - c) @ np.array([-d[1], d[0]])).max()*2
    if Lp < 12 or th < 1 or Lp/th < 3.5 or Lp/th > 40: continue
    # a lane dash runs with the road, not across it
    bearing = math.degrees(math.atan2(d[1], d[0])) % 180
    if not (55 < bearing < 125): continue
    g = ground_from_image([c + d*pr.min(), c + d*pr.max()],
                          meta["fov"], meta["pitch"], (W, H))
    if not np.isfinite(g).all(): continue
    dashes.append((float(np.linalg.norm(g[1]-g[0])), Lp, tuple(c)))
print(f"\n{len(dashes)} dash-shaped marks running with the road")
if not dashes:
    sys.exit("no lane dash found for the scale")
gl = np.array([d[0] for d in dashes])
print(f"  ground lengths in camera heights: "
      f"{' '.join(f'{x:.3f}' for x in np.sort(gl)[:10])}")
med = float(np.median(gl))
height = 4.00/med
print(f"  median {med:.3f} -> camera height {height:.2f} m "
      f"(Street View sits near 2.5 m)")
if not (1.8 < height < 3.4):
    print("  REFUSING: that height is not a Street View camera, so one of the "
          "inputs is not what it was taken to be")
    sys.exit(1)

g0 = ground_from_image(list(lines[0][:2]), meta["fov"], meta["pitch"], (W, H))
g1 = ground_from_image(list(lines[1][:2]), meta["fov"], meta["pitch"], (W, H))
if not (np.isfinite(g0).all() and np.isfinite(g1).all()):
    sys.exit("an annotation line does not meet the ground")
d0 = (g0[1]-g0[0]); d0 /= np.linalg.norm(d0)
nrm = np.array([-d0[1], d0[0]])
sep = abs(float((g1.mean(0) - g0[0]) @ nrm))*height
print(f"\nstrip between the two marked lines: {sep:.2f} m")
print(f"  that is drain grating and a no-stopping line, not running surface")
json.dump({"capture": STEM, "camera_height_m": round(height, 2),
           "dash_m": 4.00, "strip_width_m": round(sep, 2),
           "what": "drain covers plus the kerbside red line, marked by the "
                   "site owner as outside the normal carriageway"},
          open("results/drain_strip.json", "w"), indent=2, ensure_ascii=False)
