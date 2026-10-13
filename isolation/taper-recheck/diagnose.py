"""Where does taper_427 diverge between encodings of one frame? (2026-09-23)"""
import sys, math, glob, cv2, numpy as np
sys.path.insert(0, "src")
from marking import phone as P
from marking.vanishing import angle_between

FOV = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))


def stages(img, K):
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
    longs = [tuple(map(float, s)) for s in (L.reshape(-1, 4) if L is not None else [])
             if math.hypot(s[2] - s[0], s[3] - s[1]) > 200]
    inhull = [s for s in longs if inside[int((s[1] + s[3]) / 2), int((s[0] + s[2]) / 2)] > 0]
    rest, pens = list(inhull), []
    for _ in range(4):
        if len(rest) < 3: break
        r, inl = P.ransac_vp(rest, 6.0, (0, h * 0.60))
        if r is None: break
        pens.append({"vp": r[0], "segs": inl})
        X = {tuple(s) for s in inl}; rest = [s for s in rest if tuple(s) not in X]
    pens = [p for p in pens if len(p["segs"]) >= 3]
    ang = {}
    for i in range(len(pens)):
        for j in range(i + 1, len(pens)):
            ang[(i, j)] = round(angle_between(K, np.append(pens[i]["vp"], 1), np.append(pens[j]["vp"], 1)), 2)
    return {"otsu": int(lv), "white_px": int((white > 0).sum()), "hull_area": int(st[big, 4]),
            "long": len(longs), "inhull": len(inhull),
            "pencils": [(len(p["segs"]), [int(v) for v in p["vp"]]) for p in pens], "pair_deg": ang}


if __name__ == "__main__":
    f = sys.argv[1]
    im = cv2.imread(f); K = P.K_from_fov(im.shape[1], im.shape[0], FOV)
    for q in [None] + [int(x) for x in sys.argv[2:]]:
        x = im if q is None else cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, q])[1], 1)
        s = stages(x, K)
        print(f"q={q or 'orig'}", s)
