"""How much of the chevron was painted out.

Each painted stripe points at its own erased continuation. Fit the stripe's
axis, walk off its end along that axis, and read the surface: where the paint
stops the imprint carries on, darker than the asphalt around it, until the
original edge of the band. Both lengths lie on one line, so their ratio is
what "佔比" means and no camera model enters it.

Four earlier attempts are named in the git history; the one worth repeating is
that an erased stripe and the gap between two painted stripes are both dark,
so darkness alone cannot separate them. Walking out from a known stripe does,
because the gaps are behind you.
"""
import cv2, numpy as np, json

SRC = "evidence/field-2026-09-20/IMG_20260920_155843.jpg"
im = cv2.imread(SRC)
H, W = im.shape[:2]
crop = cv2.resize(im[int(H*0.42):int(H*0.62), int(W*0.10):int(W*0.80)],
                  None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
h, w = crop.shape[:2]
L = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
res = L - cv2.GaussianBlur(L, (0, 0), 25)
paint = cv2.morphologyEx((res > 14).astype(np.uint8), cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

n, lbl, stats, cent = cv2.connectedComponentsWithStats(paint, 8)
strips = [i for i in range(1, n)
          if stats[i, cv2.CC_STAT_AREA] > 220
          and max(stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]) > 26]
print(f"{len(strips)} painted components above size")

def axis(i):
    ys, xs = np.nonzero(lbl == i)
    p = np.stack([xs, ys], 1).astype(np.float32)
    m = p.mean(0)
    _, _, vt = np.linalg.svd(p - m, full_matrices=False)
    d = vt[0] / np.linalg.norm(vt[0])
    proj = (p - m) @ d
    return m, d, float(proj.min()), float(proj.max())

def read(pt):
    x, y = int(round(pt[0])), int(round(pt[1]))
    if 0 <= x < w and 0 <= y < h:
        return float(res[y, x]), int(paint[y, x])
    return None, None

rows = []
for i in strips:
    m, d, lo, hi = axis(i)
    painted = hi - lo
    if painted < 26:
        continue
    for sign, end in ((+1, hi), (-1, lo)):
        run, gap, imprint = 0.0, 0, []
        s = end + sign*2
        while abs(s - end) < painted*3 + 40:
            v, isp = read(m + d*s)
            if v is None:
                break
            if isp:                      # walked into the next painted stripe
                break
            imprint.append(v)
            # the imprint reads below the local mean; asphalt sits at it
            if v < -4:
                run = abs(s - end); gap = 0
            else:
                gap += 1
                if gap > 7:
                    break
            s += sign*1.5
        rows.append({"cc": int(i), "side": "+" if sign > 0 else "-",
                     "painted_px": round(painted, 1), "imprint_px": round(run, 1),
                     "share": round(run/(painted+run), 3) if painted+run else 0.0})

good = [r for r in rows if r["imprint_px"] > 6]
print(f"{len(good)} stripe ends carry a measurable imprint, of {len(rows)} tested\n")
print(f"{'cc':>5} {'side':>5} {'painted':>8} {'imprint':>8} {'erased share':>13}")
for r in sorted(good, key=lambda r: -r["imprint_px"])[:18]:
    print(f"{r['cc']:>5} {r['side']:>5} {r['painted_px']:>8.1f} "
          f"{r['imprint_px']:>8.1f} {r['share']*100:>12.0f}%")

if good:
    sh = np.array([r["share"] for r in good])
    print(f"\nerased share of the original chevron width")
    print(f"  median {np.median(sh)*100:.0f}%   mean {sh.mean()*100:.0f}%   "
          f"sd {sh.std()*100:.0f}%   n={len(sh)}")
    print(f"  quartiles {np.percentile(sh,25)*100:.0f}% - {np.percentile(sh,75)*100:.0f}%")
json.dump({"source": SRC, "ends_tested": len(rows), "ends_with_imprint": len(good),
           "median_erased_share": round(float(np.median([r['share'] for r in good])), 3)
           if good else None, "per_end": good},
          open("results/erasure.json", "w"), indent=2)

ov = crop.copy()
ov[paint > 0] = (0.3*ov[paint > 0] + 0.7*np.array([60, 255, 60])).astype(np.uint8)
for r in good:
    m, d, lo, hi = axis(r["cc"])
    end = hi if r["side"] == "+" else lo
    sgn = 1 if r["side"] == "+" else -1
    a = m + d*end; b = m + d*(end + sgn*r["imprint_px"])
    cv2.line(ov, tuple(np.int32(a)), tuple(np.int32(b)), (60, 60, 255), 2)
__import__("os").makedirs("output/erasure", exist_ok=True); cv2.imwrite("output/erasure/erasure.png", ov)
