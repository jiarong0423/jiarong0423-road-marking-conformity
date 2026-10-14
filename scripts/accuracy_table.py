#!/usr/bin/env python3
"""How accurate is it? Every check this project has, gathered from the result files that hold it.

There is no surveyed ground truth for this road. What there is:
  1. sizes fixed by law or by a standard, measured back with the same method (the only truth available)
  2. the same thing measured on different photographs (repeatability)
  3. the same photograph re-saved (stability under JPEG re-encoding)
  4. assess(), the function behind the online service, on 20 photographs at full resolution
     (how often it refuses, and whether each refusal says why)

Nothing is measured here; this only reads results/ and isolation/ files and writes
results/accuracy_table.json, which docs/accuracy.md quotes.

    python3 -B scripts/accuracy_table.py
"""
import json
import os
from collections import defaultdict

R = lambda p: json.load(open(p, encoding="utf-8"))
out = {"date": "2026-10-14", "no_surveyed_ground_truth": True}

# 1. against a size fixed by law or by a standard
card = R("isolation/field-2026-09-23/card_vs_redline.json")
tri = R("results/erased_triangle_P64.json")
dash = R("results/dash_ruler_P64.json")
out["against_a_known_size"] = {
    "red_line_width_with_a_card": {
        "known": "red line 100 mm wide (設置規則 §169); scale from an ID-1 card, 85.60 mm (ISO/IEC 7810)",
        "source": "isolation/field-2026-09-23/card_vs_redline.json",
        "frames": {c["frame"]: c["median_mm"] for c in card},
        "error_pct": {c["frame"]: round(100 * (c["median_mm"] - 100) / 100, 1) for c in card if c["median_mm"] > 50},
        "failed": [c["frame"] for c in card if c["median_mm"] <= 50],
    },
    "lane_dash_in_the_top_down_view": {
        "known": "lane dash 4 m (設置規則 §182)", "source": "results/erased_triangle_P64.json ruler",
        "measured_m": tri["ruler"]["first_dash_length_m"],
        "error_pct": round(100 * (tri["ruler"]["first_dash_length_m"] - 4) / 4, 1),
    },
    "dash_spacing_used_as_the_ruler": {
        "known": "dash + gap = 10 m (§182)", "source": "results/dash_ruler_P64.json subsets",
        "spacing_spread_pct": [s["dash_spacing_spread_pct"] for s in dash["subsets"].values()],
        "metres_per_plan_unit": [s["metres_per_plan_unit"] for s in dash["subsets"].values()],
    },
}

# 2. the same thing on different photographs
gaps = {f: R(f"results/redline_gap_{f}.json")["summary"]["median_m"] for f in ("F30", "F31", "F32")}
grates = defaultdict(list)
for g in R("results/grate_crossings_2026-09-23.json"):
    grates[g["group"]].append({"frame": g["frame"], "red_axis_to_grate_centre_cm": g["red_axis_to_grate_centre_cm"],
                               "grate_w_cm": g["grate_cm"]["w"], "grate_h_cm": g["grate_cm"]["h"]})
multi = {k: v for k, v in grates.items() if len(v) > 1}
spread = lambda xs: round(max(xs) - min(xs), 1)
out["same_thing_different_photographs"] = {
    "red_line_gap_m": {"source": "results/redline_gap_F30.json .. F32.json", "medians": gaps,
                       "range_m": round(max(gaps.values()) - min(gaps.values()), 3)},
    "red_axis_to_grate_centre_cm": {
        "source": "results/grate_crossings_2026-09-23.json", "per_grate": multi,
        "spread_cm": {k: spread([x["red_axis_to_grate_centre_cm"] for x in v]) for k, v in multi.items()},
        "max_spread_cm": max(spread([x["red_axis_to_grate_centre_cm"] for x in v]) for v in multi.values()),
    },
    "grate_size_cm_not_repeatable": {
        "max_spread_w_cm": max(spread([x["grate_w_cm"] for x in v]) for v in multi.values()),
        "note": "the box found around a grate changes size between photographs, so grate sizes are not published; the offset of the red line from the grate centre is",
    },
    "old_end_angle_deg": {"source": "results/dash_ruler_P64.json", "across_ruler_subsets": dash["slanted_end_edge"]["angle_range_deg"],
                          "monte_carlo_p10_p90": [dash["monte_carlo"]["angle_deg"]["p10"], dash["monte_carlo"]["angle_deg"]["p90"]],
                          "note": "one photograph (P64); the spread is from the ruler and from perturbing the points a person gave"},
}


# 3. the same photographs, re-saved: assess() before and after the plate masks re-encoded them
def codes(p):
    return {x["no"]: sorted(x["codes"]) for x in R(p)["photographs"]}


def compare(before, after):
    a, b = codes(before), codes(after); common = sorted(set(a) & set(b))
    changed = {n: {"before": a[n], "after": b[n]} for n in common if a[n] != b[n]}
    return {"photographs": len(common), "unchanged": len(common) - len(changed), "changed": changed}


out["same_photograph_re_saved"] = {
    "what": "assess() on the photographs before and after the plate masks were added (re-encoded once, pixels outside the masks changed by 0.047 grey levels on average)",
    "at_50_kmh": compare("results/assess_2026-09-22.json", "results/assess_2026-10-13_post_redaction_23.json"),
    "at_30_kmh": compare("results/assess_2026-09-22_kmh30.json", "results/assess_2026-10-13_post_redaction_kmh30_23.json"),
    "online_gate": "the online service measures the bytes as received and three light re-encodes (JPEG 97/94/91) and reports a number only if at least 3 of the 4 agree (src/marking/phone.py)",
}

# 4. what assess(), the function behind the online service, does with 20 photographs
ev = R("results/agentic_evaluate_2026-09-23.json")["summary"]
out["assess_on_20_photographs"] = {"source": "results/agentic_evaluate_2026-09-23.json (isolation/agentic/evaluate.py: full resolution, 30 km/h, evenly spaced over both field days)", **ev}

with open("results/accuracy_table.json.tmp", "w", encoding="utf-8") as fh:
    fh.write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
os.replace("results/accuracy_table.json.tmp", "results/accuracy_table.json")
print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
