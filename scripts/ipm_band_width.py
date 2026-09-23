"""The chevron's width in metres, measured on its arms in the bird's eye plane.

Everything here is decided by §171 and checked against it:

  the arms lie 45° to the band          - used to separate them from the
                                          boundary lines, and re-measured
                                          afterwards as the acceptance test
  an arm is 20 cm wide                  - the scale, giving the camera height
  the band's width is the arm's reach   - at 45°, W = L·sin45°

The previous attempt measured a V-shaped component's principal axis, which
runs along the bisector and therefore along the band. Arms are isolated here
by opening with a line element laid along the arm direction, so a V is cut
into its two arms and the boundary lines, which run at 45° to them, do not
survive.

The camera height is printed because it is the check, not an input: one
camera took every capture and Street View sits near 2.5 m.
"""
import sys, json, math
import cv2, numpy as np

PX = 260.0            # bird's eye pixels per camera height
ARM_W = 0.20          # m, §171 - kept for the record, no longer the scale
ARM_PITCH = 0.50      # m, §171: a 20 cm arm every 30 cm, so a 50 cm repeat
CAPS = ["f40_p-20", "f60_p-20", "f90_p-20", "f60_p-35", "f90_p-35",
        "before_p-25", "before_p-40", "before_close"]

def se(metres, ang_deg):
    L = max(3, int(metres*PX)) | 1
    k = np.zeros((L, L), np.uint8); c = L//2; t = math.radians(ang_deg)
    for s in np.linspace(-L/2, L/2, L*4):
        x, y = int(round(c+s*math.cos(t))), int(round(c+s*math.sin(t)))
        if 0 <= x < L and 0 <= y < L: k[y, x] = 1
    return k

def directions(paint):
    """Band and arm, from the segment angle histogram. No window is assumed."""
    e = cv2.Canny(paint, 50, 150)
    ls = cv2.HoughLinesP(e, 1, np.pi/720, int(0.12*PX),
                         minLineLength=int(0.25*PX), maxLineGap=int(0.06*PX))
    if ls is None:
        return None
    seg = ls.reshape(-1, 4)
    ang = np.array([math.degrees(math.atan2(y2-y1, x2-x1)) % 180
                    for x1, y1, x2, y2 in seg])
    wt = np.array([math.hypot(x2-x1, y2-y1) for x1, y1, x2, y2 in seg])
    h, _ = np.histogram(ang, bins=180, range=(0, 180), weights=wt)
    h = np.convolve(np.r_[h, h, h], np.ones(5)/5, "same")[180:360]
    band = int(np.argmax(h))
    # the arm is the strongest direction that sits 45 +- 12 deg off the band
    cand = [(h[i], i) for i in range(180)
            if 33 <= min(abs(i-band), 180-abs(i-band)) <= 57]
    if not cand:
        return None
    arm = max(cand)[1]
    return band, arm, float(min(abs(arm-band), 180-abs(arm-band))), len(seg)

