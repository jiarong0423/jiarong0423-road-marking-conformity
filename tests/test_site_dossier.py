"""The 116 site block, the encoding probe, and the two new measurements.

Added 2026-09-23 with the wiring of red_line_gap and taper_table_4_2_7
into assess(). The site block is attached to every response by the
owner's decision; these tests keep it equal to results/ and keep it
labelled as not measured from the caller's photograph.
"""
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from marking import phone                      # noqa: E402
from marking.actions import next_actions       # noqa: E402
from marking.site_116 import SITE_116          # noqa: E402
from marking.situation import assess           # noqa: E402
import build_site_dossier                      # noqa: E402

GREY = np.full((900, 1200, 3), 128, np.uint8)
NOISE = np.random.default_rng(0).integers(0, 255, (900, 1200, 3), dtype=np.uint8)
# 24 mm-equivalent on the 3072-wide portrait frames: 2 atan(1536 / 2840)
FOV_24MM = 2 * math.degrees(math.atan(1536 / (24 * math.hypot(3072, 4096) / 43.267)))


def test_the_frozen_site_block_equals_results():
    assert SITE_116 == build_site_dossier.build(), (
        "src/marking/site_116.py has drifted from results/; "
        "rerun scripts/build_site_dossier.py")


def test_the_site_block_says_it_was_not_measured_here_and_where_each_number_is():
    assert SITE_116["measured_from_this_photograph"] is False
    for item in SITE_116["items"]:
        assert item["source"].startswith("results/"), item


def test_every_response_carries_the_site_block_even_a_refused_one():
    for img in (GREY, NOISE):
        out = assess(img, 60.0, 50.0)
        assert out["site_116_not_measured_from_this_photograph"] is SITE_116


def test_the_taper_figure_carries_its_encoding_instability():
    taper = [i for i in SITE_116["items"] if "漸變率" in i["what"]][0]
    assert "23.2" in taper["stability"], "the 2026-09-23 instability is not stated"


def test_the_probe_refuses_readings_that_move_with_encoding():
    calls = iter([10.0, 20.0, 12.0, 15.0])
    fake = lambda img, K: {"ok": True, "v": next(calls)}        # noqa: E731
    _, pr = phone.encoding_probe(fake, GREY, np.eye(3), lambda o: o["v"], rel_tol=0.10)
    assert pr["stable"] is False and "spread" in pr["why"]


def test_the_probe_accepts_readings_that_agree():
    fake = lambda img, K: {"ok": True, "v": 0.66}               # noqa: E731
    _, pr = phone.encoding_probe(fake, GREY, np.eye(3), lambda o: o["v"], abs_tol=0.05)
    assert pr["stable"] is True and pr["median"] == 0.66


def test_the_probe_refuses_when_too_few_encodings_measure():
    fake = lambda img, K: {"ok": False, "why": "nothing"}       # noqa: E731
    _, pr = phone.encoding_probe(fake, GREY, np.eye(3), lambda o: 1.0, abs_tol=0.05)
    assert pr["stable"] is False and "0 of 4" in pr["why"]


def test_the_red_line_documents_appear_only_when_the_gap_was_measured():
    quiet = next_actions({"findings": [], "taper": {"state": "CANNOT_MEASURE"},
                          "red_line_gap": {"state": "CANNOT_MEASURE", "why": "x"}})
    assert not [a for a in quiet if "竣工" in a["what"] or "核定函" in a["what"]]
    measured = next_actions({"findings": [{"code": "TWO_RED_LINES", "measured": {}}],
                             "taper": {"state": "CANNOT_MEASURE"},
                             "red_line_gap": {"state": "MEASURED", "gap_m": 0.67}})
    whats = " ".join(a["what"] for a in measured)
    assert "核定函" in whats and "竣工" in whats
    assert "任何公分數" not in whats, "a measured scale must not be denied in the same breath"


def test_f31_measures_the_red_line_gap_through_assess():
    """The published F31 figure, through the endpoint's own path."""
    path = sorted((ROOT / "evidence" / "field-2026-09-20").glob("IMG_*.jpg"))[30]
    img = cv2.imread(str(path))
    out = assess(img, FOV_24MM, 50.0)
    rg = out["red_line_gap"]
    assert rg["state"] == "MEASURED", rg.get("why")
    assert 0.63 <= rg["gap_m"] <= 0.70, rg["gap_m"]
    assert "TWO_RED_LINES" in [f["code"] for f in out["findings"]]
