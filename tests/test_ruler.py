"""The ground length must come out right under any camera, or not at all.

`marking.ruler` exists because every length this project measured needed a
pitch it never had. The claim replacing it is that a length ratio along a
ground line needs only that line's vanishing point. That claim is asserted
here against randomly generated cameras, not printed.

The refusals are tested as hard as the answer. A measurement tool whose
guards never fire is a tool with no guards - standing rule 5, and this
project has built one before (`surface_types_stable(runs=1)`, ER01), so
every constant in the module has a test that crosses it.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marking.ruler import (  # noqa: E402
    COLLINEAR_TOL_PX, MAX_TOWARDS_VP, MIN_RULER_PX,
    ground_length, length_ratio, measure)


PX = 900.0      # the synthetic camera's pixel scale


def scene(rng, spread=0.25):
    """A ground line, three points on it, and the image of all of it."""
    o = rng.normal(0, 3, 2)
    d = rng.normal(0, 1, 2)
    d /= np.linalg.norm(d)
    sB, sC = rng.uniform(0.3, 2.0), rng.uniform(2.5, 12.0)

    H = np.eye(3) + rng.normal(0, spread, (3, 3))
    H[2, 2] = 1.0

    if abs(np.linalg.det(H)) < 1e-3:
        return None

    # Into pixels. Without this the synthetic "image" spans a few units and
    # every scene is refused by MIN_RULER_PX - which is how this generator
    # was written the first time, and the exactness test then passed on the
    # 0 scenes it had left. The count assertion below exists because of it.
    H = np.array([[PX, 0, 1536.0], [0, PX, 2048.0], [0, 0, 1.0]]) @ H

    def proj(p):
        q = H @ np.array([p[0], p[1], 1.0])
        return None if abs(q[2]) < 1e-9 else q[:2] / q[2]

    pts = [proj(o + d * s) for s in (0.0, sB, sC)]
    vq = H @ np.array([d[0], d[1], 0.0])

    if any(p is None for p in pts) or abs(vq[2]) < 1e-9:
        return None

    return pts, vq[:2] / vq[2], sC / sB, sB


def test_the_ratio_is_exact_under_any_homography():
    """The whole module rests on this line, so it is checked 500 times."""
    rng = np.random.default_rng(0)
    worst, n = 0.0, 0

    for _ in range(800):
        s = scene(rng)
        if s is None:
            continue
        (a, b, c), v, truth, _ = s
        got = length_ratio(a, b, c, v)
        if got is None:
            continue
        worst = max(worst, abs(got - truth) / abs(truth))
        n += 1

    # The rest are refused, and correctly: a homography drawn this wildly
    # often puts the horizon between the points. That the guards fire is
    # tested below one by one; the bar here only stops this assertion
    # passing vacuously on an empty loop, which is mistake shape 3.
    assert n >= 300, f"only {n} scenes were measurable; the test is not testing"
    assert worst < 1e-9, f"worst relative error {worst:.3e}"


def test_the_image_ratio_alone_is_not_the_answer():
    """If dropping the vanishing point changed little, it would not be needed.

    This guards against the module quietly degenerating into the affine
    ratio - the mistake it exists to prevent.
    """
    rng = np.random.default_rng(1)
    err = []

    for _ in range(800):
        s = scene(rng)
        if s is None:
            continue
        (a, b, c), v, truth, _ = s
        if length_ratio(a, b, c, v) is None:
            continue
        naive = np.linalg.norm(np.asarray(c) - a) / np.linalg.norm(
            np.asarray(b) - a)
        err.append(abs(naive - truth) / truth)

    assert np.median(err) > 0.10, (
        f"the vanishing point moved the answer by only {np.median(err):.1%} "
        "at the median, so this scene generator is too weakly perspective "
        "to be testing anything")


def test_a_known_length_gives_metres():
    """§171's 20 cm stripe as the ruler."""
    rng = np.random.default_rng(2)
    s = None
    while s is None:
        s = scene(rng)
    (a, b, c), v, truth, sB = s
    got = ground_length(a, b, c, v, known_ab_m=0.20)
    assert got == pytest.approx(0.20 * truth, rel=1e-9)


def test_parallel_in_the_image_is_the_affine_case():
    """A vanishing point at infinity must give the plain image ratio."""
    a, b, c = np.array([10.0, 50.0]), np.array([30.0, 50.0]), np.array([90.0, 50.0])
    assert length_ratio(a, b, c, [1.0, 0.0, 0.0]) == pytest.approx(4.0)


