#!/usr/bin/env python3
"""The recognition figures: original beside what the system found, nothing hand-placed.

Three panels, one per thing OpenCV finds on its own here:
  chevron   the white-paint-density polygon (measure_taper_phone.run) and,
            where the frame passed, the two edge pencils it measured
  redline   the saturated / faint red masks measure_redline_gap.run uses
  grates    the gutter-facing Street View with the bar-texture boxes

    /opt/anaconda3/bin/python3 scripts/draw_recognition.py
"""
import glob, json, math, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import measure_redline_gap as M, measure_chevron_phone as C
OUT = ROOT / "docs/figures"; F = sorted(glob.glob(M.FIELD))

def label(t, s):
    cv2.rectangle(t, (0, 0), (min(t.shape[1], 30 + 22 * len(s)), 46), (0, 0, 0), -1)
    cv2.putText(t, s, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2); return t

def chevron_panel(fr, width=760):
    img = cv2.imread(F[fr - 1]); h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); lv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white = cv2.inRange(hsv, (0, 0, int(lv)), (180, 60, 255)); white[:int(h * 0.38)] = 0
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dens = cv2.blur((white > 0).astype(np.float32), (121, 121)); n, lbl, st, _ = cv2.connectedComponentsWithStats((dens > 0.12).astype(np.uint8), 8)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); ys, xs = np.nonzero(lbl == big)
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    x, y, bw, bh = cv2.boundingRect(hull); pad = 160
    x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(w, x + bw + pad), min(h, y + bh + pad)
    over = img.copy(); m = white > 0; over[m] = (0.4 * over[m] + 0.6 * np.array([0, 255, 0])).astype(np.uint8)
    cv2.polylines(over, [hull], True, (0, 0, 255), 8)
    res = json.loads((ROOT / "results/taper_phone.json").read_text())
    fr_res = next((r for r in res["frames"] if r["frame"] == f"F{fr:02d}"), None)
    tag = f"F{fr}"
    if fr_res and fr_res.get("ok"):
        # redraw the two edge pencils the script used
        out = C.__dict__  # noqa: F841 (import kept for M.hline / seglen parity)
        e = cv2.Canny(white, 50, 150); L = cv2.HoughLinesP(e, 1, np.pi / 1440, 50, minLineLength=200, maxLineGap=12)
        inside = cv2.dilate((lbl == big).astype(np.uint8), np.ones((61, 61), np.uint8))
        longs = [tuple(map(float, s)) for s in (L.reshape(-1, 4) if L is not None else []) if math.hypot(s[2] - s[0], s[3] - s[1]) > 200]
        inhull = [s for s in longs if inside[int((s[1] + s[3]) / 2), int((s[0] + s[2]) / 2)] > 0]
        rest, cols = list(inhull), [(255, 0, 255), (0, 255, 255)]
        for k in range(2):
            r, inl = C.ransac_vp(rest, 6.0, (0, h * 0.60))
            if r is None: break
            for s in inl: cv2.line(over, (int(s[0]), int(s[1])), (int(s[2]), int(s[3])), cols[k], 10)
            X = {tuple(s) for s in inl}; rest = [s for s in rest if tuple(s) not in X]
        tag += f"  taper {fr_res['taper_deg']} deg = {fr_res['taper_ratio']}:1"
    else:
        tag += "  refused: " + (fr_res["why"][:38] if fr_res else "-")
    a, b = img[y0:y1, x0:x1], over[y0:y1, x0:x1]
    s = width / a.shape[1]; a = cv2.resize(a, (width, int(a.shape[0] * s))); b = cv2.resize(b, (width, int(b.shape[0] * s)))
    return np.hstack([label(a, f"F{fr} original"), label(b, tag)])

def main():
    OUT.mkdir(exist_ok=True)
    panels = [chevron_panel(fr) for fr in (17, 40, 18, 19, 20, 37)]
    W = max(p.shape[1] for p in panels); panels = [np.hstack([p, np.zeros((p.shape[0], W - p.shape[1], 3), np.uint8)]) for p in panels]
    sheet = np.vstack(panels); cv2.imwrite(str(OUT / "recognition-chevron.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
    print("docs/figures/recognition-chevron.jpg", sheet.shape)

if __name__ == "__main__":
    main()
