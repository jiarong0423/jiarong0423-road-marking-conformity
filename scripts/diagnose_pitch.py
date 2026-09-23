"""Is the pitch the request asks for the pitch the camera had?

Stripe widths recovered from nine captures of one chevron imply camera
heights that climb with the pitch: 2.38 m at -20 degrees, 4.05 at -35,
9.96 at -42. One camera photographed all nine, so the height is a constant
and the trend is an error in how pitch is being used.

Two explanations are separable from this data. If the Static API's pitch is
offset from the rotation the rectification assumes, one constant offset will
flatten the whole series. If instead the rectification mishandles pitch, no
single offset will, and the residual will keep its shape.

This matters beyond the heights: rectify.py is underneath the 0.202 taper
rate that the rest of the project rests on.
"""
import sys, json, math
import cv2, numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image   # noqa: E402

STRIPE_W = 0.20

def cuts(stem):
    """The stripe's two edges, in pixels, at several stations. Pitch-free."""
    meta = json.load(open(f"output/api/{stem}.json"))
    im = cv2.imread(f"output/api/{stem}.jpg"); H, W = im.shape[:2]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    paint = cv2.morphologyEx(
        ((L - cv2.GaussianBlur(L, (0, 0), 25)) > 14).astype(np.uint8),
        cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(paint, 8)
    if n < 2: return meta, (W, H), []
    big = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_AREA])
    ys, xs = np.nonzero(lbl == big)
    p = np.stack([xs, ys], 1).astype(np.float32)
    _, _, v = np.linalg.svd(p - p.mean(0), full_matrices=False)
    band = math.degrees(math.atan2(v[0][1], v[0][0]))
    def se(length, ang):
        k = np.zeros((length | 1, length | 1), np.uint8); c = length//2
        t = math.radians(ang)
        for s in np.linspace(-length/2, length/2, length*3):
            x, y = int(round(c+s*math.cos(t))), int(round(c+s*math.sin(t)))
            if 0 <= x < k.shape[1] and 0 <= y < k.shape[0]: k[y, x] = 1
        return k
    bnd = cv2.dilate(cv2.morphologyEx(paint, cv2.MORPH_OPEN, se(61, band)),
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    stp = cv2.morphologyEx(cv2.bitwise_and(paint, cv2.bitwise_not(bnd)),
                           cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    ns, ls, ss, _ = cv2.connectedComponentsWithStats(stp, 8)
    out = []
    for i in range(1, ns):
        if ss[i, cv2.CC_STAT_AREA] < 200: continue
        yy, xx = np.nonzero(ls == i)
        q = np.stack([xx, yy], 1).astype(np.float32); c = q.mean(0)
        if c[1] < H*0.55: continue
        _, _, vv = np.linalg.svd(q - c, full_matrices=False)
        d = vv[0]/np.linalg.norm(vv[0]); nr = np.array([-d[1], d[0]])
        al = (q-c) @ d; ac = (q-c) @ nr
        if al.max()-al.min() < 25: continue
        for t in np.linspace(al.min()+6, al.max()-6, 7):
            sel = np.abs(al-t) < 3
            if sel.sum() < 10: continue
            mid = c + d*t
            out.append((mid + nr*ac[sel].min(), mid + nr*ac[sel].max()))
    return meta, (W, H), out

data = []
for stem in ["before_close", "before_p-25", "before_p-40", "f40_p-20",
             "f40_p-35", "f60_p-20", "f60_p-35", "f90_p-20", "f90_p-35"]:
    meta, size, cc = cuts(stem)
    if len(cc) >= 8:
        data.append((stem, meta, size, cc))
print(f"{len(data)} captures with enough stripe cuts")

def heights(delta):
    hs = {}
    for stem, meta, size, cc in data:
        vals = []
        for a, b in cc:
            g = ground_from_image([a, b], meta["fov"], meta["pitch"]+delta, size)
            if not np.isfinite(g).all(): continue
            w = float(np.linalg.norm(g[1]-g[0]))
            if w > 1e-9: vals.append(STRIPE_W/w)
        if len(vals) >= 8:
            v = np.array(vals); m, md = np.median(v), np.median(np.abs(v-np.median(v)))
            k = np.abs(v-m) < 3*1.4826*max(md, 1e-9)
            hs[stem] = (float(np.median(v[k])), meta["pitch"], meta["fov"])
    return hs

print(f"\n{'delta':>7}{'captures':>10}{'height mean':>13}{'sd':>8}{'spread':>9}")
best = None
for delta in np.arange(-12, 12.01, 0.5):
    hs = heights(float(delta))
    if len(hs) < len(data)-1: continue
    h = np.array([v[0] for v in hs.values()])
    if h.max() > 20 or h.min() < 0.3: continue
    sd = float(h.std())
    if best is None or sd < best[1]: best = (float(delta), sd, hs)
    if abs(delta) % 3 < 0.25:
        print(f"{delta:>7.1f}{len(hs):>10}{h.mean():>13.2f}{sd:>8.2f}"
              f"{h.max()-h.min():>9.2f}")
if best:
    delta, sd, hs = best
    h = np.array([v[0] for v in hs.values()])
    print(f"\nbest single offset: {delta:+.1f} deg, heights {h.mean():.2f} m "
          f"sd {sd:.2f}")
    for s, (v, p, f) in sorted(hs.items(), key=lambda kv: kv[1][1]):
        print(f"  {s:14s} pitch {p:>4} fov {f:>3}  ->  {v:5.2f} m")
    if sd < 0.3:
        print("\n  one offset flattens the series: the API's pitch differs from "
              "the rotation the rectification assumes, by that amount")
    else:
        print("\n  no single offset flattens it, so this is not a convention "
              "mismatch - the rectification itself mishandles pitch")
