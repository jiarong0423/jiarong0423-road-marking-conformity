"""Agentic Vision evidence: the vision result changes what the system does next.

Runs assess() (the endpoint's own function) on a few inputs chosen to differ in what
they show, and records for each: the OpenCV findings and measurement states, and the
next actions they produced. Writes output/agentic/trace.json and prints a table.

    /opt/anaconda3/bin/python3 -B isolation/agentic/trace.py
"""
import json, math, sys, time
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from marking.situation import assess

FOV = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))
f20 = sorted((ROOT / "evidence/field-2026-09-20").glob("IMG_*.jpg"))
CASES = [
    ("random noise (not a road)", np.random.default_rng(0).integers(0, 255, (900, 1200, 3), dtype=np.uint8)),
    ("F31 full size: two red lines", cv2.imread(str(f20[30]))),
    ("F31 downscaled to 2000 px", cv2.resize(cv2.imread(str(f20[30])), (1500, 2000), interpolation=cv2.INTER_AREA)),
    ("F40 full size: island + double white line", cv2.imread(str(f20[39]))),
]
out = []
for name, img in CASES:
    t = time.time(); r = assess(img, FOV, 30.0); dt = time.time() - t
    rec = {"input": name, "seconds": round(dt, 1), "state": r.get("state", "ASSESSED"),
           "findings": [f["code"] for f in r.get("findings", [])],
           "red_line_gap": (r.get("red_line_gap") or {}).get("state"),
           "gap_m": (r.get("red_line_gap") or {}).get("gap_m"),
           "taper_table_4_2_7": (r.get("taper_table_4_2_7") or {}).get("state"),
           "next_actions": [{"action": a["action"], "what": a["what"], "why": a["why"], "to": a["to"]} for a in r["next_actions"]]}
    out.append(rec)
    print(f"\n== {name}  ({dt:.1f} s)  findings={rec['findings']}  red_line_gap={rec['red_line_gap']} {rec['gap_m']}")
    for a in rec["next_actions"]:
        print(f"   {a['action']:18} {a['what'][:40]}")
(ROOT / "output/agentic").mkdir(parents=True, exist_ok=True)
(ROOT / "output/agentic/trace.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