def test_a_point_off_the_line_is_refused():
    """Off by 20 px is refused; off by 3 px is measured, and correctly.

    The axis is fitted to all three points, so a small deviation is
    absorbed into the fit rather than rejected - which is the intent, a
    hand-placed point should not have to be perfect. What stops a point
    that is genuinely somewhere else is that tilting the axis to reach it
    takes the vanishing point off the line, and that is checked. Measured:
    the refusal begins at 8 px of offset, where the fit residual is still
    only 1.23 of the 3.0 allowed, so it is the vanishing-point test doing
    the work and not the residual one.
    """
    a, b, c = np.array([0.0, 0.0]), np.array([100.0, 0.0]), np.array([400.0, 0.0])
    v = np.array([4000.0, 0.0])
    true = (400 / 100) * ((4000 - 100) / (4000 - 400))

    assert length_ratio(a, b, c, v) == pytest.approx(true)
    assert length_ratio(a, b, c + [0.0, 20.0], v) is None
    assert length_ratio(a, b, c + [0.0, 3.0], v) == pytest.approx(true, rel=1e-3)


def test_measuring_the_other_way_from_the_ruler():
    """C on the far side of A from B: a signed ratio, and the axis must hold.

    The reason this is here: the axis is fitted by SVD, whose sign for the
    first right-singular vector is nobody's contract, and `_axis` turns it
    to run a -> b. With c beyond b that turn is never needed - 0 of 4000
    random triples - so the branch looked dead and mutation testing called
    it out. With c on the OTHER side of a it is needed in 4929 of 20000,
    and no test went there. The dead branch was a dead test.

    Measuring away from the kerb in one direction and towards it in the
    other is the ordinary case on this road, so this is the geometry, not
    a corner of it.
    """
    for pitch in (-12, -25, -40):
        s = camera_scene(pitch, far_m=-2.0)
        if s is None:
            continue
        (a, b, c), v, truth = s
        assert truth == pytest.approx(-10.0)
        got = length_ratio(a, b, c, v)
        assert got is not None, f"refused at pitch {pitch}"
        assert got == pytest.approx(truth, rel=1e-9)
        assert ground_length(a, b, c, v, 0.20) == pytest.approx(-2.0, rel=1e-9)


def test_a_vanishing_point_off_the_line_is_refused():
    """v belongs to the line being measured, not merely to the picture.

    A vanishing point from the wrong family of parallel lines - the road's
    rather than the cross-road's, say - would otherwise be used without
    complaint and would return a number.
    """
    a, b, c = np.array([0.0, 0.0]), np.array([100.0, 0.0]), np.array([400.0, 0.0])

    on = np.array([4000.0, 0.0])
    assert length_ratio(a, b, c, on) is not None

    # 1 degree out at 4000 px is 70 px off the line
    assert length_ratio(a, b, c, np.array([4000.0, 40.0])) is not None
    assert length_ratio(a, b, c, np.array([4000.0, 120.0])) is None

    # and the same for a vanishing point given at infinity as a direction
    assert length_ratio(a, b, c, [1.0, 0.0, 0.0]) is not None
    assert length_ratio(a, b, c, [1.0, 0.1, 0.0]) is None


def test_a_ruler_of_a_few_pixels_is_refused():
    a, v = np.array([0.0, 0.0]), np.array([4000.0, 0.0])
    c = np.array([400.0, 0.0])

    assert length_ratio(a, np.array([MIN_RULER_PX + 1.0, 0.0]), c, v) is not None
    assert length_ratio(a, np.array([MIN_RULER_PX - 1.0, 0.0]), c, v) is None


def test_the_horizon_falling_between_the_points_is_refused():
    """v inside the span means the ground line runs through infinity there."""
    a, b, c = np.array([0.0, 0.0]), np.array([100.0, 0.0]), np.array([400.0, 0.0])
    assert length_ratio(a, b, c, np.array([250.0, 0.0])) is None
    assert length_ratio(a, b, c, np.array([50.0, 0.0])) is None
    assert length_ratio(a, b, c, np.array([4000.0, 0.0])) is not None


def test_a_vanishing_point_on_top_of_a_is_refused_not_raised():
    """The one case the ratio test cannot reach: it would divide by zero.

    Found by mutation testing. The span test that used to stand here was
    dead except for this, and a crash is not a refusal.
    """
    a, b, c = np.array([0.0, 0.0]), np.array([100.0, 0.0]), np.array([400.0, 0.0])
    assert length_ratio(a, b, c, np.array([0.0, 0.0])) is None


def test_a_point_almost_at_the_vanishing_point_is_refused():
    a, b = np.array([0.0, 0.0]), np.array([100.0, 0.0])
    v = np.array([1000.0, 0.0])

    near = np.array([MAX_TOWARDS_VP * 1000.0 + 5.0, 0.0])
    far = np.array([MAX_TOWARDS_VP * 1000.0 - 5.0, 0.0])

    assert length_ratio(a, b, near, v) is None
    assert length_ratio(a, b, far, v) is not None


