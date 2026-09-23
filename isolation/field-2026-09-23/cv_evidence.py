"""Evidence from the 09-23 top-down frames by image recognition (isolation, 2026-09-23).

Owner: 「想辦法把證據用影像辨識學找出來」. Per frame:
  grate   dark gaps between bright bars -> closed -> the largest near-rectangular component;
          confirmed by bar periodicity (FFT peak / mean >= 6) along both axes AT FULL RESOLUTION
          (the 2026-09-22 detector inverted at one-third resolution)
  red     new red line = LAB a* well above the frame median; its axis from patch centroids
  ruler   the new red line's width, full-width rows only (validated 95-97 mm against a card)
  holes   dark, near-circular blobs of plausible drain-hole size
Everything in cm through the ruler; top-down frames only (the ruler is a local, flat scale).
"""
import sys, json, math, csv, cv2, numpy as np
from pathlib import Path

D = Path("evidence/field-2026-09-23")
ROWS = {r["no"]: r for r in csv.DictReader(open(D / "MANIFEST.csv"))}


def red_masks(img):
    a = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 1].astype(np.int16); med = int(np.median(a))
    strong = cv2.morphologyEx(((a - med) > 12).astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    return cv2.morphologyEx(strong, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))


def periodicity(profile):
    p = profile - profile.mean(); f = np.abs(np.fft.rfft(p))[3:len(p) // 4]
    return float(f.max() / (f.mean() + 1e-9)) if len(f) else 0.0


def grate(gray, thr=45, open_k=61):
    h, w = gray.shape
    # gaps between bars open onto the drain below. Measured 2026-09-23 on P09/P29/P50: gap pixels
    # 10-51 grey, the concrete's darkest tenth 57-92. A global percentile missed covers 4-6 and a
    # background-relative test failed because the whole grate darkens its own background.
    dark = (gray < thr).astype(np.uint8)
    cl = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((45, 45), np.uint8))
    cl = cv2.morphologyEx(cl, cv2.MORPH_OPEN, np.ones((open_k, open_k), np.uint8))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(cl, 8)
    best = None
    for i in range(1, n):
        x, y, bw, bh, area = st[i]
        if area < 0.02 * h * w or x == 0 or y == 0 or x + bw >= w or y + bh >= h: continue
        cnt, _ = cv2.findContours((lbl == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rect = cv2.minAreaRect(max(cnt, key=cv2.contourArea)); rw, rh = rect[1]
        fill = area / max(rw * rh, 1)
        if fill < 0.75 or not 0.5 < rw / max(rh, 1) < 2.0: continue
        roi = gray[y:y + bh, x:x + bw].astype(np.float32)
        px, py = periodicity(roi.mean(0)), periodicity(roi.mean(1))
        if max(px, py) < 6: continue
        if best is None or area > best["area"]:
            best = {"area": int(area), "rect": [list(map(float, rect[0])), [float(rw), float(rh)], float(rect[2])],
                    "bbox": [int(x), int(y), int(bw), int(bh)], "fill": round(float(fill), 3),
                    "period_x": round(px, 1), "period_y": round(py, 1), "dark_threshold": thr, "open_px": open_k}
    return best


def grate_any(gray):
    # P29's gaps read 29-51 grey (a shallower drain, more light): relax only if 45 finds nothing,
    # and every relaxation still has to pass the bar-periodicity test
    # P29 (cover 4): the grate joined a hole and a dark band below it into one strip (fill 0.52)
    # though its bars were strongly periodic (25/36). A wider opening cuts the thin joint.
    for thr in (45, 55, 65):
        for k in (61, 151, 251):
            g = grate(gray, thr, k)
            if g: return g
    return None


def ruler_px(red, axis_p0, axis_d):
    """Median of the widest quarter of cross-section widths along the red axis."""
    h, w = red.shape; nv = np.array([-axis_d[1], axis_d[0]]); widths = []
    for t in np.arange(-3000, 3000, 20):
        c = axis_p0 + axis_d * t
        if not (0 <= c[0] < w and 0 <= c[1] < h): continue
        ss = np.arange(-400, 400); P = (c[None] + ss[:, None] * nv[None]).astype(int)
        ok = (P[:, 0] >= 0) & (P[:, 0] < w) & (P[:, 1] >= 0) & (P[:, 1] < h)
        v = np.zeros(len(ss), bool); v[ok] = red[P[ok, 1], P[ok, 0]] > 0
        idx = np.nonzero(v)[0]
        if len(idx) < 20: continue
        runs = np.split(idx, np.nonzero(np.diff(idx) > 2)[0] + 1); r = max(runs, key=len)
        if abs((r[0] + r[-1]) / 2 - 400) < 200: widths.append(len(r))
    if len(widths) < 8: return None, widths
    top = sorted(widths)[-max(3, len(widths) // 4):]
    return float(np.median(top)), widths


def holes(gray, px_per_cm, exclude):
    h, w = gray.shape
    dark = (gray < np.percentile(gray, 6)).astype(np.uint8)
    dark[exclude > 0] = 0
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    cnt, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnt:
        a = cv2.contourArea(c)
        if a < 400: continue
        (x, y), r = cv2.minEnclosingCircle(c); circ = a / (math.pi * r * r)
        d_cm = 2 * r / px_per_cm
        if circ > 0.6 and 5 <= d_cm <= 25:
            out.append({"xy": [round(x), round(y)], "diam_cm": round(d_cm, 1), "circularity": round(circ, 2)})
    return out


def run(no):
    img = cv2.imread(str(D / ROWS[no]["file"])); gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); h, w = gray.shape
    res = {"frame": no, "group": ROWS[no]["group"], "file": ROWS[no]["file"]}
    g = grate_any(gray); res["grate"] = g
    red = red_masks(img)
    n, lbl, st, cen = cv2.connectedComponentsWithStats(red, 8)
    # the old line runs along the frame edge as a long thin strip; the new line is blocks above/below the grate
    comps = [i for i in range(1, n) if st[i, 4] > 15000
             and st[i, 0] > 0.08 * w and st[i, 0] + st[i, 2] < 0.92 * w
             and max(st[i, 2], st[i, 3]) / max(1, min(st[i, 2], st[i, 3])) < 6]
    if not comps:
        res["why"] = "new red line: no patch"; return res, img
    if len(comps) >= 2:
        pts = np.array([cen[i] for i in comps], np.float32)
        vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        res["red_axis_from"] = f"{len(comps)} patch centroids"
    else:   # one patch (cover 4): its own long axis - a painted stripe is longer than it is wide
        ys, xs = np.nonzero(lbl == comps[0]); P = np.stack([xs, ys], 1).astype(np.float32)
        vx, vy, x0, y0 = cv2.fitLine(P, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
        res["red_axis_from"] = "one patch, its principal axis"
    d = np.array([vx, vy]); p0 = np.array([x0, y0])
    rp, widths = ruler_px(red, p0, d)
    if rp is None:
        res["why"] = "ruler: red line cross-sections too few"; return res, img
    ppcm = rp / 10.0; res["ruler"] = {"px_per_10cm": round(rp, 1), "rows": len(widths)}
    if g:
        (cx, cy), (rw, rh), ang = g["rect"]
        nv = np.array([-d[1], d[0]]); off = float((np.array([cx, cy]) - p0) @ nv)
        res["grate_cm"] = {"w": round(rw / ppcm, 1), "h": round(rh / ppcm, 1)}
        res["red_axis_to_grate_centre_cm"] = round(abs(off) / ppcm, 1)
        half_across = abs(np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))]) @ nv) * rw / 2 + \
                      abs(np.array([-math.sin(math.radians(ang)), math.cos(math.radians(ang))]) @ nv) * rh / 2
        res["red_axis_crosses_grate"] = bool(abs(off) < half_across)
    excl = np.zeros_like(gray)
    if g:
        x, y, bw, bh = g["bbox"]; excl[max(0, y - 40):y + bh + 40, max(0, x - 40):x + bw + 40] = 1
    hs = holes(gray, ppcm, excl)
    nv = np.array([-d[1], d[0]])
    for hh in hs:
        hh["off_red_axis_cm"] = round(abs((np.array(hh["xy"]) - p0) @ nv) / ppcm, 1)
    res["holes"] = hs
    # overlay
    v = img.copy()
    if g:
        box = cv2.boxPoints(tuple(map(lambda t: tuple(t) if isinstance(t, list) else t, g["rect"])))
        cv2.drawContours(v, [box.astype(np.int32)], 0, (0, 255, 255), 14)
    a = p0 - d * 5000; b = p0 + d * 5000
    cv2.line(v, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (255, 0, 255), 10)
    for hh in hs: cv2.circle(v, tuple(hh["xy"]), int(hh["diam_cm"] * ppcm / 2) + 10, (0, 255, 0), 12)
    return res, v


if __name__ == "__main__":
    outdir = Path(sys.argv[1]); outdir.mkdir(parents=True, exist_ok=True); allr = []
    for no in sys.argv[2:]:
        r, v = run(no); allr.append(r)
        cv2.imwrite(str(outdir / f"{no}_cv.jpg"), cv2.resize(v, (768, 1024)), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(json.dumps({k: r.get(k) for k in ("frame", "group", "grate_cm", "red_axis_to_grate_centre_cm", "red_axis_crosses_grate", "ruler", "why")}, ensure_ascii=False),
              "holes", [(x["diam_cm"], x["off_red_axis_cm"]) for x in r.get("holes", [])], "grate_period", (r["grate"] or {}).get("period_x"), (r["grate"] or {}).get("period_y"))
    json.dump(allr, open(outdir / "cv_evidence.json", "w"), ensure_ascii=False, indent=1)
