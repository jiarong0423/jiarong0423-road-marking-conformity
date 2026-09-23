"""The chevron's width before and after, from the marking's own geometry.

§171 sets the stripes 20 cm wide at 30 cm spacing, so they repeat every
50 cm. That is a ruler lying in the road plane, and it is in both the
2025-06 Street View frame and the 2026-09 field photograph.

Two vanishing points are recoverable from the marking alone - one where the
band's boundary lines meet, one where the stripes meet - and the line
through them is the road plane's horizon. Sending that line to infinity
affinely rectifies the plane. Angles are still wrong afterwards, but ratios
of lengths along parallel directions are true, which is all that is needed:
the band's width is a stripe's length, the ruler is the stripe spacing, and
both are measured in the same rectified frame.

The point of doing it this way is that it does not use the imprint at all.
The 64% in results/erasure_ratio.json came from a hand-drawn edge over the
erased chevron. This comes from two photographs of the paint itself, three
years apart. They should agree, and if they do not, one of them is wrong.
"""
import cv2, numpy as np, json, sys

def load(path, box=None, scale=1.0):
    im = cv2.imread(path)
    if im is None:
        sys.exit(f"missing {path}")
    if box:
        H, W = im.shape[:2]
        im = im[int(H*box[1]):int(H*box[3]), int(W*box[0]):int(W*box[2])]
    if scale != 1.0:
        im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return im

