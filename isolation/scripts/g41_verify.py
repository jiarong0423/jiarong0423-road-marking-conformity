"""G41 independent re-verification: why §167 cannot see the F07 double line.

Recorder/verifier role. Reads src/, writes nothing outside isolation/ and the
session scratchpad. Every number printed here is produced in this run.

  /opt/anaconda3/bin/python3 isolation/scripts/g41_verify.py <step>

steps: claim1 claim2 claim3 claim4 kernel welded profile pair draw all
"""
from __future__ import annotations

import math
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, "src"))

from marking.extract import markings, road_region                    # noqa: E402
from marking.gate2 import _segments                                  # noqa: E402
from marking.situation import (_merge_collinear, _on_road,           # noqa: E402
                               _paint_bars, _double_line_from_bars)

F07 = os.path.join(HERE, "evidence/field-2026-09-20/IMG_20260920_155735.jpg")
F07_SHA = "f7ffca88480b93eb580874ba5816dfe83d3e881a3413d521ba1542a56dcf1d28"
BLOCK = (1400, 2650, 1450, 2100)      # x0, x1, y0, y1 - the region under test
SCRATCH = "output/g41"   # cache; output/ is not in git
OUT = os.path.join(HERE, "isolation", "out", "g41")


def load():
    import hashlib
    b = open(F07, "rb").read()
    got = hashlib.sha256(b).hexdigest()
    assert got == F07_SHA, f"F07 sha256 mismatch: {got}"
    im = cv2.imread(F07)
    print(f"F07 {os.path.basename(F07)} sha256 {got[:16]}… shape {im.shape}")
    return im


def response(im):
    """Raw dark-light-dark response, cached. It does not depend on the
    threshold - markings() thresholds r1 after computing it - and that is
    checked here rather than assumed."""
    p = os.path.join(SCRATCH, "r_f07.npy")
    if os.path.exists(p):
        return np.load(p)
    os.makedirs(SCRATCH, exist_ok=True)
    _, r, _ = markings(im, min_response=8.0)
    np.save(p, r)
    return r


def mask_at(im, thr, r=None):
    """markings(min_response=thr) reproduced from the cached response."""
    r = response(im) if r is None else r
    m = (r >= thr).astype(np.uint8) * 255
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))


def in_block(x, y):
    x0, x1, y0, y1 = BLOCK
    return x0 <= x <= x1 and y0 <= y <= y1


def seg_in_block(s):
    x1, y1, x2, y2 = s
    return in_block((x1 + x2) / 2, (y1 + y2) / 2)


# --------------------------------------------------------------------- claim 1
def claim1(im):
    print("\n=== claim 1: Hough after merge, inside the block ===")
    h, w = im.shape[:2]
    segs, roi = _segments(im)
    print(f"_segments(F07): {len(segs)} raw segments, roi_frac "
          f"{float((roi > 0).mean()):.4f}")
    merged = _merge_collinear(segs)
    print(f"_merge_collinear: {len(merged)} segments")
    blk = [s for s in merged if seg_in_block(s)]
    lens = sorted((math.hypot(s[2] - s[0], s[3] - s[1]) for s in blk),
                  reverse=True)
    print(f"block {BLOCK}: {len(blk)} merged segments, lengths "
          f"{[round(v, 1) for v in lens[:8]]}")
    print(f"length threshold in _double_white: h*0.15 = {h}*0.15 = {h * 0.15:.1f} px")
    print(f"longest in block {lens[0] if lens else 0:.1f} px -> clears "
          f"threshold: {bool(lens and lens[0] >= h * 0.15)}")
    onroad = [s for s in blk if _on_road(s, im.shape)]
    print(f"of those, _on_road: {len(onroad)}")
    # and the same over the whole frame, for context
    allen = sorted((math.hypot(s[2] - s[0], s[3] - s[1]) for s in merged),
                   reverse=True)
    print(f"whole frame: longest merged {allen[0]:.1f} px, "
          f"{sum(1 for v in allen if v >= h * 0.15)} clear h*0.15")
    return blk