rows = []
for stem in CAPS:
    bev = cv2.imread(f"output/bev_{stem}.png")
    if bev is None:
        continue
    g = cv2.cvtColor(bev, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    cover = bev.sum(2) > 0
    paint = (((g - cv2.GaussianBlur(g, (0, 0), 0.30*PX)) > 12) & cover
             ).astype(np.uint8)*255
    paint = cv2.morphologyEx(paint, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    d = directions(paint)
    if d is None:
        print(f"{stem:14s} -- no arm family 45 deg off the band"); continue
    band, arm, sep, nseg = d

    # keep what runs along the arm; the boundary runs 45 deg away and is cut
    arms = cv2.morphologyEx(paint, cv2.MORPH_OPEN, se(0.45, arm))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(arms, 8)
    ad = np.array([math.cos(math.radians(arm)), math.sin(math.radians(arm))])
    an = np.array([-ad[1], ad[0]])
    widths, reaches, checks, cents = [], [], [], []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < (0.09*PX)**2:
            continue
        yy, xx = np.nonzero(lbl == i)
        q = np.stack([xx, yy], 1).astype(np.float32); c = q.mean(0)
        al = (q - c) @ ad; ac = (q - c) @ an
        reach = float(al.max()-al.min())
        if reach < 0.35*PX:
            continue
        # width across the arm, read at stations so a blob cannot pass
        ws = []
        for t in np.linspace(al.min()+0.05*PX, al.max()-0.05*PX, 9):
            sel = np.abs(al - t) < 0.02*PX
            if sel.sum() < 6: continue
            ws.append(float(ac[sel].max() - ac[sel].min()))
        if len(ws) < 5:
            continue
        widths.append(float(np.median(ws))); reaches.append(reach)
        cents.append(c)
        _, _, vv = np.linalg.svd(q - c, full_matrices=False)
        checks.append(math.degrees(math.atan2(vv[0][1], vv[0][0])) % 180)
    if len(widths) < 5:
        print(f"{stem:14s} -- {len(widths)} arms"); continue
    w_px = float(np.median(widths))
    # The scale is the repeat along the band, not an arm's width. A 20 cm
    # width is a few pixels and what a threshold calls its edge moves with
    # the source blur: the same arm measured 20.9 px at fov 60 and 13.5 px
    # at fov 90, one camera and one chevron. The repeat is read over a
    # dozen arms, so the baseline is metres and blur cancels.
    bd = np.array([math.cos(math.radians(band)), math.sin(math.radians(band))])
    proj = np.sort(np.array(cents) @ bd)
    gaps = np.diff(proj)
    gaps = gaps[gaps > 0.15*PX]
    if len(gaps) < 5:
        print(f"{stem:14s} -- {len(gaps)} usable gaps between arms"); continue
    g_med = float(np.median(gaps))
    k = np.round((proj - proj[0])/g_med)
    A = np.vstack([k, np.ones_like(k)]).T
    pitch_px, _ = np.linalg.lstsq(A, proj, rcond=None)[0]
    resid = float(np.std(proj - (A @ np.linalg.lstsq(A, proj, rcond=None)[0])))
    height = ARM_PITCH/(pitch_px/PX)
    reach_m = float(np.median(reaches))/PX*height
    band_m = reach_m*math.sin(math.radians(sep))
    z = np.exp(2j*np.radians(np.array(checks)))
    remeas = abs(((math.degrees(np.angle(z.sum())/2) - band + 90) % 180) - 90)
    ok = 1.8 < height < 3.4 and abs(remeas - 45) < 15
    print(f"{stem:14s} band {band:3d} arm {arm:3d} ({sep:4.1f})  "
          f"{len(widths):2d} arms  pitch {pitch_px:6.1f} px (resid {resid:4.1f})  "
          f"height {height:5.2f} m  band {band_m:5.2f} m  "
          f"recheck {remeas:4.1f}  {'ok' if ok else 'REFUSED'}")
    rows.append({"capture": stem, "band_deg": band, "arm_deg": arm,
                 "separation_deg": round(sep, 1), "arms": len(widths),
                 "arm_width_px": round(w_px, 1),
                 "arm_pitch_px": round(float(pitch_px), 1),
                 "pitch_fit_residual_px": round(resid, 1),
                 "camera_height_m": round(height, 2),
                 "arm_reach_m": round(reach_m, 2),
                 "band_width_m": round(band_m, 2),
                 "arm_angle_recheck_deg": round(remeas, 1), "accepted": bool(ok)})

good = [r for r in rows if r["accepted"]]
print(f"\n{len(good)} of {len(rows)} captures pass both checks")
if good:
    h = np.array([r["camera_height_m"] for r in good])
    b = np.array([r["band_width_m"] for r in good])
    print(f"  camera height {h.mean():.2f} m, sd {h.std():.2f}")
    print(f"  original chevron band width {b.mean():.2f} m, sd {b.std():.2f}, "
          f"range {b.min():.2f}-{b.max():.2f}")
    if h.std() < 0.35 and b.std() < 0.35:
        print(f"\n  with 64% erased: removed {b.mean()*0.64:.2f} m, "
              f"left {b.mean()*0.36:.2f} m")
    else:
        print("\n  the captures still disagree by more than the method carries")
json.dump({"arm_width_m": ARM_W, "source": "設置規則 §171",
           "checks": ["camera height 1.8-3.4 m", "arm to band 45 +- 15 deg"],
           "captures": rows}, open("results/ipm_band_width.json", "w"),
          indent=2, ensure_ascii=False)
