"""The image result must drive an action, and every action must be earned.

The competition's Agentic Vision criterion states that explaining a
fixed result is not enough - the result has to drive a plan, a tool
call, an action or a request for human approval. `route.py` was built
for exactly that criterion and sat imported by nothing for two days,
which is standing rule 7's shape and E55's.

So these tests assert two things: that the actions exist on the
delivery path, and that each one is tied to something in THIS
photograph rather than printed unconditionally.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from marking.actions import next_actions  # noqa: E402
from marking.situation import assess      # noqa: E402

ADMITTED = np.full((900, 1200, 3), 128, np.uint8)
NOISE = np.random.default_rng(0).integers(0, 255, (900, 1200, 3),
                                          dtype=np.uint8)


def test_assess_attaches_the_actions_itself():
    """Not left for a caller to remember - that is how route.py was
    built for this criterion and never wired."""
    out = assess(ADMITTED, 60.0, 50.0)
    assert out["next_actions"], "assess() produced no actions"


def test_a_frame_that_is_not_a_road_asks_for_a_retake_and_nothing_else():
    out = assess(NOISE, 60.0, 50.0)
    acts = out["next_actions"]
    assert [a["action"] for a in acts] == ["RETAKE"], acts
    assert "30%" in acts[0]["why"] or "30" in acts[0]["why"]


def test_every_action_says_what_in_this_photograph_caused_it():
    out = assess(ADMITTED, 60.0, 50.0)
    for a in out["next_actions"]:
        assert a["why"].strip(), f"{a['action']} has no why"
        assert a["what"].strip()


def test_the_document_actions_appear_only_when_something_caused_them():
    """A request to the authority is printed because THIS frame found
    an occupation or a patched surface, not on every frame."""
    quiet = next_actions({"findings": [], "taper": {"state": "CANNOT_MEASURE"}})
    kinds = [a["action"] for a in quiet]
    assert "REQUEST_DOCUMENT" not in kinds, quiet
    assert "CHECK_PUBLIC_RECORD" not in kinds

    occupied = next_actions({
        "findings": [{"code": "CARRIAGEWAY_OCCUPIED", "measured": {}}],
        "taper": {"state": "CANNOT_MEASURE"}})
    kinds = [a["action"] for a in occupied]
    assert "REQUEST_DOCUMENT" in kinds and "CHECK_PUBLIC_RECORD" in kinds


def test_a_human_look_is_asked_for_each_clause_that_fired():
    r = next_actions({
        "findings": [{"code": "EDGE_NOT_CARRIAGEWAY",
                      "measured": {"px": [1, 2, 3, 4]}}],
        "taper": {"state": "CANNOT_MEASURE"}})
    looks = [a for a in r if a["action"] == "HUMAN_LOOK"]
    assert len(looks) == 1
    assert "§169" in looks[0]["what"]
    assert looks[0]["evidence"]["框"] == [1, 2, 3, 4], (
        "the action does not carry the box a person is meant to open")


def test_the_things_a_photograph_cannot_answer_are_always_said():
    """These are not findings and they do not depend on detections.
    A reader who is told only what was found will assume the rest was
    checked."""
    r = next_actions({"findings": [], "taper": {"state": "CANNOT_MEASURE"}})
    what = " ".join(a["what"] for a in r)
    assert "公分" in what, "no statement that centimetres are unavailable"
    assert "水溝蓋" in what, "no statement that drain covers are undetected"


def test_an_answered_taper_does_not_print_the_taper_refusal():
    r = next_actions({"findings": [],
                      "taper": {"state": "STEEPER_THAN_REFERENCE"}})
    assert not [a for a in r if "漸變段" in a["what"]]