# --------------------------------------------------------------------- claim 2
def claim2(im):
    print("\n=== claim 2: is it a resolution problem ===")
    x0, x1, y0, y1 = BLOCK
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0].astype(np.float32)
    # horizontal cross-sections through the block, bright runs measured on L*
    print("cross-sections on L* (run = consecutive L* >= 200):")
    widths = []
    for y in range(y0, y1 + 1, 50):
        row = L[y, x0:x1 + 1] >= 200
        runs, n = [], 0
        for v in row:
            if v:
                n += 1
            elif n:
                runs.append(n); n = 0
        if n:
            runs.append(n)
        runs = [r for r in runs if r >= 5]
        if runs:
            widths += runs
            print(f"  y={y:5d}  runs {runs}")
    if widths:
        print(f"  bright-run widths: n={len(widths)} min={min(widths)} "
              f"max={max(widths)} median={int(np.median(widths))}")
    # component L* of the paint mask inside the block
    m = mask_at(im, 8.0)
    sub = np.zeros_like(m); sub[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]
    n, lbl, st, cen = cv2.connectedComponentsWithStats(sub, 8)
    big = [(int(st[i, cv2.CC_STAT_AREA]), i) for i in range(1, n)
           if st[i, cv2.CC_STAT_AREA] >= 400]
    big.sort(reverse=True)
    print(f"components in block with area>=400: {len(big)}")
    for area, i in big[:6]:
        mean_l = float(L[lbl == i].mean())
        print(f"  area {area:6d}  mean L* {mean_l:6.1f}  "
              f"bbox {st[i, 0]},{st[i, 1]} {st[i, 2]}x{st[i, 3]}")
    # the pixel budget the project's own script predicts at this range
    print("pixel budget (project's own arithmetic, f35=24mm, 3072 px wide):")
    for dist in (19, 40, 65):
        # 10 cm line, 24 mm equivalent focal length -> hfov
        hfov = 2 * math.degrees(math.atan(36 / 2 / 24))
        px_per_m_at = 3072 / (2 * dist * math.tan(math.radians(hfov / 2)))
        print(f"  {dist:3d} m: {px_per_m_at:6.1f} px/m across -> a 0.10 m "
              f"line spans {px_per_m_at * 0.10:5.1f} px")


# --------------------------------------------------------------------- claim 3
def claim3(im):
    print("\n=== claim 3: is it a threshold problem ===")
    h, w = im.shape[:2]
    r = response(im)
    # the cached response is the same object markings() thresholds - check it
    mk, rk, _ = markings(im, min_response=4.0)
    same = bool(np.array_equal(mk, mask_at(im, 4.0, r)))
    print(f"cached-response reconstruction == markings(min_response=4.0): {same}")
    roi = road_region(im)
    for thr in (8.0, 6.5, 5.0, 4.0):
        m = mask_at(im, thr, r)
        cov = float((m > 0).mean()) * 100
        mm = cv2.bitwise_and(m, roi)
        edges = cv2.Canny(mm, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 720, 40,
                                minLineLength=max(25, w // 25), maxLineGap=6)
        segs = ([] if lines is None
                else [tuple(map(float, s)) for s in lines.reshape(-1, 4)])
        merged = _merge_collinear(segs)
        blk = [s for s in merged if seg_in_block(s)]
        longs = [s for s in blk
                 if math.hypot(s[2] - s[0], s[3] - s[1]) >= h * 0.15]
        best = max((math.hypot(s[2] - s[0], s[3] - s[1]) for s in blk),
                   default=0.0)
        print(f"  min_response={thr:4.1f}  paint coverage {cov:5.1f}%  "
              f"raw segs {len(segs):5d}  merged {len(merged):5d}  "
              f"in block {len(blk):3d}  >=h*0.15 in block {len(longs)}  "
              f"longest in block {best:6.1f} px")


# --------------------------------------------------------------------- claim 4
def claim4(im):
    print("\n=== claim 4: contours + minAreaRect on the same mask ===")
    h = im.shape[0]
    roi = road_region(im)
    x0, x1, y0, y1 = BLOCK
    for label, ksize in (("no close", None), ("3x3", 3), ("5x5", 5), ("9x9", 9)):
        m = cv2.bitwise_and(mask_at(im, 8.0), roi)
        if ksize:
            m = cv2.morphologyEx(
                m, cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize)))
        sub = np.zeros_like(m); sub[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]
        cs = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        rows = []
        for c in cs:
            if cv2.contourArea(c) < 400:
                continue
            (cx, cy), (rw, rh), ang = cv2.minAreaRect(c)
            length, width = max(rw, rh), min(rw, rh)
            if width < 2 or length < h * 0.10 or length / width < 4.0:
                continue
            if rw < rh:
                ang += 90.0
            rows.append((length, width, ang % 180.0, cx, cy))
        rows.sort(reverse=True)
        print(f"  close {label:8s}: {len(rows)} bar-shaped objects")
        for length, width, ang, cx, cy in rows:
            print(f"      {length:6.1f} x {width:5.1f}  ar {length / width:5.2f}  "
                  f"ang {ang:6.1f}  centre ({cx:7.1f},{cy:7.1f})")


