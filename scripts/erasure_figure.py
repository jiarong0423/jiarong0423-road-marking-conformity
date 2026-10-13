"""Where the chevron's edge is now, and where it was, against a fixed datum.

Fitting a free line through the stripe ends does not work: a few walks
overrun into plain asphalt and drag the fit until it lies across the band
instead of along it. That figure is in the history and it is wrong.

The band supplies its own datum. §171 puts a continuous 周圍邊線 down each
side of a 槽化線, and the one on the far side is still painted - it is the
longest component in the paint mask by a wide margin. Every stripe is
measured as a perpendicular distance from that line: out to where its paint
stops, and out to where its imprint stops. Two distances from one datum, per
stripe, so an overrun shows up as an outlier in a single number instead of
rotating a line.
"""
import cv2, numpy as np, json

SRC = "evidence/field-2026-09-20/IMG_20260920_155843.jpg"
im = cv2.imread(SRC); H, W = im.shape[:2]
crop = cv2.resize(im[int(H*0.42):int(H*0.62), int(W*0.10):int(W*0.80)],
                  None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
h, w = crop.shape[:2]
L = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
res = L - cv2.GaussianBlur(L, (0, 0), 25)
paint = cv2.morphologyEx((res > 14).astype(np.uint8), cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
n, lbl, stats, _ = cv2.connectedComponentsWithStats(paint, 8)

def axis(i):
    ys, xs = np.nonzero(lbl == i)
    p = np.stack([xs, ys], 1).astype(np.float32); m = p.mean(0)
    _, _, vt = np.linalg.svd(p - m, full_matrices=False)
    d = vt[0] / np.linalg.norm(vt[0]); pr = (p - m) @ d
    return m, d, float(pr.min()), float(pr.max())

# the datum: the longest painted component is the band's own boundary line
elong = [(max(stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]), i)
         for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 300]
elong.sort(reverse=True)
d_i = elong[0][1]
dm, dd, dlo, dhi = axis(d_i)
dn = np.array([-dd[1], dd[0]])
print(f"datum = component {d_i}, {elong[0][0]} px long, "
      f"bearing {np.degrees(np.arctan2(dd[1], dd[0])) % 180:.1f} deg")

def dist(p):
    return float((np.asarray(p, np.float32) - dm) @ dn)

rows = []
for i in range(1, n):
    if i == d_i:
        continue
    a = stats[i, cv2.CC_STAT_AREA]
    span = max(stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT])
    # the near stripes are large simply because they are near; cutting on area
    # threw them away, and they carry the clearest imprint in the frame. The
    # boundary lines are excluded by how long they run, not how much they cover.
    if a < 220 or span > 0.6 * elong[0][0]:
        continue
    m, d, lo, hi = axis(i)
    if hi - lo < 26:
        continue
    # the stripe end that lies further from the datum is the one facing the
    # traffic lane, and that is the side the erasure is on
    ends = sorted([(abs(dist(m + d*lo)), lo, -1), (abs(dist(m + d*hi)), hi, +1)])
    _, end, sign = ends[-1]
    run, gap, s = 0.0, 0, end + sign*2
    while abs(s - end) < (hi-lo)*3 + 40:
        pt = m + d*s; x, y = int(round(pt[0])), int(round(pt[1]))
        if not (0 <= x < w and 0 <= y < h) or paint[y, x]:
            break
        if res[y, x] < -4:
            run = abs(s - end); gap = 0
        else:
            gap += 1
            if gap > 7:
                break
        s += sign*1.5
    if run <= 6:
        continue
    rows.append({"cc": int(i),
                 "now_px": round(abs(dist(m + d*end)), 1),
                 "was_px": round(abs(dist(m + d*(end + sign*run))), 1),
                 "p_now": (m + d*end), "p_was": (m + d*(end + sign*run))})

now = np.array([r["now_px"] for r in rows])
was = np.array([r["was_px"] for r in rows])
share = (was - now) / was
# an overrun is a stripe whose imprint reaches far past the rest; cut at the
# robust 3-sigma of the distance, not at a number chosen to suit the answer
med, mad = np.median(was), np.median(np.abs(was - np.median(was)))
keep = np.abs(was - med) < 3*1.4826*max(mad, 1e-6)
print(f"{len(rows)} stripes measured, {int(keep.sum())} within 3 robust sigma "
      f"of the imprint edge\n")
print(f"{'cc':>5} {'edge now':>9} {'edge was':>9} {'erased':>8}")
for r, k in zip(rows, keep):
    print(f"{r['cc']:>5} {r['now_px']:>9.1f} {r['was_px']:>9.1f} "
          f"{(1-r['now_px']/r['was_px'])*100:>7.0f}%{'' if k else '   (outlier)'}")
s = share[keep]
print(f"\nband width to the datum: now {now[keep].mean():.0f} px, "
      f"was {was[keep].mean():.0f} px")
print(f"erased share of the original width: median {np.median(s)*100:.0f}%  "
      f"mean {s.mean()*100:.0f}%  sd {s.std()*100:.0f}%  n={int(keep.sum())}")

fig = crop.copy()
ov = fig.copy(); ov[paint > 0] = (0.25*ov[paint > 0] + 0.75*np.array([90, 255, 90])).astype(np.uint8)
fig = cv2.addWeighted(ov, .8, fig, .2, 0)
a = tuple(np.int32(dm + dd*dlo)); b = tuple(np.int32(dm + dd*dhi))
cv2.line(fig, a, b, (255, 210, 60), 3, cv2.LINE_AA)
for r, k in zip(rows, keep):
    col = (70, 255, 255) if k else (150, 150, 150)
    cv2.line(fig, tuple(np.int32(r["p_now"])), tuple(np.int32(r["p_was"])), (80, 80, 255) if k else col, 2, cv2.LINE_AA)
    cv2.circle(fig, tuple(np.int32(r["p_now"])), 4, (70, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(fig, tuple(np.int32(r["p_was"])), 4, (80, 80, 255), -1, cv2.LINE_AA)
cv2.rectangle(fig, (0, 0), (w, 62), (0, 0, 0), -1)
cv2.putText(fig, "blue datum = 周圍邊線 still painted   yellow dot = paint ends   "
                 "red dot = imprint ends", (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX, .56, (255, 255, 255), 2, cv2.LINE_AA)
cv2.putText(fig, f"erased {np.median(s)*100:.0f}% of the original band width  "
                 f"(median, n={int(keep.sum())}, sd {s.std()*100:.0f}%)   F17 2026-09-20",
            (10, 50), cv2.FONT_HERSHEY_SIMPLEX, .54, (170, 220, 255), 1, cv2.LINE_AA)
S = "output/erasure/"   # output/ is not in git
import os; os.makedirs(S, exist_ok=True)
cv2.imwrite(S + "difference.png", np.vstack([crop, fig]))
json.dump({"source": SRC, "datum_cc": int(d_i), "n_stripes": int(keep.sum()),
           "width_now_px": round(float(now[keep].mean()), 1),
           "width_was_px": round(float(was[keep].mean()), 1),
           "erased_share_median": round(float(np.median(s)), 3),
           "erased_share_sd": round(float(s.std()), 3)},
          open("results/erasure_edges.json", "w"), indent=2)
