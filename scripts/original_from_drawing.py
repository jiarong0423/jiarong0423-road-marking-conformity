"""The original chevron in metres, from three lines drawn on the 2025 frame.

The Street View request fixes the field of view and the pitch, so pixel to
ground is exact up to the camera's height. Recovering that height from the
stripe repeat failed its own check - it implied cameras between 0.40 m and
2.32 m off the road, and Street View sits near 2.5 m - so the scale comes
from a marking whose length is stated rather than inferred: §182 puts a lane
dash at 4 m.

    drawn 1, 2   the chevron's two edges       -> band width, camera heights
    drawn 3      one lane dash, end to end     -> 4.00 m, so the height

Nothing else is assumed. The height is solved, not looked up, and printing
it is the check: a value far from about 2.5 m means one of the three lines
is not what it was taken to be.

Usage: put the annotated image at the path below and run. The lines are
recovered by differencing against the unmarked capture, the same way the
earlier hand-drawn edge was.
"""
import sys, json, math
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image   # noqa: E402

ANNOT = Path(__file__).resolve().parents[1] / "data" / "annotations"   # owner drawings; data/ is not in git
ANN = Path(sys.argv[1]) if len(sys.argv) > 1 else ANNOT / "annotation_7.webp"
STEM = sys.argv[2] if len(sys.argv) > 2 else "before_p-25"
DASH_M = 4.00        # §182 車道線 line segment

meta = json.load(open(f"output/api/{STEM}.json"))
base = cv2.imread(f"output/api/{STEM}.jpg")
ann = cv2.imread(str(ANN))
if ann is None:
    sys.exit(f"no annotated image at {ANN}")
H0, W0 = base.shape[:2]
print(f"{STEM}: fov {meta['fov']}, pitch {meta['pitch']}, {W0}x{H0}")

small = cv2.resize(base, (ann.shape[1], int(ann.shape[1]*H0/W0)))
sift = cv2.SIFT_create(6000); bf = cv2.BFMatcher()
ka, da = sift.detectAndCompute(cv2.cvtColor(ann, cv2.COLOR_BGR2GRAY), None)
kb, db = sift.detectAndCompute(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), None)
mt = [x for x, y in bf.knnMatch(da, db, k=2) if x.distance < 0.7*y.distance]
Hm, inl = cv2.findHomography(
    np.float32([ka[x.queryIdx].pt for x in mt]).reshape(-1, 1, 2),
    np.float32([kb[x.trainIdx].pt for x in mt]).reshape(-1, 1, 2), cv2.RANSAC, 3.0)
print(f"registered, {int(inl.sum())} inliers")
warp = cv2.warpPerspective(small, np.linalg.inv(Hm), (ann.shape[1], ann.shape[0]))
d = (cv2.cvtColor(ann, cv2.COLOR_BGR2GRAY).astype(np.int16)
     - cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY).astype(np.int16))
mk = ((d > 25) & (warp.sum(2) > 0)).astype(np.uint8)*255
m2 = np.zeros_like(mk); m2[20:-20, 20:-20] = 255
mk = cv2.bitwise_and(mk, m2)

# join dashes in several directions so a diagonal line is not smeared
joined = np.zeros_like(mk)
for ang in range(0, 180, 15):
    se = cv2.getStructuringElement(cv2.MORPH_RECT, (61, 1))
    M = cv2.getRotationMatrix2D((30, 0), ang, 1.0)
    se = cv2.warpAffine(se, M, (61, 61))[:, :]
    joined = cv2.bitwise_or(joined, cv2.morphologyEx(mk, cv2.MORPH_CLOSE,
                                                     (se > 0).astype(np.uint8)))
n, lbl, st, _ = cv2.connectedComponentsWithStats(joined, 8)
k = W0/ann.shape[1]
segs = []
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < 250:
        continue
    ys, xs = np.nonzero(lbl == i)
    p = np.stack([xs, ys], 1).astype(np.float32); c = p.mean(0)
    _, _, v = np.linalg.svd(p - c, full_matrices=False)
    dv = v[0]/np.linalg.norm(v[0]); pr = (p - c) @ dv
    L = pr.max()-pr.min()
    if L < 60 or np.abs((p-c) @ np.array([-dv[1], dv[0]])).max() > L*0.16:
        continue
    def up(q):
        r = Hm @ np.array([q[0], q[1], 1.0]); return (r[:2]/r[2])*k
    segs.append((up(c+dv*pr.min()), up(c+dv*pr.max()), float(L)))
segs.sort(key=lambda s: -s[2])
print(f"{len(segs)} drawn lines found")
for i, (a, b, L) in enumerate(segs):
    print(f"  {i}: ({a[0]:6.0f},{a[1]:6.0f}) -> ({b[0]:6.0f},{b[1]:6.0f})  "
          f"len {L*k:5.0f} px")
if len(segs) < 3:
    sys.exit("need three: the chevron's two edges and one lane dash")

def ground(p, q):
    g = ground_from_image([p, q], meta["fov"], meta["pitch"], (W0, H0))
    return g if np.isfinite(g).all() else None

# the dash is the shortest of the three; the two edges are the long ones
segs3 = segs[:3]
dash = min(segs3, key=lambda s: s[2])
edges = [s for s in segs3 if s is not dash]
gd = ground(dash[0], dash[1])
if gd is None:
    sys.exit("the dash does not project onto the ground - is it above the horizon?")
height = DASH_M / float(np.linalg.norm(gd[1]-gd[0]))
print(f"\nlane dash = {DASH_M} m  ->  camera height {height:.2f} m")
print("  Street View sits near 2.5 m; far from it means a line is misread")

ge = [ground(a, b) for a, b, _ in edges]
if any(g is None for g in ge):
    sys.exit("an edge does not project onto the ground")
def line2(g):
    d = g[1]-g[0]; d /= np.linalg.norm(d); return g[0], d
p0, d0 = line2(ge[0]); p1, d1 = line2(ge[1])
nrm = np.array([-d0[1], d0[0]])
sep = abs(float((p1 - p0) @ nrm)) * height
ang = math.degrees(math.acos(abs(float(d0 @ d1))))
print(f"\noriginal chevron band width {sep:.2f} m")
print(f"  the two edges differ in ground bearing by {ang:.2f} deg "
      f"(a chevron's edges converge, so a few degrees is expected)")
print(f"\nwith 64% erased (results/erasure_ratio.json):")
print(f"  removed {sep*0.64:.2f} m, left {sep*0.36:.2f} m")
json.dump({"capture": STEM, "fov": meta["fov"], "pitch": meta["pitch"],
           "dash_m": DASH_M, "camera_height_m": round(height, 2),
           "band_width_m": round(sep, 2), "edge_convergence_deg": round(ang, 2),
           "erased_share": 0.64, "removed_m": round(sep*0.64, 2),
           "remaining_m": round(sep*0.36, 2)},
          open("results/original_chevron.json", "w"), indent=2)
