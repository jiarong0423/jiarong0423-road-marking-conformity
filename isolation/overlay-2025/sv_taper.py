"""Pre-erasure taper measured directly on 2025-06 Street View frames (isolation, 2026-09-23).

Same recognizers as F40 (outermost paint + EDLines must agree; horizon from the
vertical vanishing point; edge A must meet the horizon at the road's VP).
Street View frames are 640 px; they are upscaled to 3072 so the pixel-tuned
parameters mean the same thing. K from the request's fov. Extra check the
phone never had: the request's pitch predicts the horizon row (roll ~ 0).
"""
import sys, math, json, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from marking import phone as P
import horizon2 as H2
import edge_extremes as EX


def paint_region(img):
    """Street View is bright: Otsu on V takes the pavement concrete as white.
    Paint by local contrast instead (brighter than its surroundings, colourless)."""
    h, w = img.shape[:2]
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    res = L - cv2.GaussianBlur(L, (0, 0), 70)
    sat = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 1]
    white = (res > 18) & (sat < 60) & (L > 150); white[:int(h * 0.30)] = False
    white = cv2.morphologyEx(white.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)) > 0
    dens = cv2.blur(white.astype(np.float32), (121, 121))
    n, lbl, st, _ = cv2.connectedComponentsWithStats((dens > 0.12).astype(np.uint8), 8)
    if n < 2: return None, None
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return white, lbl == big


EX.chevron_region = paint_region; H2.chevron_region = paint_region
import consensus as C
_ed = C.edlines


def edlines_native(gray, minlen=120):
    """Upscaling blurs 1 native px into ~5; EDLines runs at the native 640 and is scaled back."""
    f = gray.shape[1] / 640.0
    small = cv2.resize(gray, (640, int(round(gray.shape[0] / f))), interpolation=cv2.INTER_AREA)
    return [tuple(v * f for v in s) for s in _ed(small, max(20, int(minlen / f)))]


C.edlines = edlines_native

FRAMES = [("e3 CLY3P h128 p-18 f65", "output/epochs/e3_2025-06.jpg", 65, -18),
          ("seq +35.5 h141.6 p-25 f90", "output/seq/+0035.5.jpg", 90, -25),
          ("seq +45.4 h141.6 p-25 f90", "output/seq/+0045.4.jpg", 90, -25)]
UP = 3072


def horizon_row_from_pitch(K, pitch_deg):
    return K[1, 2] - K[1, 1] * math.tan(math.radians(-pitch_deg))


def one(img, fov, pitch):
    K = P.K_from_fov(img.shape[1], img.shape[0], fov)
    r = H2.run(img, K)
    r["horizon_row_from_pitch"] = round(horizon_row_from_pitch(K, pitch), 1)
    return r, K


if __name__ == "__main__":
    out = {}
    for name, f, fov, pitch in FRAMES:
        im = cv2.resize(cv2.imread(f), (UP, UP), interpolation=cv2.INTER_CUBIC)
        rows = []
        for vn, x in [("orig", im), ("q97", cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 97])[1], 1)),
                      ("q91", cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 91])[1], 1)),
                      ("crop24", im[24:, 24:])]:
            if vn == "crop24":
                K = P.K_from_fov(UP, UP, fov); K[0, 2] -= 24; K[1, 2] -= 24; r = H2.run(x, K)
            else:
                r, K = one(x, fov, pitch)
            rows.append((vn, r))
            print(name, vn, "OK" if r.get("ok") else "--", r.get("taper_ratio"), r.get("taper_deg"),
                  "A-vs-road", r.get("edgeA_vs_road_deg"), r.get("why", ""), flush=True)
        out[name] = {vn: {k: v for k, v in r.items() if k != "vert"} for vn, r in rows}
    json.dump(out, open(__import__("os").makedirs("output/overlay-2025", exist_ok=True) or "output/overlay-2025/sv_taper.json", "w"), indent=1, default=float)
