"""The erased share of the chevron, as a ground ratio rather than a picture one.

Three lines run parallel on the road: the 周圍邊線 still painted on the far
side, the edge where the paint now stops, and the edge the chevron used to
reach. The third was drawn by hand over F17 and registered here by homography;
it is an input, not a result, because seven automatic attempts to find it
failed and are written up in docs/thesis.md.

Parallel ground lines meet at a vanishing point in the photograph, and a
cross-ratio against that point turns image distances back into ground
distances exactly - no focal length, no camera height, no pitch. Each stripe
of the chevron is a transversal cutting all three lines, so the frame yields
one independent measurement per stripe and their spread is the error.

The stripes only become usable once the boundary line is taken out: in the
paint mask they are fused to it, 44% of all paint in one component, and the
fragments that connected-components does return are not stripes at all. An
opening with a line element along the band isolates the boundary; removing it
leaves the stripes separate.
"""
import cv2, numpy as np, json

F17 = "evidence/field-2026-09-20/IMG_20260920_155843.jpg"
SCR = "output/erasure/"   # scratch outputs; output/ is not in git
import os; os.makedirs(SCR, exist_ok=True)
im = cv2.imread(F17); H, W = im.shape[:2]
user = np.load("data/annotations/user_line_F17.npy")   # owner drawing, identical bytes to the old scratch copy

ox, oy, sc = int(W*0.10), int(H*0.42), 0.55
crop = cv2.resize(im[oy:int(H*0.62), ox:int(W*0.80)], None, fx=sc, fy=sc,
                  interpolation=cv2.INTER_AREA)
