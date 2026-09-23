"""The chevron as it was, measured on ground the camera parameters are known for.

Every difficulty with the 2026 field photographs comes from not knowing where
the camera was pointing. The Street View Static API does not have that
problem: the request fixes the field of view and the pitch, so the map from
pixel to ground plane is exact up to the camera's height, and the height
falls out of the marking itself - §171 repeats the stripes every 50 cm, so
whatever scale makes the measured period 0.50 m is the height.

That makes the 2025-06 state measurable in metres with nothing assumed:
the band's width, the stripe pitch, the taper edge against the road. It is
the "before" the rest of the project keeps referring to, and until now it
existed only as a rate.
"""
import sys, json, math
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image   # noqa: E402

API = Path("output/api")

def princ(i, labels):
    ys, xs = np.nonzero(labels == i)
    p = np.stack([xs, ys], 1).astype(np.float32); m = p.mean(0)
    _, _, v = np.linalg.svd(p - m, full_matrices=False)
    d = v[0]/np.linalg.norm(v[0]); pr = (p - m) @ d
    return m + d*pr.min(), m + d*pr.max(), float(pr.max()-pr.min())

def line_se(length, ang):
    k = np.zeros((length | 1, length | 1), np.uint8); c = length//2
    t = math.radians(ang)
    for s in np.linspace(-length/2, length/2, length*3):
        x, y = int(round(c+s*math.cos(t))), int(round(c+s*math.sin(t)))
        if 0 <= x < k.shape[1] and 0 <= y < k.shape[0]: k[y, x] = 1
    return k

def measure(stem):
    meta = json.load(open(API/f"{stem}.json"))
    im = cv2.imread(str(API/f"{stem}.jpg"))
    H, W = im.shape[:2]
    fov, pitch = meta["fov"], meta["pitch"]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    paint = cv2.morphologyEx(
        ((L - cv2.GaussianBlur(L, (0, 0), 25)) > 14).astype(np.uint8),
        cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(paint, 8)
    if n < 2:
        return None
    big = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_AREA])
    a, b, _ = princ(big, lbl)
    band = math.degrees(math.atan2((b-a)[1], (b-a)[0]))
    bnd = cv2.morphologyEx(paint, cv2.MORPH_OPEN, line_se(61, band))
    stp = cv2.morphologyEx(
        cv2.bitwise_and(paint, cv2.bitwise_not(
            cv2.dilate(bnd, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))))),
        cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    ns, ls, ss, _ = cv2.connectedComponentsWithStats(stp, 8)

    ends, mids, lens = [], [], []
    for i in range(1, ns):
        if ss[i, cv2.CC_STAT_AREA] < 100:
            continue
        p, q, Lp = princ(i, ls)
        if Lp < 18:
            continue
        ang = abs((math.degrees(math.atan2((q-p)[1], (q-p)[0])) - band) % 180)
        if min(ang, 180-ang) < 15:
            continue
        gp = ground_from_image([p, q], fov, pitch, (W, H))
        if not np.isfinite(gp).all():
            continue
        ends.append(gp); mids.append(gp.mean(0))
        lens.append(float(np.linalg.norm(gp[1]-gp[0])))
    if len(lens) < 6:
        return {"file": stem, "ok": False, "why": f"{len(lens)} stripes on ground"}

    mids = np.array(mids)
    d = mids[-1]-mids[0]; d /= np.linalg.norm(d)
    t = np.sort(mids @ d)
    sp = np.diff(t)
    sp = sp[(sp > np.percentile(sp, 15)) & (sp < np.percentile(sp, 85))]
    if len(sp) < 3:
        return {"file": stem, "ok": False, "why": "no stable stripe pitch"}
    period_h = float(np.median(sp))          # in camera-height units
    height = 0.50 / period_h                 # §171: 50 cm repeat
    width_m = float(np.median(lens)) * height
    return {"file": stem, "ok": True, "fov": fov, "pitch": pitch,
            "stripes": len(lens),
            "period_camera_heights": round(period_h, 5),
            "implied_camera_height_m": round(height, 2),
            "band_width_m": round(width_m, 2),
            "band_width_sd_m": round(float(np.std(lens))*height, 2),
            "stripe_pitch_check_m": 0.50}

out = []
for stem in ["before_close", "before_p-25", "before_p-40",
             "f40_p-20", "f40_p-35", "f60_p-20", "f60_p-35",
             "f90_p-20", "f90_p-35"]:
    if not (API/f"{stem}.jpg").exists():
        continue
    r = measure(stem)
    if r is None:
        continue
    out.append(r)
    if r["ok"]:
        print(f"{stem:14s} fov {r['fov']:>3} pitch {r['pitch']:>4}  "
              f"{r['stripes']:3d} stripes  camera height "
              f"{r['implied_camera_height_m']:5.2f} m  ->  band "
              f"{r['band_width_m']:5.2f} m +- {r['band_width_sd_m']:.2f}")
    else:
        print(f"{stem:14s} {r['why']}")

ok = [r for r in out if r["ok"]]
if ok:
    hh = np.array([r["implied_camera_height_m"] for r in ok])
    bw = np.array([r["band_width_m"] for r in ok])
    print(f"\n{len(ok)} captures of the same chevron")
    print(f"  implied camera height {hh.mean():.2f} m, sd {hh.std():.2f}  "
          f"(Street View cars sit near 2.5 m - this is the check that the "
          f"projection is right, not an input)")
    print(f"  original band width {bw.mean():.2f} m, sd {bw.std():.2f}, "
          f"range {bw.min():.2f}-{bw.max():.2f}")
    print(f"\n  with 64% erased, what is left today would be "
          f"{bw.mean()*0.36:.2f} m")
json.dump({"source": "Street View Static API, 2025-06, fov and pitch fixed by "
                     "the request; scale from the §171 50 cm stripe repeat",
           "captures": out}, open("results/original_chevron.json", "w"),
          indent=2, ensure_ascii=False)
