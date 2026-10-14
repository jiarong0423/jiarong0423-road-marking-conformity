"""docs/accuracy.md quotes results/accuracy_table.json; a number there must still be the number here."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = json.loads((ROOT / "results/accuracy_table.json").read_text(encoding="utf-8"))
DOC = (ROOT / "docs/accuracy.md").read_text(encoding="utf-8")


def test_known_sizes_are_quoted_as_recorded():
    card = T["against_a_known_size"]["red_line_width_with_a_card"]
    for frame, mm in card["frames"].items():
        assert f"{mm} mm" in DOC, frame
    for frame, pct in card["error_pct"].items():
        assert f"{pct:+.1f} %".replace("-", "−") in DOC, frame
    dash = T["against_a_known_size"]["lane_dash_in_the_top_down_view"]
    assert f"{dash['measured_m']} m" in DOC and f"+{dash['error_pct']} %" in DOC


def test_repeat_photographs_are_quoted_as_recorded():
    rep = T["same_thing_different_photographs"]
    gaps = rep["red_line_gap_m"]["medians"]
    assert ", ".join(f"{gaps[f]:.3f}" for f in ("F30", "F31", "F32")) in DOC
    grates = rep["red_axis_to_grate_centre_cm"]
    for group, rows in grates["per_grate"].items():
        assert ", ".join(str(r["red_axis_to_grate_centre_cm"]) for r in rows) + " cm" in DOC, group
    assert f"within {grates['max_spread_cm']} cm" in DOC
    assert f"{rep['grate_size_cm_not_repeatable']['max_spread_w_cm']} cm apart" in DOC


def test_re_saved_counts_are_quoted_as_recorded():
    for kmh, key in (("30", "at_30_kmh"), ("50", "at_50_kmh")):
        r = T["same_photograph_re_saved"][key]
        assert f"| {kmh} km/h | {r['unchanged']} of {r['photographs']} |" in DOC
        for no in r["changed"]:
            assert no in DOC


def test_refusals_are_quoted_as_recorded():
    a = T["assess_on_20_photographs"]
    assert a["photos"] == 20 and f"{a['red_line_gap_measured']} of 20" in DOC
    assert f"{a['photos_with_action']['HUMAN_LOOK']} of 20" in DOC
    assert f"{a['median_seconds']} s" in DOC