h, w = crop.shape[:2]
L = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
res = L - cv2.GaussianBlur(L, (0, 0), 25)
paint = cv2.morphologyEx((res > 14).astype(np.uint8), cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
tf = lambda p: np.array([p[0]/sc + ox, p[1]/sc + oy])

n, lbl, stats, _ = cv2.connectedComponentsWithStats(paint, 8)
big = max(range(1, n), key=lambda i: stats[i, cv2.CC_STAT_AREA])
ys, xs = np.nonzero(lbl == big)
_, _, vt = np.linalg.svd(np.stack([xs, ys], 1).astype(np.float32) -
                         np.stack([xs, ys], 1).mean(0), full_matrices=False)
band = float(np.degrees(np.arctan2(vt[0][1], vt[0][0])))

def line_se(length, ang):
    k = np.zeros((length | 1, length | 1), np.uint8); c = length // 2
    a = np.radians(ang)
    for t in np.linspace(-length/2, length/2, length*3):
        x, y = int(round(c + t*np.cos(a))), int(round(c + t*np.sin(a)))
        if 0 <= x < k.shape[1] and 0 <= y < k.shape[0]:
            k[y, x] = 1
    return k

bnd_raw = cv2.morphologyEx(paint, cv2.MORPH_OPEN, line_se(91, band))
bnd = cv2.dilate(bnd_raw, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
stripes = cv2.morphologyEx(cv2.bitwise_and(paint, cv2.bitwise_not(bnd)),
                           cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
ns, ls, ss, _ = cv2.connectedComponentsWithStats(stripes, 8)

# the datum is the boundary line furthest from the hand-drawn edge
nb, lb, sb, cb = cv2.connectedComponentsWithStats(bnd_raw, 8)
cands = [i for i in range(1, nb) if sb[i, cv2.CC_STAT_AREA] > 400]
def fitline(mask_i, labels):
    ys, xs = np.nonzero(labels == mask_i)
    p = np.stack([xs, ys], 1).astype(np.float32); m = p.mean(0)
    _, _, v = np.linalg.svd(p - m, full_matrices=False)
    d = v[0]/np.linalg.norm(v[0]); pr = (p - m) @ d
    return tf(m + d*pr.min()), tf(m + d*pr.max())

homog = lambda p: np.array([p[0], p[1], 1.0])
ln = lambda a, b: np.cross(homog(a), homog(b))
def meet(l1, l2):
    p = np.cross(l1, l2)
    return p[:2]/p[2] if abs(p[2]) > 1e-9 else None

l_user = ln(*user)
best = None
for i in cands:
    a, b = fitline(i, lb)
    mid = (a + b)/2
    dist = abs(np.dot(l_user/np.linalg.norm(l_user[:2]), homog(mid)))
    if best is None or dist > best[0]:
        best = (dist, a, b, i)
_, da, db_, di = best
datum = np.array([da, db_])
print(f"boundary candidates {len(cands)}; datum is the far one, "
      f"{best[0]:.0f} px from the drawn edge")
l_datum = ln(*datum)
V = meet(l_datum, l_user)
print(f"vanishing point ({V[0]:.0f}, {V[1]:.0f})")

rows = []
for i in range(1, ns):
    if ss[i, cv2.CC_STAT_AREA] < 150:
        continue
    yy, xx = np.nonzero(ls == i)
    p = np.stack([xx, yy], 1).astype(np.float32); m = p.mean(0)
    _, _, v = np.linalg.svd(p - m, full_matrices=False)
    d = v[0]/np.linalg.norm(v[0]); pr = (p - m) @ d
    if pr.max() - pr.min() < 20:
        continue
    a, b = tf(m + d*pr.min()), tf(m + d*pr.max())
    # a stripe crosses the band, so it should be far from parallel to it
    ang = abs((np.degrees(np.arctan2((b-a)[1], (b-a)[0])) - band) % 180)
    if min(ang, 180-ang) < 18:
        continue
    tr = ln(a, b)
    A, C = meet(tr, l_datum), meet(tr, l_user)
    if A is None or C is None:
        continue
    B = b if np.linalg.norm(b - C) < np.linalg.norm(a - C) else a
    AB, AC = np.linalg.norm(B-A), np.linalg.norm(C-A)
    VB, VC = np.linalg.norm(B-V), np.linalg.norm(C-V)
    if AC < 40 or AB > AC:
        continue
    g = (AB*VC)/(AC*VB)
    if not (0.05 < g < 1.05):
        continue
    rows.append({"cc": int(i), "image": round(float(AB/AC), 3),
                 "ground": round(float(g), 3), "erased": round(float(1-g), 3)})

e = np.array([r["erased"] for r in rows])
print(f"\n{len(rows)} stripes cut all three lines")
if len(e):
    med, mad = np.median(e), np.median(np.abs(e - np.median(e)))
    k = np.abs(e - med) < 3*1.4826*max(mad, 1e-3)
    print(f"{int(k.sum())} within 3 robust sigma\n")
    print(f"erased share of the original chevron width, on the ground:")
    print(f"  median {np.median(e[k])*100:.0f}%   mean {e[k].mean()*100:.0f}%   "
          f"sd {e[k].std()*100:.0f}%   n={int(k.sum())}")
    print(f"  quartiles {np.percentile(e[k],25)*100:.0f}% - "
          f"{np.percentile(e[k],75)*100:.0f}%")
    im_med = np.median([r['image'] for r in rows])
    print(f"\n  read straight off the image, without the cross-ratio, the same "
          f"stripes give {(1-im_med)*100:.0f}% - that difference is perspective")
json.dump({"source": F17,
           "original_edge": "hand-drawn by the site owner, registered to F17 by "
                            "SIFT homography",
           "vanishing_point": [round(float(V[0]), 1), round(float(V[1]), 1)],
           "n_stripes": int(k.sum()) if len(e) else 0,
           "erased_share_median": round(float(np.median(e[k])), 3) if len(e) else None,
           "erased_share_sd": round(float(e[k].std()), 3) if len(e) else None,
           "per_stripe": rows}, open("results/erasure_ratio.json", "w"), indent=2)
np.save(SCR + "datum.npy", datum)
