"""The taper's chord, measured across a run of panoramas instead of inside one.

No single photograph of this site holds both ends of the transition, and the
orthophoto predates the marking entirely - PHOTO2025 shows plain dashed lane
lines where the chevron now is. So the end-to-end quantity the regulation
defines cannot come from one frame.

Eight 2025-06 panoramas lie along 84 m of this road. Each is requested at
the road's own bearing, so in the bird's eye plane the road runs straight up
the image and a lateral offset is read directly. The panorama coordinates
give the longitudinal spacing in metres. Offset against distance across the
eight is the chord.

Scale comes from §182: a lane dash is 4 m of paint and 6 m of gap, a 10 m
repeat, measured over several periods in a road-aligned frame. That is a
long baseline near the camera, which is what every earlier scale attempt
lacked - the arm width was 20 cm and moved with the source blur, the red
line was 10 cm and sat in the middle distance.

The camera height it implies is printed. Street View sits near 2.5 m, and a
figure far from that means the dashes were not what was measured.
"""
import glob, json, math, os, sys
import cv2
import numpy as np

sys.path.insert(0, "src")
from marking.rectify import focal_px          # noqa: E402

PX = 300.0            # bird's eye pixels per camera height
NEAR, FAR = 0.5, 6.0
HALF = 4.5            # wider than the gate's: the road is wider than a lane
DASH_LEN = 4.0        # m, §182: the painted segment of a lane dash
# The 10 m repeat was tried first and cannot be seen here: the bird's eye
# range is 5.5 camera heights, under 14 m, so one period barely fits and no
# spacing can be measured from it. The segment itself does fit, and 4 m is
# long enough that the edge blur which ruined the 20 cm arm width and the
# 10 cm red line does not matter.
ROAD = 141.6


def birdseye(im, fov, pitch):
    h, w = im.shape[:2]
    f = focal_px(fov, w)
    t = math.radians(pitch)
    R = np.array([[1, 0, 0], [0, math.cos(t), -math.sin(t)],
                  [0, math.sin(t), math.cos(t)]])
    ow, oh = int(2*HALF*PX), int((FAR-NEAR)*PX)
    jj, ii = np.meshgrid(np.arange(ow), np.arange(oh))
    g = np.stack([(jj-ow/2)/PX, np.ones_like(jj, float), FAR - ii/PX], -1)
    cam = g @ R
    with np.errstate(divide="ignore", invalid="ignore"):
        u = cam[..., 0]/cam[..., 2]*f + w/2
        v = cam[..., 1]/cam[..., 2]*f + h/2
    bad = (cam[..., 2] <= 1e-6) | ~np.isfinite(u) | ~np.isfinite(v)
    u[bad] = -1; v[bad] = -1
    return cv2.remap(im, u.astype(np.float32), v.astype(np.float32),
                     cv2.INTER_LINEAR, borderValue=0)


def paint_of(bev):
    L = cv2.cvtColor(bev, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    cover = bev.sum(2) > 0
    m = (((L - cv2.GaussianBlur(L, (0, 0), 0.30*PX)) > 12) & cover).astype(np.uint8)*255
    return cv2.morphologyEx(m, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))), cover


def dash_scale(paint, cover):
    """Camera height from the lane dash's own length, §182's 4 m."""
    # A dash clipped by the edge of the mapped ground measures short, and
    # short reads as a tall camera: the first pass implied 3.25-4.93 m for a
    # car that sits near 2.5. Only dashes lying wholly inside the covered
    # region, with clear ground beyond both ends, are counted.
    inside = cv2.erode(cover.astype(np.uint8),
                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)),
                       iterations=3)
    n, lbl, st, cen = cv2.connectedComponentsWithStats(paint, 8)
    runs = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 150:
            continue
        ys, xs = np.nonzero(lbl == i)
        if not inside[ys, xs].all():
            continue
        p = np.stack([xs, ys], 1).astype(np.float32); c = p.mean(0)
        _, _, v = np.linalg.svd(p - c, full_matrices=False)
        d = v[0]/np.linalg.norm(v[0])
        # a dash runs up the image: the road is vertical in this frame
        if abs(d[1]) < 0.93:
            continue
        pr = (p - c) @ d
        length = float(pr.max() - pr.min())
        thick = float(np.abs((p - c) @ np.array([-d[1], d[0]])).max()*2)
        if length < 0.3*PX or thick < 2 or not (3 < length/thick < 30):
            continue
        runs.append((c[0], c[1], length))
    if len(runs) < 3:
        return None, len(runs), None
    # a whole dash, not a fragment: keep those long enough to be one and
    # short enough not to be a continuous line
    lens = np.array([r[2] for r in runs])/PX          # camera heights
    whole = lens[(lens > 0.6) & (lens < 3.0)]
    if len(whole) < 3:
        return None, len(runs), None
    med = float(np.median(whole))
    return DASH_LEN/med, len(runs), round(med, 3)


rows = []
for f in sorted(glob.glob("output/seq/*.jpg"),
                key=lambda p: float(os.path.basename(p)[:-4])):
    meta = json.load(open(f.replace(".jpg", ".json")))
    bev = birdseye(cv2.imread(f), meta["fov"], meta["pitch"])
    cv2.imwrite(f.replace(".jpg", "_wide.png"), bev)
    paint, cover = paint_of(bev)
    height, ndash, med = dash_scale(paint, cover)
    rows.append({"along_m": meta["along_m"], "pano": meta["pano"],
                 "dash_candidates": ndash, "dash_len_camera_heights": med,
                 "camera_height_m": None if height is None else round(height, 2)})
    h = "-" if height is None else f"{height:5.2f}"
    print(f"  {meta['along_m']:>7.1f} m  {ndash:3d} dash-shaped  "
          f"len {('-' if med is None else f'{med:.3f}'):>6} camera heights  "
          f"height {h}")

hs = [r["camera_height_m"] for r in rows if r["camera_height_m"]]
if hs:
    a = np.array(hs)
    ok = a[(a > 1.5) & (a < 4.0)]
    print(f"\n{len(hs)} frames give a height: "
          f"{' '.join(f'{x:.2f}' for x in a)}")
    if len(ok):
        print(f"  within 1.5-4.0 m: {len(ok)} of {len(a)}, "
              f"mean {ok.mean():.2f}, sd {ok.std():.2f}")
    else:
        print("  none plausible for a Street View camera")
json.dump(rows, open("results/chord_sequence.json", "w"), indent=2)
