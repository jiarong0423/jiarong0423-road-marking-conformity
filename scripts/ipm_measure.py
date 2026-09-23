"""Measure the chevron in the bird's eye plane, where scale is a constant.

Three failures in this project share one cause: operators sized in pixels,
applied to images whose ground sampling varies several-fold across the frame
and between captures. A 61-pixel line element that lifts a boundary line out
of one capture eats the stripes in another; stripes that are near-parallel
and short give a vanishing point that lands inside the frame; and telling the
road from the taper edge by which angle window a bearing falls in assumes the
camera faces along the road.

The standard answer in the lane-detection literature is to invert the
perspective first and filter afterwards. In the bird's eye plane a pixel is a
fixed ground distance, so a kernel is a real length; parallel ground lines
are parallel; and a measured angle is a ground angle. All three faults are
properties of the frontal image, not of the road.

Two limits from the same literature are respected here rather than noted:

  flat ground   IPM assumes it, and this site sits near the foot of a bridge
                approach, so only the near field is mapped.
  far stretch   resolution falls off with range and IPM magnifies it, so the
                mapped region stops well short of the horizon.

Calibration, which is usually the obstacle, is exact: the Static API is told
the fov and pitch, and tests/test_pitch_roundtrip.py confirms the projection
returns a known ground length to six decimals at every pitch used here.
"""
import sys, json, math
import cv2, numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image, focal_px   # noqa: E402

PX_PER_H = 260.0      # bird's eye pixels per camera height
NEAR, FAR = 0.6, 4.0  # camera heights ahead: the near field only
HALF = 2.2            # camera heights either side
STRIPE_W = 0.20       # m, 設置規則 §171

def ipm(im, fov, pitch):
    """Frontal image to bird's eye, in camera-height units."""
    H, W = im.shape[:2]
    f = focal_px(fov, W)
    t = math.radians(pitch)
    R = np.array([[1, 0, 0],
                  [0, math.cos(t), -math.sin(t)],
                  [0, math.sin(t), math.cos(t)]])
    out_w = int(2*HALF*PX_PER_H); out_h = int((FAR-NEAR)*PX_PER_H)
    jj, ii = np.meshgrid(np.arange(out_w), np.arange(out_h))
    X = (jj - out_w/2)/PX_PER_H
    Z = FAR - ii/PX_PER_H
    P = np.stack([X, np.ones_like(X), Z], -1)
    cam = P @ R                      # inverse of the forward rotation
    with np.errstate(divide="ignore", invalid="ignore"):
        u = cam[..., 0]/cam[..., 2]*f + W/2
        v = cam[..., 1]/cam[..., 2]*f + H/2
    bad = (cam[..., 2] <= 1e-6) | ~np.isfinite(u) | ~np.isfinite(v)
    u[bad] = -1; v[bad] = -1
    return cv2.remap(im, u.astype(np.float32), v.astype(np.float32),
                     cv2.INTER_LINEAR, borderValue=0)

