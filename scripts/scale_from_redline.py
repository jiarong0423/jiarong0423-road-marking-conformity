"""Camera height from the kerbside red line, which the rules give a width.

Three measurements in this session failed for want of a known length near
the camera. §169 supplies one: 禁止臨時停車線 is a red solid line 10 cm wide,
set within 30 cm of the pavement edge. It runs down the right of the 2025-06
capture, in the foreground, which is exactly where the lane dashes are not.

Width, not length, is the quantity used. A line's length along the road is
foreshortened by the pitch and needs both endpoints to project; its width
across the road is short enough that the ground patch under it is locally
flat, so one perpendicular cut gives the scale where it is cut.

The check is the number that comes out: Street View cameras sit near 2.5 m.
"""
import sys, json, math
import cv2, numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image   # noqa: E402

STEM = sys.argv[1] if len(sys.argv) > 1 else "before_p-25"
RED_W = 0.10          # m, 道路交通標誌標線號誌設置規則 §169
meta = json.load(open(f"output/api/{STEM}.json"))
im = cv2.imread(f"output/api/{STEM}.jpg"); H, W = im.shape[:2]
fov, pitch = meta["fov"], meta["pitch"]
print(f"{STEM}: fov {fov}, pitch {pitch}, {W}x{H}")

hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.int16)
b, g, r = cv2.split(im.astype(np.int16))
# road red paint is weakly saturated and dusty; ask for red-dominance rather
# than a vivid hue, or the whole line is missed
redness = r - (g + b)//2
mask = ((redness > 18) & (r > 60)).astype(np.uint8)*255
mask[:int(H*0.42)] = 0
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
n, lbl, st, _ = cv2.connectedComponentsWithStats(mask, 8)
print(f"{n-1} red components, largest "
      f"{max([st[i, cv2.CC_STAT_AREA] for i in range(1, n)], default=0)} px")
if n < 2:
    sys.exit("no red paint found")
i = max(range(1, n), key=lambda j: st[j, cv2.CC_STAT_AREA])
ys, xs = np.nonzero(lbl == i)
p = np.stack([xs, ys], 1).astype(np.float32); c = p.mean(0)
_, _, v = np.linalg.svd(p - c, full_matrices=False)
d = v[0]/np.linalg.norm(v[0]); q = np.array([-d[1], d[0]])
along = (p - c) @ d; across = (p - c) @ q
print(f"red line runs {along.max()-along.min():.0f} px, "
      f"bearing {math.degrees(math.atan2(d[1], d[0])) % 180:.1f} deg")

# cut it at stations along its length; at each, the width is the extent across
heights, rows = [], []
for t in np.linspace(along.min()+8, along.max()-8, 24):
    sel = np.abs(along - t) < 4
    if sel.sum() < 12:
        continue
    lo, hi = across[sel].min(), across[sel].max()
    mid = c + d*t
    a_pt, b_pt = mid + q*lo, mid + q*hi
    gp = ground_from_image([a_pt, b_pt], fov, pitch, (W, H))
    if not np.isfinite(gp).all():
        continue
    wid_h = float(np.linalg.norm(gp[1]-gp[0]))     # in camera heights
    if wid_h <= 0:
        continue
    h_m = RED_W/wid_h
    heights.append(h_m)
    rows.append({"station_px": round(float(t), 1),
                 "width_px": round(float(hi-lo), 1),
                 "width_camera_heights": round(wid_h, 5),
                 "implied_height_m": round(h_m, 2)})
if not heights:
    sys.exit("no station projected onto the ground")
hh = np.array(heights)
med, mad = np.median(hh), np.median(np.abs(hh - np.median(hh)))
keep = np.abs(hh - med) < 3*1.4826*max(mad, 1e-6)
print(f"\n{len(hh)} cuts, {int(keep.sum())} within 3 robust sigma")
print(f"{'station':>9}{'width px':>10}{'implied height m':>19}")
for rr, k in zip(rows, keep):
    print(f"{rr['station_px']:>9.0f}{rr['width_px']:>10.1f}"
          f"{rr['implied_height_m']:>19.2f}{'' if k else '   (outlier)'}")
h = float(np.median(hh[keep]))
print(f"\ncamera height {h:.2f} m, sd {hh[keep].std():.2f}")
if 1.8 < h < 3.4:
    print("  consistent with a Street View camera - the scale is usable")
else:
    print("  NOT a Street View camera height. Either the red component is not "
          "the §169 line, or it is partly occluded. The scale is refused.")
json.dump({"capture": STEM, "fov": fov, "pitch": pitch,
           "red_line_width_m": RED_W, "source": "設置規則 §169",
           "camera_height_m": round(h, 2),
           "camera_height_sd_m": round(float(hh[keep].std()), 2),
           "cuts": rows, "usable": bool(1.8 < h < 3.4)},
          open("results/scale_redline.json", "w"), indent=2, ensure_ascii=False)
