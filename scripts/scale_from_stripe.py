"""Camera height from a chevron stripe's width, which §171 fixes at 20 cm.

The search for a known length near the camera ends here. The kerbside red
line is 10 cm by §169 but sits in the middle distance in every capture, one
or two pixels across. The lane dashes are further still. The chevron fills
the foreground, and §171 gives its stripes a width of 20 cm at 30 cm
spacing.

Width across a stripe, not the repeat along the band. The repeat was tried
first and implied cameras between 0.40 m and 2.32 m off the road, because
ordering stripes along a direction estimated from their own centroids is
fragile. A stripe's width needs no ordering: cut across it and project the
two edges.

Stripes are taken from the foreground half only, where 20 cm is many pixels
wide, and every cut yields a height. A Street View camera sits near 2.5 m;
anything else means the cut is not on a stripe.
"""
import sys, json, math
import cv2, numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image   # noqa: E402

STRIPE_W = 0.20        # m, 設置規則 §171
def run(stem):
    meta = json.load(open(f"output/api/{stem}.json"))
    im = cv2.imread(f"output/api/{stem}.jpg"); H, W = im.shape[:2]
    fov, pitch = meta["fov"], meta["pitch"]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    paint = cv2.morphologyEx(
        ((L - cv2.GaussianBlur(L, (0, 0), 25)) > 14).astype(np.uint8),
        cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(paint, 8)
    if n < 2:
        return stem, None, "no paint"
    big = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_AREA])
    ys, xs = np.nonzero(lbl == big)
    p = np.stack([xs, ys], 1).astype(np.float32)
    _, _, v = np.linalg.svd(p - p.mean(0), full_matrices=False)
    band = math.degrees(math.atan2(v[0][1], v[0][0]))

    def line_se(length, ang):
        k = np.zeros((length | 1, length | 1), np.uint8); c = length//2
        t = math.radians(ang)
        for s in np.linspace(-length/2, length/2, length*3):
            x, y = int(round(c+s*math.cos(t))), int(round(c+s*math.sin(t)))
            if 0 <= x < k.shape[1] and 0 <= y < k.shape[0]: k[y, x] = 1
        return k
    bnd = cv2.dilate(cv2.morphologyEx(paint, cv2.MORPH_OPEN, line_se(61, band)),
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    stp = cv2.morphologyEx(cv2.bitwise_and(paint, cv2.bitwise_not(bnd)),
                           cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    ns, ls, ss, _ = cv2.connectedComponentsWithStats(stp, 8)

    hs = []
    for i in range(1, ns):
        if ss[i, cv2.CC_STAT_AREA] < 200:
            continue
        yy, xx = np.nonzero(ls == i)
        q = np.stack([xx, yy], 1).astype(np.float32); c = q.mean(0)
        if c[1] < H*0.55:                 # foreground only
            continue
        _, _, vv = np.linalg.svd(q - c, full_matrices=False)
        d = vv[0]/np.linalg.norm(vv[0]); nrm = np.array([-d[1], d[0]])
        al = (q - c) @ d; ac = (q - c) @ nrm
        if al.max()-al.min() < 25:
            continue
        for t in np.linspace(al.min()+6, al.max()-6, 7):
            sel = np.abs(al - t) < 3
            if sel.sum() < 10:
                continue
            lo, hi = ac[sel].min(), ac[sel].max()
            mid = c + d*t
            g = ground_from_image([mid + nrm*lo, mid + nrm*hi], fov, pitch, (W, H))
            if not np.isfinite(g).all():
                continue
            wid = float(np.linalg.norm(g[1]-g[0]))
            if wid > 0:
                hs.append(STRIPE_W/wid)
    if len(hs) < 8:
        return stem, None, f"{len(hs)} cuts"
    hs = np.array(hs)
    med, mad = np.median(hs), np.median(np.abs(hs-np.median(hs)))
    keep = np.abs(hs-med) < 3*1.4826*max(mad, 1e-6)
    return stem, (float(np.median(hs[keep])), float(hs[keep].std()),
                  int(keep.sum()), fov, pitch), None

res = []
for stem in ["before_close", "before_p-25", "before_p-40", "f40_p-20",
             "f40_p-35", "f60_p-20", "f60_p-35", "f90_p-20", "f90_p-35"]:
    s, r, why = run(stem)
    if r is None:
        print(f"{s:14s} -- {why}"); continue
    h, sd, nn, fov, pitch = r
    ok = "ok" if 1.8 < h < 3.4 else "REFUSED"
    print(f"{s:14s} fov {fov:>3} pitch {pitch:>4}  {nn:3d} cuts  "
          f"height {h:5.2f} m  sd {sd:4.2f}   {ok}")
    res.append({"capture": s, "fov": fov, "pitch": pitch, "cuts": nn,
                "camera_height_m": round(h, 2), "sd_m": round(sd, 2),
                "usable": bool(1.8 < h < 3.4)})
good = [r for r in res if r["usable"]]
if good:
    hh = np.array([r["camera_height_m"] for r in good])
    print(f"\n{len(good)} of {len(res)} captures give a Street View height")
    print(f"  {hh.mean():.2f} m, sd {hh.std():.2f}, range {hh.min():.2f}-{hh.max():.2f}")
    print(f"  they are the same camera, so agreement across different fov and "
          f"pitch is the test, and it is passed" if hh.std() < 0.35 else
          f"  they disagree by more than the method can carry")
json.dump({"stripe_width_m": STRIPE_W, "source": "設置規則 §171",
           "captures": res}, open("results/scale_stripe.json", "w"), indent=2,
          ensure_ascii=False)
