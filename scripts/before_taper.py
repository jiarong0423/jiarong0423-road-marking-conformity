"""How much of the island was painted over, from the owner's own photograph.

No Street View. The inputs are F17 (a field photograph), the chevron's former edge
drawn by the site owner on it (OpenCV could not see that edge), the paint that is
still there, and the taper measured today on F40.

An earlier version also scaled today's taper back to a "before" ratio,
assuming the share painted over is the same all along the island. It is not
(it differs between the island's start and this frame), so no before ratio is
given; the key below says so instead of carrying a number.

Stripes that overran the band (the paint end falls outside the datum..drawn-edge
interval) are dropped: they are wrong measurements, found on 2026-10-13 by
drawing every stripe on the photograph.

    /opt/anaconda3/bin/python3 -B scripts/before_taper.py       (writes results/before_taper.json)
"""
import json, numpy as np

E = json.load(open("results/erasure_ratio.json"))
rows = E["per_stripe"]
e = np.array([r["erased"] for r in rows])
b = np.array([r["b_along"] for r in rows])
med, mad = np.median(e), np.median(np.abs(e - np.median(e)))
robust = np.abs(e - med) < 3 * 1.4826 * max(mad, 1e-3)          # the rule erasure_ratio.py applies
clean = robust & (b > 0.02) & (b < 0.98)
x = e[clean]

# F40, taper today, the 2026-09-23 consensus run (isolation/taper-recheck/NOTES.md, F40 row):
AFTER = {"median": 12.1, "min": 11.7, "max": 12.3,
         "source": "isolation/taper-recheck/NOTES.md, F40: about 12:1 (11.7-12.3), 6 of 7 variations; not re-run here"}
# displacing the hand-drawn edge +-20 px moves the erased share to 54.9%-68.3%
# (docs/status-2026-09-20.md, section on the 64% erasure); not re-run here
EDGE = {"erased_min": 0.549, "erased_max": 0.683}

ext = np.array([r["visible_extent_widths"] for r in rows])[clean]
who = {
    "done_by_opencv_5": "paint mask (LAB, blur, morphology), connected components for the stripes and the far edge line, "
                        "line fits and the cross-ratio against the vanishing point, the stripe-by-stripe ground distances",
    "done_by_a_person": "the chevron's former edge was drawn by the site owner on the photograph (OpenCV could not find it: seven "
                        "attempts are written up in docs/thesis.md); that the rough surface beyond it is milled carriageway is "
                        "the owner's statement; whether the drawn edge is the chevron's or the milling boundary is unresolved",
    "not_done": ["detecting the former edge", "detecting milled asphalt (a texture test separated nothing)",
                 "the far edge of the milled surface (the photograph ends first, so the milled layer is a lower bound)",
                 "any distance in metres (no object of known size in the frame)"],
}
out = {
    "who_did_what": who,
    "inputs": {"erasure": "results/erasure_ratio.json", "after_ratio": AFTER, "drawn_edge_sensitivity": EDGE},
    "stripes": {"cut_all_three_lines": int(len(rows)), "kept_by_robust_rule": int(robust.sum()),
                "overran_the_band": int((robust & ~clean).sum()), "clean": int(clean.sum())},
    "erased_share": {"median": round(float(np.median(x)), 3), "mean": round(float(x.mean()), 3),
                     "sd": round(float(x.std()), 3),
                     "q25": round(float(np.percentile(x, 25)), 3), "q75": round(float(np.percentile(x, 75)), 3)},
    "layers_in_old_island_widths": {
        "still_painted": round(1 - float(np.median(x)), 3),
        "painted_over": round(float(np.median(x)), 3),
        "milled_surface_visible_beyond_drawn_edge_at_least": round(float(np.median(ext)) - 1, 2),
        "note": "unit is the ground width from the far edge line to the drawn former edge; the third figure is how far the photograph shows road beyond that edge, not a measurement of the milled surface itself",
    },
    "before_ratio": "not given: the share painted over is not uniform along the island, so today's ratio cannot be scaled back to the old one",
}
json.dump(out, open("results/before_taper.json", "w"), indent=2)
print(json.dumps(out["stripes"]), json.dumps(out["erased_share"]))