# -------------------------------------------------------------------- kernel
def kernel_sweep(im):
    print("\n=== key suspicion: does MORPH_CLOSE weld the two lines together ===")
    roi = road_region(im)
    x0, x1, y0, y1 = BLOCK
    base = cv2.bitwise_and(mask_at(im, 8.0), roi)
    for label, ksize in (("none", None), ("3x3", 3), ("5x5", 5), ("9x9", 9),
                         ("15x15", 15), ("25x25", 25)):
        m = base.copy()
        if ksize:
            m = cv2.morphologyEx(
                m, cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize)))
        sub = np.zeros_like(m); sub[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]
        n, lbl, st, _ = cv2.connectedComponentsWithStats(sub, 8)
        comps = sorted(((int(st[i, cv2.CC_STAT_AREA]), i) for i in range(1, n)
                        if st[i, cv2.CC_STAT_AREA] >= 400), reverse=True)
        cs = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        bars = []
        for c in cs:
            if cv2.contourArea(c) < 400:
                continue
            (cx, cy), (rw, rh), _ = cv2.minAreaRect(c)
            bars.append((max(rw, rh), min(rw, rh)))
        bars.sort(reverse=True)
        print(f"  close {label:6s}: {len(comps)} components area>=400, "
              f"{len(bars)} contours area>=400; top rects "
              f"{[(round(a), round(b, 1)) for a, b in bars[:4]]}")
        print(f"      block paint coverage "
              f"{float((sub[y0:y1 + 1, x0:x1 + 1] > 0).mean()) * 100:5.1f}%")


