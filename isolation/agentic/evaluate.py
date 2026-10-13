"""Agentic Vision evaluation over all 106 evidence photos (full resolution).

For each photo: assess() state, findings, measurement states, and the next actions.
Summarises how often each action is produced, how often the system refuses, and
whether every action carries a reason. Writes output/agentic/evaluate.json.

    /opt/anaconda3/bin/python3 -B isolation/agentic/evaluate.py [N]   # N per batch, evenly spaced; omit for all 106
"""
import json, math, sys, time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
FOV = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))


def one(p):
    import cv2
    sys.path.insert(0, str(ROOT / "src"))
    from marking.situation import assess
    cv2.setNumThreads(1)
    t = time.time(); r = assess(cv2.imread(str(p)), FOV, 30.0)
    return {"file": p.name, "batch": p.parent.name, "seconds": round(time.time() - t, 1),
            "state": r.get("state", "ASSESSED"), "findings": [f["code"] for f in r.get("findings", [])],
            "red_line_gap": (r.get("red_line_gap") or {}).get("state"),
            "taper_table_4_2_7": (r.get("taper_table_4_2_7") or {}).get("state"),
            "actions": [a["action"] for a in r["next_actions"]],
            "every_action_has_why": all(a["why"].strip() for a in r["next_actions"])}


if __name__ == "__main__":
    a = sorted((ROOT / "evidence/field-2026-09-20").glob("IMG_*.jpg")); b = sorted((ROOT / "evidence/field-2026-09-23").glob("IMG_*.jpg"))
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 0          # 0 = all 106; N = every k-th photo, N per batch
    photos = (a + b) if not n else (a[::max(1, len(a) // n)][:n] + b[::max(1, len(b) // n)][:n])
    with Pool(4) as pool:
        rows = pool.map(one, photos)
    acts = Counter(a for r in rows for a in set(r["actions"]))
    summary = {"photos": len(rows),
               "not_a_road": sum(r["state"] == "NOT_A_ROAD_PHOTOGRAPH" for r in rows),
               "red_line_gap_measured": sum(r["red_line_gap"] == "MEASURED" for r in rows),
               "taper_427_reported": sum(r["taper_table_4_2_7"] not in (None, "CANNOT_MEASURE") for r in rows),
               "photos_with_action": dict(acts),
               "distinct_action_sets": len({tuple(sorted(set(r["actions"]))) for r in rows}),
               "every_action_has_why": all(r["every_action_has_why"] for r in rows),
               "median_seconds": sorted(r["seconds"] for r in rows)[len(rows) // 2]}
    (ROOT / "output/agentic").mkdir(parents=True, exist_ok=True)
    (ROOT / "output/agentic/evaluate.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))
