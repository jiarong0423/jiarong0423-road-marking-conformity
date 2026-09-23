"""The angle between two ground directions must not move when the camera does.

This is the claim the whole measurement now rests on, so it is asserted
rather than printed. Two families of parallel ground lines are set a known
angle apart and photographed from a range of pitches, rolls and fields of
view. If K^-1 v is the direction and the angle between directions is
rotation-invariant, every pose returns the same number.

The previous pipeline needed the pitch to be right and it was not - the
Static API's nominal value carries a degree or two of suspension movement -
and it needed the road's bearing, which measured 141.87 +- 8.32 degrees.
Neither appears here.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marking.vanishing import intrinsics, vanishing_point, angle_between  # noqa: E402

W = H = 640
POSES = [(-12, 0, 40), (-20, 0, 60), (-20, 3, 90), (-25, -2, 75),
         (-35, 0, 60), (-35, 4, 90), (-42, 3, 50), (-42, -5, 90)]


def project(P, K, pitch, roll):
    t, r = math.radians(pitch), math.radians(roll)
    rx = np.array([[1, 0, 0], [0, math.cos(t), -math.sin(t)],
                   [0, math.sin(t), math.cos(t)]])
    rz = np.array([[math.cos(r), -math.sin(r), 0],
                   [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    c = (rz @ rx) @ P
    if c[2] <= 1e-6:
        return None
    q = K @ c
    p = q[:2] / q[2]
    return p if (0 <= p[0] < W and 0 <= p[1] < H) else None


def family(angle_deg, K, pitch, roll):
    """Segments of parallel ground lines at this bearing that stay in frame."""
    a = math.radians(angle_deg)
    segs = []
    for off in np.linspace(-6, 6, 13):
        pts = []
        for z in np.linspace(1.5, 14.0, 40):
            p = project(np.array([off + z*math.tan(a), 1.0, z]), K, pitch, roll)
            if p is not None:
                pts.append(p)
        if len(pts) >= 2 and np.hypot(*(pts[-1] - pts[0])) > 25:
            segs.append((pts[0][0], pts[0][1], pts[-1][0], pts[-1][1]))
    return segs


@pytest.mark.parametrize("true_deg", [3.5, 11.4, 45.0])
def test_angle_is_the_same_from_every_pose(true_deg):
    got = []
    for pitch, roll, fov in POSES:
        K = intrinsics(fov, W, H)
        a, b = family(0.0, K, pitch, roll), family(true_deg, K, pitch, roll)
        if len(a) < 2 or len(b) < 2:
            continue
        va, vb = vanishing_point(a), vanishing_point(b)
        assert va is not None and vb is not None
        got.append(angle_between(K, va[0], vb[0]))
    assert len(got) >= 5, f"only {len(got)} poses produced enough lines"
    got = np.array(got)
    assert abs(got.mean() - true_deg) < 1e-3, (
        f"{true_deg} deg went in, {got.mean():.6f} came back")
    assert got.std() < 1e-3, (
        f"the angle moved with the camera: sd {got.std():.6f} deg over "
        f"{len(got)} poses spanning pitch -12 to -42 and roll -5 to +5")


def test_pitch_error_does_not_reach_the_angle():
    """The failure mode that broke the old pipeline, made explicit.

    An earlier version of this test looped `for wrong in (-23, -25, -27)`
    and never used `wrong`. It asserted the same fixed expression three
    times and passed without testing its own name - found 2026-09-21 by
    a supervision agent, in the one test the project now rests on.

    A test that a wrong pitch changes nothing has to give the wrong pitch
    somewhere it could take effect. So both paths run here: the old one,
    which is handed the pitch, and the new one, which has no parameter to
    hand it to. The old one moves. The new one cannot.
    """
    import inspect
    from marking.rectify import ground_angle

    K = intrinsics(75, W, H)
    a, b = family(0.0, K, -25, 0), family(11.4, K, -25, 0)

    # New path. The pitch is not an argument, so there is nowhere to put it.
    assert "pitch" not in inspect.signature(angle_between).parameters
    exact = angle_between(K, vanishing_point(a)[0], vanishing_point(b)[0])
    assert abs(exact - 11.4) < 1e-3

    # Old path. The pitch is an argument, and a wrong one is used.
    #
    # `rectify` counts pitch downward-positive and `project` above counts
    # it downward-negative, so the true pitch is +25 here. At +25 the old
    # path returns 0.000 and 11.400 exactly - its arithmetic is right, and
    # that is the point: what failed was never the arithmetic.
    moved = []
    for wrong in (23, 25, 27):         # what the API might have reported
        ga = ground_angle(a[0], 75, wrong, (W, H))
        gb = ground_angle(b[0], 75, wrong, (W, H))
        moved.append(abs((gb - ga + 90) % 180 - 90))
    at_truth = moved[1]                # wrong == 25 is the true pitch
    assert abs(at_truth - 11.4) < 0.5, f"the old path is wrong even at the true pitch: {at_truth}"

    # Two degrees of pitch error moves the old answer, and the amount is
    # the reason the new path exists. If this ever stops moving, the two
    # paths have converged and this test no longer distinguishes them.
    drift = max(abs(m - at_truth) for m in (moved[0], moved[2]))
    assert drift > 1e-6, "a wrong pitch changed nothing in the path that takes one"
    assert abs(exact - at_truth) < 1e-3   # they agree when the pitch is right
