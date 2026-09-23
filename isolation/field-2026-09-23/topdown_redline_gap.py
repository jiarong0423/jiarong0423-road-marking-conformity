"""俯拍版紅線外移(隔離區草稿,2026-09-23)。
新紅線(溝帶上,飽和)內緣 → 舊紅線(柏油上,淡粉)中心的距離,尺 = 新紅線線寬 10 cm(§169)。
俯拍近似正射:以溝蓋上/下邊長比檢查傾斜;比值偏離 1 超過 5% 就拒答。"""
import sys, json, math, hashlib, csv
import cv2, numpy as np
from pathlib import Path
D = Path("evidence/field-2026-09-23")
rows = {r["no"]: r for r in csv.DictReader(open(D / "MANIFEST.csv"))}

def masks(bgr):
    # 清晨光偏暖,HSV 飽和度抓不到粉色漆;改用 LAB a*(相對全圖中位數)
    a = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[..., 1].astype(np.int16)
    med = int(np.median(a))
    strong = ((a - med) > 12).astype(np.uint8) * 255
    faint = ((a - med) > 6).astype(np.uint8) * 255
    strong = cv2.morphologyEx(strong, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    strong = cv2.morphologyEx(strong, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    faint = cv2.morphologyEx(faint, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    return strong, faint

def grate_box(gray):
    # 格柵 = 暗色格縫的包絡:暗像素閉運算後,取面積最大、長寬比近 1、且不碰影像邊的區塊
    h, w = gray.shape
    dark = (gray < np.percentile(gray, 12)).astype(np.uint8) * 255
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((61, 61), np.uint8))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(dark, 8)
    ok = [i for i in range(1, n) if 0.5 < st[i, 2] / max(st[i, 3], 1) < 2.0
          and st[i, 0] > 5 and st[i, 1] > 5 and st[i, 0] + st[i, 2] < w - 5 and st[i, 1] + st[i, 3] < h - 5]
    if not ok:
        return None
    best = max(ok, key=lambda i: st[i, cv2.CC_STAT_AREA])
    cnt, _ = cv2.findContours((lbl == best).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnt, key=cv2.contourArea)
    return cv2.boxPoints(cv2.minAreaRect(c)), cv2.approxPolyDP(cv2.convexHull(c), 0.03 * cv2.arcLength(c, True), True).reshape(-1, 2).astype(float)

def keystone_of(quad):
    # 四邊形 → 上邊/下邊長,左邊/右邊長
    if quad is None or len(quad) != 4:
        return None
    c = quad.mean(0); ang = np.arctan2(quad[:, 1] - c[1], quad[:, 0] - c[0]); q = quad[np.argsort(ang)]
    # 順序:左上附近開始的環;找 y 最小兩點為上邊
    idx = np.argsort(quad[:, 1]); top = quad[idx[:2]]; bot = quad[idx[2:]]
    tl, tr = sorted(top, key=lambda p: p[0]); bl, br = sorted(bot, key=lambda p: p[0])
    return {"top_px": float(np.linalg.norm(tr - tl)), "bottom_px": float(np.linalg.norm(br - bl)),
            "left_px": float(np.linalg.norm(bl - tl)), "right_px": float(np.linalg.norm(br - tr))}

def run(no):
    p = D / rows[no]["file"]; img = cv2.imread(str(p)); h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    strong, faint = masks(img)
    n, lbl, st, cen = cv2.connectedComponentsWithStats(strong, 8)
    comps = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 20000 and st[i, 0] > w * 0.3]
    if len(comps) < 2:
        return {"frame": no, "ok": False, "why": "新紅線色塊不足兩塊,定不出軸向"}
    pts = np.array([cen[i] for i in comps])
    vx, vy, x0, y0 = cv2.fitLine(pts.astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    if vy < 0: vx, vy = -vx, -vy                   # fitLine 方向不定,統一朝下
    tilt = math.degrees(math.atan2(vx, vy))            # 軸相對垂直的角度
    M = cv2.getRotationMatrix2D((float(x0), float(y0)), -tilt, 1.0)
    rs, rf = (cv2.warpAffine(m, M, (w, h), flags=cv2.INTER_NEAREST) for m in (strong, faint))
    gb = grate_box(gray)
    ks = keystone_of(gb[1]) if gb is not None else None
    keystone = None if ks is None else ks["bottom_px"] / ks["top_px"]
    xc = int(x0)
    stations = []
    for y in range(0, h, 40):
        row_s = rs[y]; row_f = rf[y]
        xs = np.nonzero(row_s[max(0, xc - 400):min(w, xc + 400)])[0]
        if len(xs) < 20: continue
        xs = xs + max(0, xc - 400)
        # 最長連續段
        runs = np.split(xs, np.nonzero(np.diff(xs) > 3)[0] + 1); r = max(runs, key=len)
        left, right = r[0], r[-1]; width = right - left
        if not 120 <= width <= 450: continue
        xf = np.nonzero(row_f[:max(0, left - 600)])[0]
        if len(xf) < 15: continue
        fr = np.split(xf, np.nonzero(np.diff(xf) > 3)[0] + 1); fr = [f for f in fr if 15 <= len(f) <= 450]
        if not fr: continue
        f = max(fr, key=lambda a: a[-1])                # 最靠近新線的舊線段
        gap_px = left - (f[0] + f[-1]) / 2
        stations.append({"y": y, "ruler_px": int(width), "gap_px": round(float(gap_px), 1),
                         "gap_m": round(float(gap_px / width * 0.10), 3)})
    g = [s["gap_m"] for s in stations]
    return {"frame": no, "file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "ok": len(g) >= 5 and keystone is not None and 0.95 <= keystone <= 1.05, "grate_quad_px": ks, "axis_tilt_deg": round(tilt, 2),
            "grate_keystone_bottom_over_top": None if keystone is None else round(keystone, 3), "stations": stations,
            "summary": None if not g else {"n": len(g), "median_m": round(float(np.median(g)), 3),
                "p10_m": round(float(np.percentile(g, 10)), 3), "p90_m": round(float(np.percentile(g, 90)), 3)},
            "note": "新紅線是斑駁色塊,線寬逐列變動;尺的不確定度直接反映在 p10–p90。"}

if __name__ == "__main__":
    out = [run(no) for no in sys.argv[1:]]
    Path("isolation/field-2026-09-23/topdown_redline_gap.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for o in out:
        print(o["frame"], "OK" if o["ok"] else "--", o.get("why", ""), "keystone", o.get("grate_keystone_bottom_over_top"),
              "tilt", o.get("axis_tilt_deg"), o.get("summary"))
