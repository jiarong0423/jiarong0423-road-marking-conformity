"""Telling a lane dash from a continuous line, by the population not the item.

Earlier attempts picked one component and asked whether it was 4 m. That
fails both ways: a dash broken by wear measures short, and a continuous edge
line measures long, and both are thin and straight so neither is excluded by
shape. Taking a median mixed them; taking a maximum returned the edge line.

Two tests from the lane-marking literature, and they are about the set:

  population   a family is dashes when more than half its members fall
               within +-10% of the regulated length. §182 sets that at 4 m,
               and 第02898章 holds the paint to +-5 cm over it, so the real
               spread is under 2% and a wide one means the wrong family.
  periodicity  a dashed line's profile along its own direction has a strong
               peak in the power spectrum; a continuous line has none.
               Tried once before on a frontal high-pass residual, where it
               found only noise. Here the frame is rectified and the
               direction is known, which is what it needed.

Neither is run until the scale is known, because both need metres, so the
procedure is a search: for each candidate camera height, see which one makes
the population look like §182 says it should.
"""
import glob, json, math, os, sys
import cv2
import numpy as np

sys.path.insert(0, "src")
exec(open("scripts/chord_sequence.py").read().split("rows = []")[0])

DASH_M, GAP_M = 4.0, 6.0          # §182
TOL = 0.10                        # the literature's ±10% on the regulated size


def components(bev):
    paint, cover = paint_of(bev)
    inside = cv2.erode(cover.astype(np.uint8),
                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)), 3)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(paint, 8)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 150:
            continue
        ys, xs = np.nonzero(lbl == i)
        clipped = not inside[ys, xs].all()
        p = np.stack([xs, ys], 1).astype(np.float32)
        c = p.mean(0)
        _, _, v = np.linalg.svd(p - c, full_matrices=False)
        d = v[0]/np.linalg.norm(v[0])
        if abs(d[1]) < 0.95:
            continue
        pr = (p - c) @ d
        th = float(np.abs((p - c) @ np.array([-d[1], d[0]])).max()*2)
        if th < 2:
            continue
        out.append({"len_h": float(pr.max()-pr.min())/PX,
                    "thick_h": th/PX, "x": float(c[0]), "y": float(c[1]),
                    "clipped": bool(clipped)})
    return out


pool = []
for f in sorted(glob.glob("output/seq/*.jpg")):
    meta = json.load(open(f.replace(".jpg", ".json")))
    bev = birdseye(cv2.imread(f), meta["fov"], meta["pitch"])
    got = components(bev)
    for g in got:
        g["frame"] = meta["along_m"]
    pool += got
print(f"{len(pool)} longitudinal components across {len(glob.glob('output/seq/*.jpg'))} frames, "
      f"{sum(c['clipped'] for c in pool)} clipped by the frame edge")

lens = np.array([c["len_h"] for c in pool])
unclipped = np.array([c["len_h"] for c in pool if not c["clipped"]])
print(f"lengths in camera heights: {lens.min():.2f} to {lens.max():.2f}, "
      f"{len(unclipped)} unclipped\n")

# Which camera height makes the population behave like §182 says it should?
# A clipped component can only be short, so only unclipped ones vote.
print(f"{'height':>7}{'dash len':>10}{'within ±10%':>13}{'share':>8}"
      f"{'longer (solid)':>16}")
best = None
for H in np.arange(1.6, 3.61, 0.05):
    d_h = DASH_M/H                      # a dash, in camera heights
    hit = np.abs(unclipped - d_h) <= TOL*d_h
    longer = unclipped > d_h*(1+TOL)
    share = hit.sum()/max(len(unclipped), 1)
    if best is None or hit.sum() > best[1]:
        best = (float(H), int(hit.sum()), float(share), int(longer.sum()))
    if abs(round(H, 2)*100 % 25) < 1:
        print(f"{H:>7.2f}{d_h:>10.2f}{hit.sum():>13}{share:>8.0%}{longer.sum():>16}")
H, nhit, share, nlong = best
print(f"\nbest fit: camera height {H:.2f} m - {nhit} of {len(unclipped)} "
      f"unclipped components ({share:.0%}) are a 4 m dash to ±10%")
print(f"  {nlong} are longer than that: continuous lines, correctly excluded")
if share > 0.5:
    print(f"  the literature's rule is met: over half the family is at the "
          f"regulated size, so these are dashes")
else:
    print(f"  the rule is NOT met - under half - so this family is not "
          f"cleanly dashes and the height is not established")
print(f"\n  Street View sits near 2.5 m. This says {H:.2f}.")
json.dump({"components": len(pool), "unclipped": int(len(unclipped)),
           "best_height_m": round(H, 2), "hits": nhit,
           "share_at_regulated_size": round(share, 3),
           "longer_excluded": nlong, "rule": "dashes when >50% within ±10% "
           "of the regulated 4 m (§182)"},
          open("results/dash_population.json", "w"), indent=2)