# ---------------------------------------------------------------------- pair
def pair(im):
    print("\n=== _double_line_from_bars: which criterion rejects the pair ===")
    roi = road_region(im)
    bars = _paint_bars(im, roi)
    print(f"_paint_bars(F07, roi) -> {len(bars)} bars over the WHOLE frame")
    for k, ((cx, cy), (length, width), ang, _) in enumerate(bars):
        print(f"  bar[{k}] centre ({cx:7.1f},{cy:7.1f}) len {length:7.1f} "
              f"width {width:6.1f} ar {length / width:5.2f} ang {ang:6.1f} "
              f"in_block {in_block(cx, cy)}")
    out = _double_line_from_bars(im, roi)
    print(f"_double_line_from_bars(F07, roi) -> {out}")
    if len(bars) < 2:
        print("  REJECTED AT THE DOOR: fewer than 2 bars, no pair is formed.")
        return bars
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0].astype(np.float32); B = lab[:, :, 2].astype(np.float32)
    h, w = L.shape
    print("  every pair, every criterion, with the value that decided it:")
    for i in range(len(bars)):
        (ci, (li, wi), ai, _) = bars[i]
        for j in range(i + 1, len(bars)):
            (cj, (lj, wj), aj, _) = bars[j]
            da = min(abs(ai - aj), 180 - abs(ai - aj))
            wr = max(wi, wj) / max(1e-6, min(wi, wj))
            th = math.radians((ai + aj) / 2)
            d = np.array([math.cos(th), math.sin(th)])
            n = np.array([-d[1], d[0]])
            pi_, pj_ = np.array(ci), np.array(cj)
            gap = abs(float((pj_ - pi_) @ n))
            width = (wi + wj) / 2
            ratio = gap / max(1e-6, width)
            mid = (pi_ + pj_) / 2
            xx, yy = int(mid[0]), int(mid[1])
            here = float(L[yy, xx]) if (0 <= xx < w and 0 <= yy < h) else float("nan")
            on = (float(L[int(pi_[1]) % h, int(pi_[0]) % w])
                  + float(L[int(pj_[1]) % h, int(pj_[0]) % w])) / 2
            bi = float(B[int(pi_[1]) % h, int(pi_[0]) % w])
            bj = float(B[int(pj_[1]) % h, int(pj_[0]) % w])
            fails = []
            if da > 6.0:
                fails.append(f"angle {da:.2f}deg > 6")
            if wr > 2.0:
                fails.append(f"width ratio {wr:.2f} > 2.0")
            if abs(ratio - 1.0) > 0.6:
                fails.append(f"gap/width {ratio:.3f} outside 1.0+-0.6")
            if not (on - here >= 18):
                fails.append(f"contrast {on - here:.1f} < 18")
            if (bi > 140) != (bj > 140):
                fails.append(f"colour split b* {bi:.1f}/{bj:.1f}")
            print(f"  pair({i},{j}) angle_d {da:6.2f} widths {wi:6.1f}/{wj:6.1f} "
                  f"wratio {wr:5.2f} gap {gap:7.1f} gap/width {ratio:6.3f} "
                  f"L*on {on:6.1f} L*gap {here:6.1f} contrast {on - here:7.1f} "
                  f"b* {bi:5.1f}/{bj:5.1f}")
            print(f"            -> {'PASS' if not fails else 'REJECT: ' + '; '.join(fails)}")
    return bars


# ------------------------------------------------------------------- profile
# The axis of the real double line, from the one object _paint_bars returns
# there. Measured, not assumed: bar[3] centre (1972.7, 1743.8), angle 148.9.
AXIS_C, AXIS_ANG = (1972.7, 1743.8), 148.9


def profile(im):
    """Where the paint is, and where the detector actually responds.

    The decisive measurement for G41. A perpendicular cut through the line:
    the two members sit at u -23..-7 and +10..+29 with a 17 px dark gap
    between them, and the only mask run present at every station is u -1..+5,
    which is the middle of that gap.
    """
    print("\n=== perpendicular profile through the real double line ===")
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0].astype(np.float32)
    r = response(im)
    roi = road_region(im)
    m = cv2.bitwise_and(mask_at(im, 8.0, r), roi)
    h, w = L.shape
    th = math.radians(AXIS_ANG)
    d = np.array([math.cos(th), math.sin(th)])
    n = np.array([-d[1], d[0]])
    c = np.array(AXIS_C)

    def runs(flags, off):
        seg, st = [], None
        for i, v in enumerate(flags):
            if v and st is None:
                st = i
            if not v and st is not None:
                seg.append((st + off, i - 1 + off)); st = None
        if st is not None:
            seg.append((st + off, len(flags) - 1 + off))
        return seg

    print("u = signed perpendicular offset (px). paint = L*>=190, "
          "mask = markings(8.0)")
    for t in range(-180, 181, 60):
        base = c + d * t
        pts = [(int(round((base + n * u)[0])), int(round((base + n * u)[1])))
               for u in range(-45, 46)]
        print(f"  t={t:5d}  paint runs {runs([L[y, x] >= 190 for x, y in pts], -45)}"
              f"   mask runs {runs([m[y, x] > 0 for x, y in pts], -45)}")

    print("\nresponse on the paint vs on the gap:")
    allb = []
    P = G = PM = GM = 0
    for t in np.arange(-200, 201, 1.0):
        base = c + d * t
        for u in np.arange(-45, 45.1, 1.0):
            p = base + n * u
            x, y = int(round(p[0])), int(round(p[1]))
            if not (0 <= x < w and 0 <= y < h):
                continue
            if L[y, x] >= 190:
                P += 1; PM += bool(m[y, x]); allb.append(float(r[y, x]))
            elif -7 < u < 10:
                G += 1; GM += bool(m[y, x])
    allb = np.array(allb)
    for thr in (8.0, 6.5, 5.0, 4.0):
        print(f"   r>={thr:4.1f} : {100 * float((allb >= thr).mean()):5.1f}% "
              f"of {allb.size} paint samples")
    print(f"   median r on paint {np.median(allb):.2f}, "
          f"p90 {np.percentile(allb, 90):.2f}, max {allb.max():.2f}")
    print(f"   paint pixels {P}, of which in mask {PM} = {100 * PM / P:.1f}%")
    print(f"   gap   pixels {G}, of which in mask {GM} = {100 * GM / G:.1f}%")


