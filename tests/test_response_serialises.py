"""The response must survive `json.dumps`, because nothing else catches it.

E40. `carriageway_found` was changed to `roi is not None and (roi > 0).any()`
in the G01 commit. `.any()` returns `numpy.bool_`, which is not
JSON-serialisable - and `json.dumps` in `aws/handler.py` sits OUTSIDE the
try that wraps `assess()`. So every real photograph became a 500 with no
body, and the 153-test suite said nothing, because no test ever
serialised a result.

Two guards: the values are plain Python, and the handler's encoder
survives a numpy scalar anyway.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "aws"))

from marking.situation import assess  # noqa: E402


# A frame that PASSES the gate, which is the only path that reaches the
# line E40 was on. The first version of these tests fed noise, which
# takes the early return and its literal `False` - so removing the cast
# left them green. A test that cannot reach its subject is not a test.
ADMITTED = np.full((900, 1200, 3), 128, np.uint8)


def test_a_refused_frame_serialises():
    out = assess(np.random.default_rng(0).integers(
        0, 255, (900, 1200, 3), dtype=np.uint8), 60.0, 50.0)
    json.dumps(out, ensure_ascii=False)


def test_an_admitted_frame_serialises():
    out = assess(ADMITTED, 60.0, 50.0)
    assert out.get("state") != "NOT_A_ROAD_PHOTOGRAPH", (
        "this frame does not reach the code under test")
    assert isinstance(out["carriageway_found"], bool)
    json.dumps(out, ensure_ascii=False)


def test_every_scalar_in_the_result_is_a_python_type():
    """The cast has to be at the source, not only in the encoder."""
    out = assess(ADMITTED, 60.0, 50.0)
    assert out.get("state") != "NOT_A_ROAD_PHOTOGRAPH"

    def walk(node, path="out"):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}[{k!r}]")
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        else:
            assert not isinstance(node, (np.generic, np.ndarray)), (
                f"{path} is {type(node).__name__}, which json.dumps refuses")

    walk(out)


def test_the_handler_encoder_survives_a_numpy_scalar():
    """The belt as well as the braces: the next one must not 500."""
    handler = pytest.importorskip("handler")
    body = json.dumps({"a": np.bool_(True), "b": np.float32(1.5),
                       "c": np.array([1, 2])},
                      ensure_ascii=False, default=handler._plain)
    assert json.loads(body) == {"a": True, "b": 1.5, "c": [1, 2]}


def test_the_encoder_still_refuses_something_it_cannot_represent():
    handler = pytest.importorskip("handler")
    with pytest.raises(TypeError):
        json.dumps({"x": object()}, default=handler._plain)
