#!/usr/bin/env python3
"""How many seconds a motorcycle has to get across, from the figures already held.

Nothing here is measured; it is arithmetic on results/solid_line_extent.json
and results/reaction.json, written down so the story's seconds have a
source like its metres do.

The rider cannot pass on the right (red line, drain covers - REDLINE.md)
and cannot cross the solid line on the left (§167, 0-35.5 m). The only
legal place to move left is the taper, 35.5-85 m, and the lane there is
closing. So the window is the taper's length divided by speed, minus the
reaction time the project already uses.

    /opt/anaconda3/bin/python3 scripts/merge_window.py --write
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); a = ap.parse_args()
    ext = json.loads((ROOT / "results/solid_line_extent.json").read_text())["extents"]
    rx = json.loads((ROOT / "results/reaction.json").read_text())
    # results/reaction.json is WITHDRAWN for its taper rate; its piev_s is
    # the AASHTO perception-reaction constant, 2.5 s, which the withdrawal
    # does not touch. Read that key by name, and refuse rather than default
    # if it is missing - a default here would be E56's shape again.
    if "piev_s" not in rx:
        sys.exit("results/reaction.json has no piev_s; not defaulting")
    t_react = float(rx["piev_s"])
    s0, s1, s2 = ext["double_white_start_m"], ext["chevron_start_m"], ext["bridge_head_m"]
    rows = []
    for kmh in (30, 40, 50, 60):
        v = kmh / 3.6
        solid, taper = (s1 - s0) / v, (s2 - s1) / v
        rows.append({"kmh": kmh, "solid_s": round(solid, 1), "taper_s": round(taper, 1),
                     "window_after_reaction_s": round(taper - t_react, 1),
                     "lane_closing_cm_per_s_if_3m": round(300 / taper)})
    out = {"inputs": {"double_white_start_m": s0, "chevron_start_m": s1, "bridge_head_m": s2, "reaction_s": t_react,
                      "sources": ["results/solid_line_extent.json", "results/reaction.json#/piev_s (the file is withdrawn for its taper rate, not for this constant)"]},
           "assumption": "the rider may only move left inside the taper; the solid line forbids it before (§167) and the "
                         "right side is closed by the red line and drain covers. Lane width 3 m only for the closing rate.",
           "rows": rows,
           "reading": "at 50 km/h the taper lasts 3.6 s, of which reaction takes 2.5: about one second to decide and move"}
    for r in rows:
        print(f"  {r['kmh']} km/h: 實線 {r['solid_s']} s, 槽化線 {r['taper_s']} s, 扣反應剩 {r['window_after_reaction_s']} s, 車道每秒縮 {r['lane_closing_cm_per_s_if_3m']} cm")
    if a.write:
        (ROOT / "results/merge_window.json").write_text(json.dumps(out, ensure_ascii=False, indent=1)); print("  寫入 results/merge_window.json")

if __name__ == "__main__":
    main()
