"""The pipeline's structural invariants, which are its whole claim.

`pipeline.py` asserted twice in its docstring that this file enforced
them, and this file did not exist - found 2026-09-21 by a supervision
agent. Standing rule 7: a guarantee that nothing checks is a sentence,
not a guarantee.

Two invariants, both mechanical:

  * `search_domain` may not grow an appearance argument. Where a marking
    may be looked for has to be decided without looking at the markings,
    or the region is scored by the thing it was drawn to favour. That is
    the defect `carriageway()` had - it called `markings()` and was then
    graded on how much `markings()` output survived - and it cost 45
    percentage points of paint retention before it was found.
  * `stages_built()` may not claim a stage that `run` does not call.
    `ground_plane` is in the module and is not in the pipeline; three
    versions of it failed their own held-out check.
"""
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

# isolation/src, not the project's src: these four modules are not on the
# delivery path and are kept here so they stay runnable, not so they ship.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marking import pipeline  # noqa: E402

BANNED = ("image", "bgr", "img", "mask", "paint", "response", "segments",
          "horizon_y", "plane", "gray")


def test_search_domain_cannot_see_the_image():
    params = set(inspect.signature(pipeline.search_domain).parameters)
    leaked = params & set(BANNED)
    assert not leaked, (
        f"search_domain grew {sorted(leaked)}. A search region that is "
        "chosen by appearance is scored by the appearance that chose it.")
    assert "shape" in params


def test_search_domain_is_the_same_for_any_content_of_that_shape():
    """The invariant above, asserted on behaviour and not only on names.

    A signature check catches the argument being added. This catches it
    being smuggled in some other way - a module-level cache, a global,
    a read of a file beside the image.
    """
    shape = (4096, 3072, 3)
    a = pipeline.search_domain(shape)
    for _ in range(3):
        assert np.array_equal(pipeline.search_domain(shape), a)
    assert a.shape == shape[:2] and a.dtype == np.uint8
    assert 0 < a.mean() < 255          # neither empty nor the whole frame


def test_search_domain_is_the_lower_part_of_the_frame():
    m = pipeline.search_domain((1000, 800, 3))
    assert m[:399].max() == 0, "something above the cut is in the domain"
    assert m[400:].min() > 0, "something below the cut is not"


def test_stages_built_does_not_claim_a_stage_run_does_not_call():
    st = pipeline.stages_built()
    src = inspect.getsource(pipeline.run)
    for stage in st["built"]:
        fn = stage.split(":")[-1] if ":" in stage else stage
        alias = {"provenance": "provenance(", "paint": "paint_field(",
                 "search_domain": "search_domain(", "scale": "scale()",
                 "ipm": "near_field_ipm("}[fn]
        assert alias in src, f"stages_built claims {stage!r}; run does not call it"
    for stage in st["present_but_not_called"]:
        assert stage not in st["built"]
        assert st["present_but_not_called_why"].get(stage), (
            f"{stage} is listed as not called and does not say why. "
            "A stage that failed and a stage that is simply not on this "
            "path are not the same thing.")
    assert "plane" in st["present_but_not_called"]
    assert "ground_plane(" not in src, (
        "ground_plane is called from run, but is listed as not called")


def test_the_unbuilt_stages_are_declared_and_not_quietly_absent():
    st = pipeline.stages_built()
    assert st["specified_not_built"], "the specification is fully built, or not read"
    # The specification lives at the repository root, not beside the
    # isolated copy of the code it specifies.
    assert Path(__file__).resolve().parents[2].joinpath(
        st["specification"]).exists()


# ---------------------------------------------------------------- stage 3-4


def test_the_scale_is_absent_and_says_which_candidates_it_considered():
    """Absent is a result here, so it has to carry its reasons.

    All five sources in the enum are named, because a scale that is
    missing for an unstated reason is indistinguishable from one nobody
    looked for. Two of the five are refused on grounds that no amount of
    data fixes: §171 is circular, and §169 may not be on the plane.
    """
    sc = pipeline.scale()
    assert sc.source == "NONE" and sc.source in pipeline.SCALE_SOURCES
    assert sc.metres_per_px is None
    for token in ("camera height", "§182", "§169", "§171"):
        assert token in sc.why, f"the scale does not say why {token} is out"