def camera_scene(pitch_deg, yaw_deg=14.0, fov_deg=56.812,
                 width=3072, height=4096, ruler_m=0.20, far_m=3.0,
                 cam_h=1.5, depth=8.0):
    """A phone at `pitch_deg` and `yaw_deg`, over a cross-road line.

    The ruler is a §171 stripe width and the length wanted is lane-scale
    beside it, which is the measurement this module was written for.

    The yaw matters and is not decoration. With the camera square to the
    road the cross-road direction is parallel to the image rows, its
    vanishing point is at infinity, and the affine ratio happens to be
    exact - so a test without yaw would pass while exercising none of the
    perspective correction. Written without it first; every pose returned
    None, which is how the degeneracy was found.

    The depth is solved for rather than chosen, so the line lands in frame
    at every pitch instead of below it.
    """
    f = (width / 2) / math.tan(math.radians(fov_deg) / 2)
    K = np.array([[f, 0, width / 2], [0, f, height / 2], [0, 0, 1.0]])
    t, y = math.radians(pitch_deg), math.radians(yaw_deg)
    rx = np.array([[1, 0, 0], [0, math.cos(t), -math.sin(t)],
                   [0, math.sin(t), math.cos(t)]])
    ry = np.array([[math.cos(y), 0, math.sin(y)],
                   [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    # rectify.py's matrix maps camera rays to the world; this needs the
    # other direction, so it is transposed. Used as-is first, which turned
    # -18 degrees into looking UP 18 degrees, pushed the ground to the far
    # field and left the 20 cm ruler 1.6 px long - refused, correctly, for
    # a reason that had nothing to do with the module.
    R = rx.T @ ry

    def shot(P):
        q = K @ (R @ np.asarray(P, float))
        return None if q[2] <= 1e-6 else q[:2] / q[2]

    # A fixed depth rather than a search. The search that was here put the
    # line 1 m in front of the phone at the steeper pitches, where 3 m of
    # cross-road does not fit in a 56.8 degree lens, and the scene came
    # back None for a framing reason that looked like a refusal. 8 m is
    # where this measurement is actually taken and 3 m fits there.
    pts = [shot([x, cam_h, depth]) for x in (0.0, ruler_m, far_m)]
    vq = K @ (R @ np.array([1.0, 0.0, 0.0]))

    if any(p is None for p in pts) or abs(vq[2]) < 1e-9:
        return None
    if not all(-width <= p[0] <= 2 * width and 0 <= p[1] <= height
               for p in pts):
        return None

    return pts, vq[:2] / vq[2], far_m / ruler_m


def test_a_phone_pointed_at_this_road_is_not_refused():
    """The guards must let real photographs through.

    Built because this project has shipped a guard that refused nothing
    (ER01) and detectors that refused everything (§167, 0 of 42). A tool
    whose refusals are never crossed and a tool whose refusals are always
    crossed are the same tool: one that is not looking.
    """
    ok, tried, worst = 0, 0, 0.0

    for pitch in (-8, -12, -18, -25, -32, -40):
        s = camera_scene(pitch)
        if s is None:
            continue
        tried += 1
        (a, b, c), v, truth = s
        got = length_ratio(a, b, c, v)
        if got is not None:
            ok += 1
            worst = max(worst, abs(got - truth) / truth)

    assert tried >= 6
    assert ok >= tried - 1, (
        f"only {ok} of {tried} plausible phone poses were measurable; the "
        "guards are refusing the photographs this exists to measure")
    assert worst < 1e-9, f"worst relative error {worst:.3e}"


def test_measure_reports_a_spread_that_grows_with_the_jitter():
    (a, b, c), v, truth = camera_scene(-25)

    tight = measure(a, b, c, v, 0.20, jitter_px=0.2, trials=300)
    loose = measure(a, b, c, v, 0.20, jitter_px=3.0, trials=300)


    assert tight["ok"] and loose["ok"]
    assert tight["m"] == pytest.approx(0.20 * truth, rel=0.25)
    assert (loose["m_hi"] - loose["m_lo"]) > (tight["m_hi"] - tight["m_lo"]), (
        "the reported spread did not widen when the inputs got worse, so it "
        "is not carrying the input uncertainty")


def test_measure_refuses_when_most_perturbations_refuse():
    """A reading that only survives the exact pixels given is not a reading."""
    a, b = np.array([0.0, 0.0]), np.array([100.0, 0.0])
    v = np.array([1000.0, 0.0])
    edge = np.array([MAX_TOWARDS_VP * 1000.0 - 0.3, 0.0])

    out = measure(a, b, edge, v, 0.20, jitter_px=6.0, trials=200)

    assert out["ok"] is False
    assert "perturbations refused" in out["why"]


def test_measure_refuses_what_length_ratio_refuses():
    a, b, c = np.array([0.0, 0.0]), np.array([100.0, 0.0]), np.array([400.0, 0.0])
    out = measure(a, b, c, np.array([250.0, 0.0]), 0.20)
    assert out["ok"] is False and out["m"] is None
