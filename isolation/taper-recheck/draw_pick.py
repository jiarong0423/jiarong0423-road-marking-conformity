"""Draw which two pencils taper_427 picks on F40 under three encodings."""
import sys, math, glob, cv2, numpy as np
sys.path.insert(0, "src")
from marking import phone as P
from marking.vanishing import angle_between
FOV = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))
OUT = sys.argv[1]


def picks(img, K):
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white = cv2.inRange(hsv, (0, 0, int(lv)), (180, 60, 255)); white[:int(h * 0.38)] = 0
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dens = cv2.blur((white > 0).astype(np.float32), (121, 121))
    n, lbl, st, _ = cv2.connectedComponentsWithStats((dens > 0.12).astype(np.uint8), 8)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    inside = cv2.dilate((lbl == big).astype(np.uint8), np.ones((61, 61), np.uint8))
    e = cv2.Canny(white, 50, 150)
    L = cv2.HoughLinesP(e, 1, np.pi / 1440, 50, minLineLength=200, maxLineGap=12)
    longs = [tuple(map(float, s)) for s in L.reshape(-1, 4) if math.hypot(s[2] - s[0], s[3] - s[1]) > 200]
    inhull = [s for s in longs if inside[int((s[1] + s[3]) / 2), int((s[0] + s[2]) / 2)] > 0]
    rest, pens = list(inhull), []
    for _ in range(4):
        if len(rest) < 3: break
        r, inl = P.ransac_vp(rest, 6.0, (0, h * 0.60))
        if r is None: break
        pens.append({"vp": r[0], "segs": inl})
        X = {tuple(s) for s in inl}; rest = [s for s in rest if tuple(s) not in X]
    pens = [p for p in pens if len(p["segs"]) >= 3]
    return inhull, pens, (lbl == big)


f = sorted(glob.glob("evidence/field-2026-09-20/IMG_*.jpg"))[39]
im = cv2.imread(f)
panels = []
for label, x, d in [("original 11.9:1", im, 0),
                    ("q97 re-save 23.2:1", cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 97])[1], 1), 0),
                    ("crop 8px 5.0:1", im[8:, 8:], 8)]:
    K = P.K_from_fov(im.shape[1], im.shape[0], FOV); K[0, 2] -= d; K[1, 2] -= d
    inhull, pens, region = picks(x, K)
    v = x.copy()
    cnt, _ = cv2.findContours(region.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(v, cnt, -1, (255, 255, 0), 6)
    for s in inhull:
        cv2.line(v, (int(s[0]), int(s[1])), (int(s[2]), int(s[3])), (160, 160, 160), 5)
    for p, col in zip(pens[:2], [(0, 0, 255), (0, 200, 0)]):
        for s in p["segs"]:
            cv2.line(v, (int(s[0]), int(s[1])), (int(s[2]), int(s[3])), col, 14)
    ang = angle_between(K, np.append(pens[0]["vp"], 1), np.append(pens[1]["vp"], 1))
    y0 = int(x.shape[0] * 0.38)
    crop = v[y0:, :]
    crop = cv2.resize(crop, (900, int(crop.shape[0] * 900 / crop.shape[1])))
    cv2.rectangle(crop, (0, 0), (900, 60), (0, 0, 0), -1)
    cv2.putText(crop, f"{label}  picked {ang:.2f} deg  red={len(pens[0]['segs'])} green={len(pens[1]['segs'])}",
                (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    panels.append(crop)
hmin = min(p.shape[0] for p in panels)
cv2.imwrite(OUT, np.hstack([p[:hmin] for p in panels]))
print("wrote", OUT)