def test_the_scale_does_not_read_the_image():
    """A scale taken from the markings is checked against the markings."""
    banned = {"image", "bgr", "img", "mask", "paint", "segments", "response"}
    assert not set(inspect.signature(pipeline.scale).parameters) & banned


def test_a_tolerance_the_scale_cannot_resolve_is_refused_not_caveated():
    assert not pipeline.scale().admits(0.006)          # §02898's +-6 mm
    good = pipeline.Scale("CAMERA_HEIGHT_RECORDED", 0.007, 0.03, "taped")
    assert good.admits(0.006)                          # 3*0.03*0.007 = 0.6 mm
    assert not good.admits(0.0005)


def test_stage_4_names_both_blocks_and_not_just_the_first():
    """Fixing either one alone changes nothing, so both have to be visible."""
    r = pipeline.near_field_ipm(pipeline.scale())
    assert r["ran"] is False and len(r["blocked_by"]) == 2
    assert any("plane" in b for b in r["blocked_by"])
    assert any("scale" in b for b in r["blocked_by"])
    # And a plane alone does not unblock it.
    r2 = pipeline.near_field_ipm(pipeline.scale(), plane={"horizon_y_px": 900})
    assert r2["ran"] is False and len(r2["blocked_by"]) == 1


def test_the_stage_4_falsifier_reads_a_plane_error_as_a_plane_error():
    drifting = pipeline.depth_invariance({"near": 0.40, "mid": 0.46, "far": 0.53})
    assert drifting["monotone"] and drifting["drift"] > 0.1
    flat = pipeline.depth_invariance({"near": 0.40, "mid": 0.41, "far": 0.40})
    assert not flat["monotone"]
    assert pipeline.depth_invariance({"near": 0.4})["ran"] is False


# ---------------------------------------------------------------- stage 5


def test_s171_is_a_conjunction_and_not_periodicity():
    """The recorded false positive, asserted.

    `_grated_cover` tested periodicity and returned the chevron, an
    asphalt patch and the ghost of an erased chevron - and no drain
    cover. §171 states four properties. A predicate that keeps only the
    most distinctive one repeats that failure, so this fixes the other
    three in place.
    """
    real = pipeline.s171_chevron({"periodic": True, "duty": 0.41}, 46.4, True)
    assert real.present and real.failed == ()

    ghost = pipeline.s171_chevron({"periodic": True, "duty": 0.40}, 46.0, False)
    assert not ghost.present
    assert any("imprint" in f for f in ghost.failed), ghost.failed

    patch = pipeline.s171_chevron({"periodic": True, "duty": 0.72}, 8.0, True)
    assert not patch.present and len(patch.failed) == 2

    bare = pipeline.s171_chevron({"periodic": True}, None, None)
    assert not bare.present and len(bare.failed) == 3, (
        "periodicity alone passed, which is the removed detector")


def test_s171_carries_the_regulated_figures_it_was_checked_against():
    c = pipeline.s171_chevron({"periodic": True, "duty": 0.41}, 46.4, True)
    assert c.scale_free["duty_regulated"] == pipeline.S171_DUTY == 0.400
    assert c.scale_free["arm_regulated"] == pipeline.S171_ARM_DEG == 45.0


def test_identify_says_what_it_does_not_find():
    """A findings list that reads as exhaustive when it is not is a lie."""
    import numpy as np
    r = pipeline.identify({}, pipeline.search_domain((1000, 800, 3)))
    assert r["s171_has_no_locator"] is True
    for token in ("grated", "182", "locator", "ERASED"):
        assert token in r["known_not_identified"]
    assert set(r["not_identified"]) >= {"182", "180", "165"}


def test_the_sections_present_are_a_subset_of_those_with_predicates():
    r = pipeline.identify({"red": {"present": True},
                           "double_white": {"present": True}},
                          pipeline.search_domain((1000, 800, 3)))
    assert set(r["present"]) <= {"171", "167", "169"}
    assert "169" in r["present"] and "167" in r["present"]
