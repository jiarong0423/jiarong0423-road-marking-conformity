"""卡片當尺,驗證新紅線寬是否 10 cm(隔離區草稿,2026-09-23)。
卡片為標準 ID-1(ISO/IEC 7810,85.60 x 53.98 mm),使用者 2026-09-23 確認。卡片與紅線同在地面、同一深度,
沿卡片長邊方向量紅線寬,比值不需相機姿態(局部仿射)。"""
import cv2, numpy as np, json, csv, sys
from pathlib import Path
D = Path("evidence/field-2026-09-23"); rows = {r["no"]: r for r in csv.DictReader(open(D / "MANIFEST.csv"))}
CARD_LONG_MM = 85.60
out = []
for no in sys.argv[1:]:
    im = cv2.imread(str(D / rows[no]["file"])); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    card = (((hsv[..., 0] < 8) | (hsv[..., 0] > 170)) & (hsv[..., 1] > 120) & (hsv[..., 2] < 200)).astype(np.uint8)
    card = cv2.morphologyEx(card, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    card = cv2.morphologyEx(card, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, l, st, _ = cv2.connectedComponentsWithStats(card, 8); i = 1 + int(np.argmax(st[1:, 4]))
    cnt, _ = cv2.findContours((l == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    (cx, cy), (a, b), ang = cv2.minAreaRect(max(cnt, key=cv2.contourArea))
    long_px = max(a, b); th = np.deg2rad(ang if a >= b else ang + 90)
    u = np.array([np.cos(th), np.sin(th)]); v = np.array([-u[1], u[0]])        # u 沿卡片長邊, v 垂直
    short_px = min(a, b)
    lab_a = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 1].astype(int); med = int(np.median(lab_a))
    paint = ((lab_a - med) > 10) & ~(l == i)
    widths = []
    for off in list(range(-6, -1)) + list(range(2, 7)):                        # 卡片外、沿 v 方向上下各幾排
        c = np.array([cx, cy]) + v * off * short_px / 3.0
        ts = np.arange(-2.0 * long_px, 2.0 * long_px)
        P = (c[None] + ts[:, None] * u[None]).astype(int)
        okp = (P[:, 0] >= 0) & (P[:, 0] < im.shape[1]) & (P[:, 1] >= 0) & (P[:, 1] < im.shape[0])
        val = np.zeros(len(ts), bool); val[okp] = paint[P[okp, 1], P[okp, 0]]
        val = cv2.morphologyEx(val.astype(np.uint8)[:, None], cv2.MORPH_CLOSE, np.ones((9, 1), np.uint8)).ravel() > 0
        idx = np.nonzero(val)[0]
        if not len(idx): continue
        runs = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
        r = min(runs, key=lambda r: abs((r[0] + r[-1]) / 2 - len(ts) / 2))        # 最接近卡片中心的一段
        widths.append(int(r[-1] - r[0] + 1))
    w_mm = [round(w / long_px * CARD_LONG_MM, 1) for w in widths]
    res = {"frame": no, "card_long_px": round(long_px, 1), "card_short_px": round(short_px, 1),
           "line_width_px": widths, "line_width_mm": w_mm,
           "median_mm": None if not w_mm else float(np.median(w_mm))}
    out.append(res); print(res)
Path("isolation/field-2026-09-23/card_vs_redline.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
