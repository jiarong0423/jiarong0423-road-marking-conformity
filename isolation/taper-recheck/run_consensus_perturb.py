import sys, math, glob, json, cv2
sys.path.insert(0, "src"); sys.path.insert(0, "isolation/taper-recheck")
from marking import phone as P
from consensus import run
FOV = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))
f = sorted(glob.glob("evidence/field-2026-09-20/IMG_*.jpg"))
for fr in (17, 40):
    im = cv2.imread(f[fr - 1])
    for vn, dx in [("orig", 0), ("q97", 0), ("q94", 0), ("q91", 0), ("crop8", 8), ("crop16", 16), ("crop24", 24)]:
        x = im[dx:, dx:] if dx else (im if vn == "orig" else cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, int(vn[1:])])[1], 1))
        K = P.K_from_fov(im.shape[1], im.shape[0], FOV); K[0, 2] -= dx; K[1, 2] -= dx
        r = run(x, K)
        print(f"F{fr} {vn:6}", "OK " if r.get("ok") else "-- ", r.get("taper_ratio"), r.get("taper_deg"),
              "arm-edge", r.get("arm_to_edge_a_deg"), "|", {k: r[k] for k in ("side_a", "side_b") if k in r}, r.get("why", ""), flush=True)