def welded(im):
    """How many pre-close pieces the 9x9 close fuses into one object."""
    print("\n=== what the 9x9 close welds together ===")
    roi = road_region(im)
    x0, x1, y0, y1 = BLOCK
    base = cv2.bitwise_and(mask_at(im, 8.0), roi)
    sub = np.zeros_like(base); sub[y0:y1 + 1, x0:x1 + 1] = base[y0:y1 + 1, x0:x1 + 1]
    c9 = cv2.morphologyEx(sub, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    tgt = None
    for c in cv2.findContours(c9, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        if cv2.contourArea(c) < 400:
            continue
        (_, _), (rw, rh), _ = cv2.minAreaRect(c)
        if abs(max(rw, rh) - 433.8) < 2 and abs(min(rw, rh) - 60.5) < 2:
            tgt = c
    if tgt is None:
        print("  the 434x60.5 object was not found - the mask changed"); return
    foot = np.zeros_like(c9); cv2.drawContours(foot, [tgt], -1, 255, -1)
    n, _, st, _ = cv2.connectedComponentsWithStats(cv2.bitwise_and(sub, foot), 8)
    inside = sorted(((int(st[i, cv2.CC_STAT_AREA]), int(st[i, 0]), int(st[i, 1]),
                      int(st[i, 2]), int(st[i, 3])) for i in range(1, n)),
                    reverse=True)
    print(f"  pre-close components inside that one 9x9 object: {len(inside)}  "
          f"(area>=200: {sum(1 for a, *_ in inside if a >= 200)})")
    for a, bx, by, bw, bh in inside[:6]:
        print(f"     area {a:5d} bbox {bx:4d},{by:4d} {bw:3d}x{bh:3d}")


# ---------------------------------------------------------------------- draw
def draw(im):
    """Nothing here counts as a detection until it is drawn and looked at."""
    os.makedirs(OUT, exist_ok=True)
    roi = road_region(im)
    x0, x1, y0, y1 = BLOCK
    canvas = im.copy()
    cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 200, 255), 6)
    for label, ksize, colour in (("none", None, (0, 0, 255)),
                                 ("3x3", 3, (0, 255, 0)),
                                 ("9x9", 9, (255, 0, 0))):
        m = cv2.bitwise_and(mask_at(im, 8.0), roi)
        if ksize:
            m = cv2.morphologyEx(
                m, cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize)))
        sub = np.zeros_like(m); sub[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]
        for c in cv2.findContours(sub, cv2.RETR_EXTERNAL,
                                  cv2.CHAIN_APPROX_SIMPLE)[0]:
            if cv2.contourArea(c) < 400:
                continue
            rect = cv2.minAreaRect(c)
            if max(rect[1]) < im.shape[0] * 0.10:
                continue
            box = np.intp(cv2.boxPoints(rect))
            cv2.drawContours(canvas, [box], 0, colour, 4)
    cv2.imwrite(os.path.join(OUT, "f07_boxes_full.jpg"), canvas,
                [cv2.IMWRITE_JPEG_QUALITY, 92])
    # the block at full resolution, and the masks side by side
    cv2.imwrite(os.path.join(OUT, "f07_block_raw.jpg"),
                im[y0:y1 + 1, x0:x1 + 1], [cv2.IMWRITE_JPEG_QUALITY, 95])
    cv2.imwrite(os.path.join(OUT, "f07_block_boxes.jpg"),
                canvas[y0:y1 + 1, x0:x1 + 1], [cv2.IMWRITE_JPEG_QUALITY, 95])
    strips = []
    for ksize in (None, 3, 9):
        m = cv2.bitwise_and(mask_at(im, 8.0), roi)
        if ksize:
            m = cv2.morphologyEx(
                m, cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize)))
        strips.append(cv2.cvtColor(m[y0:y1 + 1, x0:x1 + 1], cv2.COLOR_GRAY2BGR))
    cv2.imwrite(os.path.join(OUT, "f07_block_masks.jpg"),
                np.vstack(strips), [cv2.IMWRITE_JPEG_QUALITY, 92])

    # the two objects _paint_bars returns inside the block, at full
    # resolution and unannotated, because the verdict on what they ARE was
    # reached by looking at these two and nothing else
    cv2.imwrite(os.path.join(OUT, "zoom_bar3.jpg"),
                cv2.resize(im[1620:1900, 1720:2260], None, fx=1.6, fy=1.6),
                [cv2.IMWRITE_JPEG_QUALITY, 95])
    cv2.imwrite(os.path.join(OUT, "zoom_bar2.jpg"),
                cv2.resize(im[1650:1900, 1180:1700], None, fx=1.6, fy=1.6),
                [cv2.IMWRITE_JPEG_QUALITY, 95])

    # the paint mask over the real line, at each kernel size, on the photo
    tiles = []
    for k, lab in ((None, "raw photo"), (None, "mask no close"),
                   (3, "mask 3x3"), (9, "mask 9x9")):
        if lab == "raw photo":
            t = im[1620:1900, 1720:2260].copy()
        else:
            mm = cv2.bitwise_and(mask_at(im, 8.0), roi)
            if k:
                mm = cv2.morphologyEx(
                    mm, cv2.MORPH_CLOSE,
                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
            ov = im[1620:1900, 1720:2260].copy()
            ov[mm[1620:1900, 1720:2260] > 0] = (0, 0, 255)
            t = cv2.addWeighted(im[1620:1900, 1720:2260], 0.45, ov, 0.55, 0)
        cv2.putText(t, lab, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    (0, 255, 255), 3)
        tiles.append(t)
    cv2.imwrite(os.path.join(OUT, "f07_mask_kernels.jpg"),
                np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]),
                [cv2.IMWRITE_JPEG_QUALITY, 92])

    # the four whole-frame bars, labelled, so the pair diagnostic can be read
    from marking.situation import _paint_bars as _pb
    c2 = im.copy()
    cv2.rectangle(c2, (x0, y0), (x1, y1), (0, 215, 255), 8)
    cols = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 0, 255)]
    for k, (ctr, (ln, wd), a, box) in enumerate(_pb(im, roi)):
        cv2.drawContours(c2, [np.intp(np.array(box))], 0, cols[k % 4], 8)
        cv2.putText(c2, f"bar{k} {ln:.0f}x{wd:.0f} a{a:.0f}",
                    (int(ctr[0]) - 150, int(ctr[1]) - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, cols[k % 4], 5)
    cv2.imwrite(os.path.join(OUT, "f07_bars_full.jpg"), c2,
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    cv2.imwrite(os.path.join(OUT, "f07_bars_small.jpg"),
                cv2.resize(c2, (768, 1024)), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"\nwrote {OUT}/f07_boxes_full.jpg, f07_block_raw.jpg, "
          f"f07_block_boxes.jpg, f07_block_masks.jpg")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    im = load()
    if step in ("claim1", "all"):
        claim1(im)
    if step in ("claim2", "all"):
        claim2(im)
    if step in ("claim3", "all"):
        claim3(im)
    if step in ("claim4", "all"):
        claim4(im)
    if step in ("kernel", "all"):
        kernel_sweep(im)
    if step in ("welded", "all"):
        welded(im)
    if step in ("profile", "all"):
        profile(im)
    if step in ("pair", "all"):
        pair(im)
    if step in ("draw", "all"):
        draw(im)
