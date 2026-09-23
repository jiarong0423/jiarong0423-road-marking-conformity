"""The taper angle from vanishing points, with no pitch and no bearing.

Everything that broke in this project broke for the same reason: the
measurement needed to know where the camera was pointed, and it never did.
The pitch came from the Static API's nominal value, which carries one to two
degrees of dynamic error from the survey car's suspension - the round-trip
test in tests/ verified the arithmetic of the projection, not the truth of
its inputs. The road's direction came from a caller-supplied bearing that
turned out to be 141.87 +- 8.32 degrees, which is +-0.131 on the rate,
larger than every threshold the gate compares against.

There is a construction that needs neither.

A set of parallel lines on the ground meets at a vanishing point v, and the
3D direction of that set is K^-1 v, where K holds only the focal length and
principal point. The angle between two such directions is

    cos θ = (K^-1 v1) · (K^-1 v2) / (|K^-1 v1| |K^-1 v2|)

and **an angle between two directions does not change when the camera
rotates**. Pitch and roll drop out of the algebra, not out of the error
budget by being small. The road supplies its own direction through its own
vanishing point, so no external bearing is needed either. Hartley &
Zisserman, Multiple View Geometry, on vanishing points and the calibration
conic.

What is left to get right is the lines. That is the honest remaining
problem, and it is now the only one - and it is attacked in the original
image at full resolution rather than in a bird's eye plane that stretches
the far field.

§171 then gives a check the same framework computes: the chevron's arms sit
45 degrees from its boundary, so a third vanishing point must land there.
A set that does not is not the arms.
"""

from __future__ import annotations

import math

import numpy as np


def intrinsics(fov_deg: float, width: int, height: int) -> np.ndarray:
    """K from the field of view the request fixed. No pose, no scale."""
    f = (width / 2) / math.tan(math.radians(fov_deg) / 2)
    return np.array([[f, 0, width / 2],
                     [0, f, height / 2],
                     [0, 0, 1.0]])


def vanishing_point(segments, weights=None):
    """Where a set of image lines meets, in least squares.

    Each segment contributes the line through its endpoints. The meeting
    point is the null space of the stacked lines, found by SVD so a set that
    is genuinely parallel in the image - meeting at infinity - comes back as
    a point at infinity rather than blowing up.
    """
    rows = []
    for i, (x1, y1, x2, y2) in enumerate(segments):
        line = np.cross([x1, y1, 1.0], [x2, y2, 1.0])
        n = np.linalg.norm(line[:2])
        if n < 1e-9:
            continue
        w = 1.0 if weights is None else float(weights[i])
        rows.append(line / n * w)
    if len(rows) < 2:
        return None
    _, s, vt = np.linalg.svd(np.array(rows))
    v = vt[-1]
    # how well the set actually agrees: the smallest singular value against
    # the next, which is 0 for a perfect pencil and grows as they scatter
    condition = float(s[-1] / s[-2]) if len(s) > 1 and s[-2] > 0 else float("inf")
    return v, condition


def direction(K_inv, v) -> np.ndarray:
    d = K_inv @ np.asarray(v, float)
    n = np.linalg.norm(d)
    return d / n if n > 1e-12 else d


def angle_between(K, v1, v2) -> float:
    """The 3D angle between two families of parallel ground lines, degrees.

    Invariant to the camera's rotation, which is the whole point.
    """
    K_inv = np.linalg.inv(K)
    d1, d2 = direction(K_inv, v1), direction(K_inv, v2)
    c = float(np.clip(abs(d1 @ d2), -1.0, 1.0))
    return math.degrees(math.acos(c))


def angle_uncertainty(K, segs1, segs2, trials=200, jitter_px=1.5, seed=0):
    """How much the angle moves when the line endpoints are perturbed.

    The endpoints are where a threshold happened to fall on a painted edge,
    so a pixel or two of jitter is the honest question to ask of them. This
    replaces a guard band derived from three repeat captures, which for n=3
    could not have failed: the sample range cannot exceed sqrt(3) times the
    sd, so it always sits inside a k=2 band whatever the estimator does.
    """
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(trials):
        a = [tuple(np.array(s, float) + rng.normal(0, jitter_px, 4)) for s in segs1]
        b = [tuple(np.array(s, float) + rng.normal(0, jitter_px, 4)) for s in segs2]
        va, vb = vanishing_point(a), vanishing_point(b)
        if va is None or vb is None:
            continue
        out.append(angle_between(K, va[0], vb[0]))
    if len(out) < trials // 2:
        return None
    o = np.array(out)
    return {"mean_deg": float(o.mean()), "sd_deg": float(o.std()),
            "p2.5": float(np.percentile(o, 2.5)),
            "p97.5": float(np.percentile(o, 97.5)), "trials": len(o)}
