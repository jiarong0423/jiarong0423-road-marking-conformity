import sys, math, glob, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
import cv2, numpy as np
from marking.extract import markings, road_region
from marking.sequential import taper_with_hatching
from PIL import Image
from PIL.ExifTags import TAGS

def fov_of(path, w, h):
    """scripts/assess_field.py:86 的同一條式子。無 EXIF 焦距就拒答。"""
    d = {TAGS.get(k, k): v for k, v in (Image.open(path)._getexif() or {}).items()}
    f35 = d.get("FocalLengthIn35mmFilm")
    if not f35:
        return None
    return math.degrees(2*math.atan(w/(2*(f35*math.hypot(w, h)/43.267))))

FRAMES = sorted(glob.glob(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "evidence/field-2026-09-20/IMG_*.jpg")))
W = 640          # Street View的尺度;fov 逐張從 EXIF 取,不給預設

def otsu_mask(bgr):
    h = bgr.shape[0]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    m = cv2.inRange(hsv, (0, 0, int(lv)), (180, 60, 255))
    m[:int(h*0.34), :] = 0
    m[int(h*0.96):, :] = 0
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))

def hough(mask, res, thr, minlen):
    L = cv2.HoughLinesP(cv2.Canny(mask, 50, 150), 1, res, thr,
                        minLineLength=minlen, maxLineGap=6)
    return [] if L is None else [tuple(map(float,s)) for s in L.reshape(-1,4)]

RUNS = (("現行參數",   markings,  np.pi/720,  40, 25),
        ("Otsu+現行",  otsu_mask, np.pi/720,  40, 25),
        ("dlD+槽化線", markings,  np.pi/1440, 30, 25),
        ("Otsu+槽化線",otsu_mask, np.pi/1440, 30, 25))

tot = {r[0]: [0,0,0,[]] for r in RUNS}
t0 = time.time()
print("frame " + " ".join(f"{n:>20}" for n,*_ in RUNS), flush=True)
for p in FRAMES:
    name = "F%02d" % (FRAMES.index(p)+1)
    big = cv2.imread(p)
    img = cv2.resize(big, (W, int(round(W*big.shape[0]/big.shape[1]))),
                     interpolation=cv2.INTER_AREA)
    FOV = fov_of(p, big.shape[1], big.shape[0])
    if FOV is None:
        print(f"{name:5} EXIF 無焦距,拒答"); continue
    roi = road_region(img)
    cells = []
    for label, mkf, res, thr, ml in RUNS:
        mk = mkf(img, min_response=8.0)[0] if mkf is markings else mkf(img)
        if roi is not None:
            mk = cv2.bitwise_and(mk, roi)
        sg = hough(mk, res, thr, ml)
        t = (taper_with_hatching(sg, FOV, img.shape[1], img.shape[0])
             if len(sg) >= 6 else {"ok": False})
        cands = t.get("candidates") or []
        bord = sum(1 for c in cands if c.get("borders"))
        tot[label][0]+=len(sg); tot[label][1]+=len(cands); tot[label][2]+=bord
        if t.get("ok"): tot[label][3].append((name, round(t["taper_deg"],1)))
        cells.append(f"{len(sg):3d}段{len(cands):2d}候{bord:2d}鄰"
                     + (f"{t['taper_deg']:6.1f}°" if t.get("ok") else "    --"))
    print(f"{name:5} " + " ".join(f"{c:>20}" for c in cells), flush=True)

k=len(FRAMES); print(f"\n{int(time.time()-t0)} 秒 / {k} 張", flush=True)
for label,*_ in RUNS:
    s,c,b,ok = tot[label]
    print(f"{label:12} 平均段數 {s/k:6.1f} 候選 {c:4d} 有鄰接斜紋 {b:4d} "
          f"成立 {len(ok):2d}/{k} {ok}", flush=True)
