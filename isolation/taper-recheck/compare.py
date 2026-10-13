"""Old taper_427 vs taper_v2 under seven perturbations per frame."""
import sys, math, glob, csv, json, cv2, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from marking import phone as P
from taper_v2 import taper_v2
FOV = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))
f20 = sorted(glob.glob("evidence/field-2026-09-20/IMG_*.jpg"))
m23 = {r["no"]: r["file"] for r in csv.DictReader(open("evidence/field-2026-09-23/MANIFEST.csv"))}
frames = [(f"F{n}", f20[n - 1]) for n in (17, 18, 19, 20, 35, 36, 37, 38, 39, 40)] + \
         [(p, "evidence/field-2026-09-23/" + m23[p]) for p in ("P62", "P63", "P64")]


def variants(im):
    yield "orig", im, 0, 0
    for q in (97, 94, 91):
        yield f"q{q}", cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, q])[1], 1), 0, 0
    for d in (8, 16, 24):
        yield f"crop{d}", im[d:, d:], d, d


out = {}
for name, f in frames:
    im = cv2.imread(f); row = {"old": [], "v2": []}
    for vn, x, dx, dy in variants(im):
        K = P.K_from_fov(im.shape[1], im.shape[0], FOV); K[0, 2] -= dx; K[1, 2] -= dy
        o = P.taper_427(x, K); v = taper_v2(x, K)
        row["old"].append(o.get("taper_ratio") if o.get("ok") else None)
        row["v2"].append(v.get("taper_ratio") if v.get("ok") else None)
    out[name] = row
    print(name, "old", row["old"], "| v2", row["v2"], flush=True)
json.dump(out, open("isolation/taper-recheck/compare_out.json", "w"), indent=1)
