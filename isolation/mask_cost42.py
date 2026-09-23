import sys, math, glob, os, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
import cv2, numpy as np
from marking.extract import markings, road_region
from marking import situation as S

FRAMES = sorted(glob.glob(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "evidence/field-2026-09-20/IMG_*.jpg")))

def otsu_mask(bgr):
    """scripts/measure_chevron.py lines 49-65, verbatim in behaviour."""
    h = bgr.shape[0]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    level, _ = cv2.threshold(hsv[:, :, 2], 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = cv2.inRange(hsv, (0, 0, int(level)), (180, 60, 255))
    m[:int(h*0.34), :] = 0
    m[int(h*0.96):, :] = 0
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

def segs_from(mask, roi, shape):
    if roi is not None:
        mask = cv2.bitwise_and(mask, roi)
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/720, 40,
                            minLineLength=max(25, shape[1]//25), maxLineGap=6)
    if lines is None:
        return []
    return [tuple(map(float, s)) for s in lines.reshape(-1, 4)]

print(f"{'frame':6} {'遮罩覆蓋%':>12} {'段數':>6} {'§167':>6}   |  "
      f"{'遮罩覆蓋%':>12} {'段數':>6} {'§167':>6}")
tot = {"cur": [0,0,[]], "ots": [0,0,[]]}
t0 = time.time()
for p in FRAMES:
    name = "F%02d" % (FRAMES.index(p)+1)
    img = cv2.imread(p)
    roi = road_region(img)
    n = img.shape[0]*img.shape[1]
    row = []
    for key, mk in (("cur", markings(img, min_response=8.0)[0]),
                    ("ots", otsu_mask(img))):
        cov = 100.0*int((mk > 0).sum())/n
        sg = segs_from(mk, roi, img.shape)
        try:
            dw = S._double_white(sg, img, roi)
        except Exception as e:
            dw = "ERR:%s" % type(e).__name__
        hit = "成立" if dw and dw != "" and not isinstance(dw, str) else ("無" if not dw else dw)
        tot[key][0] += cov; tot[key][1] += len(sg)
        if hit == "成立": tot[key][2].append(name)
        row += [cov, len(sg), hit]
    print(f"{name:6} {row[0]:11.1f}% {row[1]:6d} {row[2]:>6}   |  "
          f"{row[3]:11.1f}% {row[4]:6d} {row[5]:>6}", flush=True)

k = len(FRAMES)
print(f"\n{int(time.time()-t0)} 秒 / {k} 張")
for key, label in (("cur","dark_light_dark(現行)"), ("ots","Otsu(螢光綠)")):
    c, s, hits = tot[key]
    print(f"{label:24} 平均遮罩覆蓋 {c/k:5.1f}%  平均段數 {s/k:6.1f}  "
          f"§167 成立 {len(hits)}/{k} {hits}")