def paint_mask(im):
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    res = L - cv2.GaussianBlur(L, (0, 0), 25)
    return cv2.morphologyEx((res > 14).astype(np.uint8), cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

def line_se(length, ang):
    k = np.zeros((length | 1, length | 1), np.uint8); c = length // 2
    a = np.radians(ang)
    for t in np.linspace(-length/2, length/2, length*3):
        x, y = int(round(c + t*np.cos(a))), int(round(c + t*np.sin(a)))
        if 0 <= x < k.shape[1] and 0 <= y < k.shape[0]:
            k[y, x] = 1
    return k

def principal(mask, i, labels):
    ys, xs = np.nonzero(labels == i)
    p = np.stack([xs, ys], 1).astype(np.float32); m = p.mean(0)
    _, _, v = np.linalg.svd(p - m, full_matrices=False)
    d = v[0]/np.linalg.norm(v[0]); pr = (p - m) @ d
    return m + d*pr.min(), m + d*pr.max()

def vp(segs):
    """Least-squares meeting point of a bundle of lines."""
    A, b = [], []
    for a, c in segs:
        l = np.cross([a[0], a[1], 1.0], [c[0], c[1], 1.0])
        A.append(l[:2]); b.append(-l[2])
    A, b = np.array(A), np.array(b)
    return np.linalg.lstsq(A, b, rcond=None)[0]

def analyse(name, im):
    pm = paint_mask(im)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(pm, 8)
    big = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_AREA])
    a, c = principal(pm, big, lbl)
    band_ang = float(np.degrees(np.arctan2((c-a)[1], (c-a)[0])))

    bnd_raw = cv2.morphologyEx(pm, cv2.MORPH_OPEN, line_se(61, band_ang))
    bnd = cv2.dilate(bnd_raw, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    stp = cv2.morphologyEx(cv2.bitwise_and(pm, cv2.bitwise_not(bnd)),
                           cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

    nb, lb, sb, _ = cv2.connectedComponentsWithStats(bnd_raw, 8)
    bsegs = [principal(bnd_raw, i, lb) for i in range(1, nb)
             if sb[i, cv2.CC_STAT_AREA] > 250]
    ns, ls, ss, _ = cv2.connectedComponentsWithStats(stp, 8)
    ssegs = []
    for i in range(1, ns):
        if ss[i, cv2.CC_STAT_AREA] < 120:
            continue
        p, q = principal(stp, i, ls)
        if np.linalg.norm(q-p) < 15:
            continue
        ang = abs((np.degrees(np.arctan2((q-p)[1], (q-p)[0])) - band_ang) % 180)
        if min(ang, 180-ang) < 15:
            continue
        ssegs.append((p, q))
    if len(bsegs) < 2 or len(ssegs) < 4:
        return {"name": name, "ok": False,
                "why": f"{len(bsegs)} boundary, {len(ssegs)} stripe segments"}

    V1, V2 = vp(bsegs), vp(ssegs)
    hz = np.cross([V1[0], V1[1], 1.0], [V2[0], V2[1], 1.0])
    hz = hz/np.linalg.norm(hz[:2])
    Ha = np.array([[1, 0, 0], [0, 1, 0], hz], float)

    def warp(p):
        q = Ha @ np.array([p[0], p[1], 1.0])
        return q[:2]/q[2]

    # in the affine frame, stripe length is the band width and the spacing
    # between consecutive stripes is 0.50 m by §171
    mids, lens = [], []
    for p, q in ssegs:
        wp, wq = warp(p), warp(q)
        if not (np.isfinite(wp).all() and np.isfinite(wq).all()):
            continue
        lens.append(np.linalg.norm(wq-wp)); mids.append((wp+wq)/2)
    if len(lens) < 4:
        return {"name": name, "ok": False, "why": "too few stripes survive the warp"}
    mids = np.array(mids); lens = np.array(lens)
    u = warp(V1) if np.isfinite(warp(V1)).all() else None
    # order the stripes along the band and take consecutive spacings
    dirv = mids[-1]-mids[0]; dirv /= np.linalg.norm(dirv)
    t = np.sort(mids @ dirv)
    sp = np.diff(t)
    sp = sp[(sp > np.percentile(sp, 10)) & (sp < np.percentile(sp, 90))]
    if len(sp) < 3:
        return {"name": name, "ok": False, "why": "no stable stripe spacing"}
    period = float(np.median(sp))
    width_m = float(np.median(lens)) / period * 0.50
    return {"name": name, "ok": True, "stripes": len(lens),
            "period_affine": round(period, 2),
            "stripe_len_affine": round(float(np.median(lens)), 2),
            "band_width_m": round(width_m, 2),
            "band_width_sd_m": round(float(np.std(lens))/period*0.50, 2)}

jobs = [("2025-06 Street View, before", load("output/api/before_p-40.jpg")),
        ("2025-06 Street View, before (2)", load("output/api/before_p-25.jpg")),
        ("2026-09 field F17, after",
         load("evidence/field-2026-09-20/IMG_20260920_155843.jpg",
              box=(0.10, 0.42, 0.80, 0.62), scale=0.55))]
out = []
for name, im in jobs:
    r = analyse(name, im); out.append(r)
    if r["ok"]:
        print(f"{name:34s} {r['stripes']:3d} stripes  spacing {r['period_affine']:6.2f}  "
              f"stripe {r['stripe_len_affine']:7.2f}  ->  band {r['band_width_m']:5.2f} m "
              f"+- {r['band_width_sd_m']:.2f}")
    else:
        print(f"{name:34s} FAILED: {r['why']}")

ok = [r for r in out if r["ok"]]
bef = [r for r in ok if "before" in r["name"]]
aft = [r for r in ok if "after" in r["name"]]
if bef and aft:
    b = float(np.mean([r["band_width_m"] for r in bef]))
    a = aft[0]["band_width_m"]
    print(f"\nband width before {b:.2f} m, after {a:.2f} m")
    print(f"erased {100*(1-a/b):.0f}% of the original width")
    print(f"  the imprint-and-drawn-edge route gave 64% "
          f"(results/erasure_ratio.json)")
json.dump({"method": "affine rectification from the band and stripe vanishing "
                     "points; scale from the §171 50 cm stripe period",
           "results": out}, open("results/band_width.json", "w"), indent=2,
          ensure_ascii=False)
