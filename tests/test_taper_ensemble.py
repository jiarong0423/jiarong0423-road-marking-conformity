"""The ensemble must refuse before it asserts.

Measuring the taper once and quoting an endpoint-jitter uncertainty said
how precisely a chosen line could be fitted, not whether the same line
would be chosen. Re-encoding one photograph moved the answer by more than
its own size. These tests pin the refusals that discovery bought.
"""
import sys, os, math
import numpy as np
import pytest


def _scenario_steps(findings, kmh):
    """`_scenario` returns (measured, unmeasured) since G00.

    These tests assert on the measured half, which is the half that must
    be earned - but dropping the other half silently is how the
    unmeasured list ended up asserted by nothing at all, so this checks
    its shape on the way past.
    """
    from marking.situation import _scenario
    steps, unmeasured = _scenario(findings, kmh)
    assert isinstance(unmeasured, list)
    assert all(isinstance(x, str) and x for x in unmeasured)
    return steps

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from marking.situation import taper_ensemble, QUALITIES, WORK_PX


def test_blank_frame_cannot_measure():
    """Nothing in the frame must not become a reading."""
    out = taper_ensemble(np.full((600, 800, 3), 128, np.uint8), 60.0, 50.0)
    assert out["state"] == "CANNOT_MEASURE"
    assert out["readings"] == 0
    assert "why" in out


def test_noise_frame_cannot_measure():
    """Nor must texture with no structure in it."""
    rng = np.random.default_rng(7)
    im = rng.integers(0, 255, (600, 800, 3), dtype=np.uint8)
    out = taper_ensemble(im, 60.0, 50.0)
    assert out["state"] in ("CANNOT_MEASURE", "INDETERMINATE")
    if out["state"] == "CANNOT_MEASURE":
        assert out["readings"] < 3


def test_every_encoding_is_attempted():
    """The grid spans compression and resolution, because both move it."""
    out = taper_ensemble(np.full((400, 500, 3), 90, np.uint8), 60.0, 50.0)
    assert out["encodings"] == len(QUALITIES) * len(WORK_PX)
    assert len(QUALITIES) >= 3, "unanimity over fewer than 3 is not a check"
    assert len(WORK_PX) >= 3, "resolution decided the verdict; it needs votes"


def test_a_frame_that_is_all_carriageway_is_refused():
    """Noise makes the surface test claim the whole frame.

    Testing only whether carriageway() found something passed 19 of 24
    noise images. How much of the frame it claims separates them: noise
    runs 0.846-0.966 and real road photographs 0.179-0.614.
    """
    caught = 0
    for seed in range(12):
        h, w = [(600, 800), (900, 1200), (1050, 1400), (1400, 1050)][seed % 4]
        im = np.random.default_rng(seed).integers(0, 255, (h, w, 3),
                                                  dtype=np.uint8)
        out = taper_ensemble(im, 60.0, 50.0)
        if out["state"] == "CANNOT_MEASURE":
            caught += 1
    assert caught == 12, f"only {caught}/12 noise frames were refused"


def test_required_rate_follows_the_formula():
    """L = W*V^2/155, so the rate a speed demands is 155/V^2."""
    for v in (30.0, 50.0, 60.0):
        out = taper_ensemble(np.full((200, 300, 3), 128, np.uint8), 60.0, v)
        assert out["required_rate"] == pytest.approx(155.0/v**2, abs=5e-5)


def test_faster_roads_demand_gentler_tapers():
    a = taper_ensemble(np.full((200, 300, 3), 128, np.uint8), 60.0, 30.0)
    b = taper_ensemble(np.full((200, 300, 3), 128, np.uint8), 60.0, 60.0)
    assert b["required_rate"] < a["required_rate"]


def test_the_asserting_path_is_exercised():
    """The narration must survive a frame that actually asserts a taper.

    Every test here refused, so the one code path that reports a verdict
    was never run and `_scenario` kept reading keys the ensemble had
    stopped emitting. 41 of 42 photographs passed and the one that worked
    raised KeyError.
    """
    from marking.situation import _scenario, Finding

    measured = {"readings": 6, "encodings": 9, "taper_deg_spread": 13.1,
                "times_required_at_least": 1.46,
                "equivalent_kmh_at_most": 41.4, "rate_median": 0.19,
                "required_rate": 0.062}
    lines = _scenario_steps([Finding("TAPER_TOO_STEEP", "x", measured, "y")], 50.0)
    text = " ".join(lines)
    assert "41" in text, "the bound must reach the narration"
    assert "{" not in text and "None" not in text


def test_narration_survives_a_bound_without_a_rate():
    from marking.situation import _scenario, Finding
    lines = _scenario_steps([Finding("TAPER_TOO_STEEP", "x",
                               {"equivalent_kmh_at_most": 30.0}, "y")], 50.0)
    assert lines and "None" not in " ".join(lines)
