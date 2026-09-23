"""The three fixes of 2026-09-22, each of which shipped with no test.

A mutation run by the verifying agent reverted all three and the suite
stayed at 137 passed / 2 skipped. Not vacuous tests - no tests. The
commit message said "139 passed" about a suite that had no opinion on
any of the three things it had just changed.

Each test here is written so that reverting its subject fails it, and
the comment on each says what to revert.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marking.situation import Finding, _scenario  # noqa: E402

W = 3072


def _f(code, measured, basis="x"):
    return Finding(code, "x", measured, basis)


DW = {"length_px": 500.0, "gap_px": 24.0, "colour": "white", "section": "167"}
NARROW = {"lane_width_m": 3.0, "need_car_m": 3.03, "need_heavy_m": 3.75}


# ---- 1. the closing line counts findings, not steps -----------------
#
# Revert: `if len(findings) >= 3` -> `if len(steps) >= 3` in _scenario.
# §167 is narrated in two steps, so on one finding the product said
# 「這兩項是同一張照片裡同時量到的」.

def test_the_closing_line_counts_findings_not_sentences():
    steps, _ = _scenario([_f("NO_LANE_CHANGE", DW)], 50.0, image_w=W)
    joined = "".join(steps)
    assert "兩項" not in joined and "這 3 項" not in joined, (
        "one finding, and the narration announced more than one: " + joined)


def test_two_findings_say_two():
    steps, _ = _scenario([_f("NO_LANE_CHANGE", DW),
                          _f("LANE_TOO_NARROW", NARROW)], 50.0, image_w=W)
    assert "這兩項" in steps[-1], steps[-1]


def test_three_findings_say_three():
    steps, _ = _scenario([_f("NO_LANE_CHANGE", DW),
                          _f("LANE_TOO_NARROW", NARROW),
                          _f("SURFACE_IN_PIECES", {"surface_types": 4})],
                         50.0, image_w=W)
    assert "這 3 項" in steps[-1], steps[-1]


# ---- 2. the side comes from the measurement -------------------------
#
# Revert: the `side` expression -> a literal "右".
# The red line is left of frame centre on 10 of the 25 frames that fire;
# F14 said 「往右邊看」 about a box starting at x=0.

# `px` is [x, y, w, h] - a LIST. The first version of this test used a
# dict, which the detector never produces, so it passed while the code
# raised AttributeError on all 25 frames where the red line fires. The
# shapes below are copied from real output: F14 is [0, 2247, 843, 381].
@pytest.mark.parametrize("box,want", [
    ([0, 2247, 843, 381], "左"),          # F14, verbatim
    ([2600, 2200, 400, 300], "右"),
    ([W // 2, 100, 10, 10], "右"),
])
def test_the_side_follows_the_bounding_box(box, want):
    steps, _ = _scenario(
        [_f("EDGE_NOT_CARRIAGEWAY", {"run_px": 874.0, "px": box})],
        50.0, image_w=W)
    other = "右" if want == "左" else "左"
    assert f"往{want}" in steps[0], steps[0]
    assert f"往{other}" not in steps[0], steps[0]


def test_the_real_detector_shape_does_not_raise():
    """The regression that the dict-shaped test hid.

    Guarding the shape, not the value: any box the detector can emit
    must narrate rather than raise.
    """
    for box in ([0, 2247, 843, 381], [10, 20], None, {"x": 5, "w": 10}):
        steps, _ = _scenario(
            [_f("EDGE_NOT_CARRIAGEWAY", {"run_px": 874.0, "px": box})],
            50.0, image_w=W)
        assert steps, f"no narration for px={box!r}"


# ---- 3. §165 is not §167 --------------------------------------------
#
# Revert: delete the `section == "165"` branch so both fall through to
# NO_LANE_CHANGE. A double YELLOW line then tells a rider they may not
# change lanes, on the strength of a clause about opposing traffic.

YELLOW = dict(DW, colour="yellow", section="165")


# The §165 decision is made in `assess()`, not in `_scenario`. The first
# version of these two tests handed `_scenario` a CENTRE_LINE_SOLID
# finding and checked the narration - which passes whether or not the
# branch exists, because `_scenario` has no branch for that code at all.
# The mutation check caught it: removing the §165 branch from `assess()`
# left all nine tests green. These call `assess()` with the detector
# replaced, which is where the decision actually is.

def _assess_with_double_line(monkeypatch, dw):
    import numpy as np
    from marking import situation as S
    monkeypatch.setattr(S, "_double_white", lambda *a, **k: dw)
    monkeypatch.setattr(S, "_kerbside_red", lambda *a, **k: None)
    monkeypatch.setattr(S, "_works_hoarding", lambda *a, **k: None)
    monkeypatch.setattr(S, "_surface_types", lambda *a, **k: [])
    monkeypatch.setattr(S, "taper_ensemble",
                        lambda *a, **k: {"state": "CANNOT_MEASURE",
                                         "why": "stubbed", "readings": 0})
    monkeypatch.setattr(S, "road_region",
                        lambda *a, **k: np.full((800, 600), 255, np.uint8))
    monkeypatch.setattr(S, "_segments", lambda *a, **k: ([], None))
    return S.assess(np.zeros((800, 600, 3), np.uint8), 60.0, 50.0)


def test_a_double_yellow_line_is_not_reported_as_no_lane_change(monkeypatch):
    out = _assess_with_double_line(monkeypatch, YELLOW)
    codes = [f["code"] for f in out["findings"]]
    assert "NO_LANE_CHANGE" not in codes, (
        "a 雙黃實線 was reported as §167 禁止變換車道: " + str(codes))
    assert codes == ["CENTRE_LINE_SOLID"], codes
    # Assert the CLAIM, not the wording. An earlier version pinned the
    # exact phrase 「不是 §167」, and when the basis was rewritten for
    # E37 - the §165 text was invented and had to be withdrawn - this
    # test failed on correct code and was committed red. A test that
    # pins prose breaks whenever the prose is corrected.
    basis = out["findings"][0]["basis"]
    assert "§165" in basis
    assert "禁止變換車道" not in out["findings"][0]["what"]
    assert "§167" in basis and "不適用" in basis, (
        "the finding must say §167 does not apply, in whatever words: "
        + basis)


def test_a_double_white_line_still_is_no_lane_change(monkeypatch):
    out = _assess_with_double_line(monkeypatch, DW)
    codes = [f["code"] for f in out["findings"]]
    assert codes == ["NO_LANE_CHANGE"], codes
    assert "§167" in out["findings"][0]["basis"]


# ---- surface count: a seeded draw, and it says so ------------------


def test_the_surface_count_does_not_claim_a_stability_nobody_checked():
    """ER01. `surface_types_stable(runs=1)` used to return True for the
    stability flag, so `assess()`'s "the clustering is unstable" branch
    could never fire - a guard written and disabled in consecutive
    edits, E07's shape a fifth time.

    runs=1 now returns None, meaning not assessed, and the response
    says so under not_checked.
    """
    import numpy as np
    from marking.situation import surface_types_stable

    roi = np.full((800, 600), 255, np.uint8)
    img = np.random.default_rng(3).integers(0, 255, (800, 600, 3),
                                            dtype=np.uint8)
    count, stable = surface_types_stable(img, roi, runs=1)
    assert stable is None, (
        "runs=1 checked nothing and reported a stability anyway")
    if count is not None:
        c2, s2 = surface_types_stable(img, roi, runs=5)
        assert s2 in (True, False), "runs>1 must reach a verdict"


def test_an_admitted_frame_says_the_spread_is_unmeasured():
    import numpy as np
    from marking.situation import assess

    out = assess(np.full((900, 1200, 3), 128, np.uint8), 60.0, 50.0)
    assert out.get("state") != "NOT_A_ROAD_PHOTOGRAPH"
    surface = [x for x in out["not_checked"] if x.startswith("surface")]
    assert surface, "the response does not say the spread is unmeasured"
    assert "沒有量" in surface[0] or "尚未量測" in surface[0]