def measure(stem):
    meta = json.load(open(f"output/api/{stem}.json"))
    im = cv2.imread(f"output/api/{stem}.jpg")
    bev = ipm(im, meta["fov"], meta["pitch"])
    cv2.imwrite(f"output/bev_{stem}.png", bev)
    g = cv2.cvtColor(bev, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    cover = (bev.sum(2) > 0)
    if cover.mean() < 0.35:
        return {"capture": stem, "ok": False,
                "why": f"only {cover.mean()*100:.0f}% of the near field is in frame"}
    paint = ((g - cv2.GaussianBlur(g, (0, 0), 0.30*PX_PER_H)) > 12) & cover
    paint = cv2.morphologyEx(paint.astype(np.uint8), cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(paint, 8)
    if n < 2:
        return {"capture": stem, "ok": False, "why": "no paint in the near field"}

    # every kernel below is a length on the road, not a count of pixels
    MIN_STRIPE = int(0.30*PX_PER_H)          # a stripe is at least 30 cm long
    keep = [i for i in range(1, n)
            if st[i, cv2.CC_STAT_AREA] > (0.10*PX_PER_H)**2]
    if not keep:
        return {"capture": stem, "ok": False, "why": "nothing of marking size"}
    big = max(keep, key=lambda i: st[i, cv2.CC_STAT_AREA])
    ys, xs = np.nonzero(lbl == big)
    p = np.stack([xs, ys], 1).astype(np.float32)
    _, _, v = np.linalg.svd(p - p.mean(0), full_matrices=False)
    band = math.degrees(math.atan2(v[0][1], v[0][0]))

    def se(metres, ang):
        L = max(3, int(metres*PX_PER_H)) | 1
        k = np.zeros((L, L), np.uint8); c = L//2; t = math.radians(ang)
        for s in np.linspace(-L/2, L/2, L*3):
            x, y = int(round(c+s*math.cos(t))), int(round(c+s*math.sin(t)))
            if 0 <= x < L and 0 <= y < L: k[y, x] = 1
        return k
    # §171: the boundary line is continuous, the stripes are 20 cm wide, so a
    # 1.5 m line element along the band survives only on the boundary
    bnd = cv2.morphologyEx(paint, cv2.MORPH_OPEN, se(1.5, band))
    stripes = cv2.morphologyEx(
        cv2.bitwise_and(paint, cv2.bitwise_not(
            cv2.dilate(bnd, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))))),
        cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    ns, ls, ss, _ = cv2.connectedComponentsWithStats(stripes, 8)

    widths, lengths, angs = [], [], []
    for i in range(1, ns):
        if ss[i, cv2.CC_STAT_AREA] < (0.08*PX_PER_H)**2: continue
        yy, xx = np.nonzero(ls == i)
        q = np.stack([xx, yy], 1).astype(np.float32); c = q.mean(0)
        _, _, vv = np.linalg.svd(q - c, full_matrices=False)
        d = vv[0]/np.linalg.norm(vv[0]); nr = np.array([-d[1], d[0]])
        al = (q-c) @ d; ac = (q-c) @ nr
        if al.max()-al.min() < MIN_STRIPE: continue
        widths.append(float(np.percentile(ac, 95) - np.percentile(ac, 5)))
        lengths.append(float(al.max()-al.min()))
        angs.append(math.degrees(math.atan2(d[1], d[0])) % 180)
    if len(widths) < 5:
        return {"capture": stem, "ok": False, "why": f"{len(widths)} stripes"}
    w_h = float(np.median(widths))/PX_PER_H        # in camera heights
    height = STRIPE_W/w_h
    band_m = float(np.median(lengths))/PX_PER_H*height
    z = np.exp(2j*np.radians(np.array(angs)))
    coh = float(abs(z.sum())/len(z))
    rel = abs(((float(np.degrees(np.angle(z.sum())/2)) - band + 90) % 180) - 90)
    return {"capture": stem, "ok": True, "fov": meta["fov"], "pitch": meta["pitch"],
            "stripes": len(widths),
            "stripe_width_px": round(float(np.median(widths)), 1),
            "camera_height_m": round(height, 2),
            "band_width_m": round(band_m, 2),
            "stripe_to_band_deg": round(rel, 1),
            "stripe_angle_coherence": round(coh, 3)}

rows = []
for stem in ["before_close", "before_p-25", "before_p-40", "f40_p-20",
             "f40_p-35", "f60_p-20", "f60_p-35", "f90_p-20", "f90_p-35"]:
    r = measure(stem); rows.append(r)
    if r["ok"]:
        print(f"{r['capture']:14s} fov {r['fov']:>3} pitch {r['pitch']:>4}  "
              f"{r['stripes']:3d} stripes  height {r['camera_height_m']:5.2f} m  "
              f"band {r['band_width_m']:5.2f} m  stripe-to-band "
              f"{r['stripe_to_band_deg']:5.1f} deg (coh {r['stripe_angle_coherence']:.2f})")
    else:
        print(f"{r['capture']:14s} -- {r['why']}")

ok = [r for r in rows if r["ok"]]
if ok:
    h = np.array([r["camera_height_m"] for r in ok])
    b = np.array([r["band_width_m"] for r in ok])
    a = np.array([r["stripe_to_band_deg"] for r in ok])
    print(f"\n{len(ok)} captures, one camera and one chevron")
    print(f"  camera height {h.mean():.2f} m, sd {h.std():.2f}  "
          f"(Street View sits near 2.5 m; this is the check, not an input)")
    print(f"  original band width {b.mean():.2f} m, sd {b.std():.2f}")
    print(f"  stripe to band {a.mean():.1f} deg, sd {a.std():.1f}  "
          f"(§171 says 斜四五度)")
json.dump({"method": "IPM first, morphology in the bird's eye plane; every "
                     "kernel sized in metres", "px_per_camera_height": PX_PER_H,
           "near_far_camera_heights": [NEAR, FAR], "captures": rows},
          open("results/ipm_measure.json", "w"), indent=2, ensure_ascii=False)
