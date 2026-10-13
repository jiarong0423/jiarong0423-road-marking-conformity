"""Ground lengths from one known length and a vanishing point. No pose.

Every length this project tried to measure needed the camera's pitch, and
the camera's pitch was never known. `results/taper_after.json` was withdrawn
for recovering it from Hough lines and getting -8.0 to +19.6 degrees over
eight frames of one road; `results/band_width.json` was withdrawn because
the rectification it needed was degenerate, the horizon passing within
0.7 px of the stripes and the warp scale spanning 462x. The phone
photographs carry their field of view in EXIF and say nothing about where
the phone was pointed.

There is a construction that does not ask.

For three points A, B, C lying on one line on the ground, whose image is
the line through a, b, c, and whose direction has vanishing point v on that
same image line,

    D(A,C)   ac     tv - ab
    ------ = --  *  -------
    D(A,B)   ab     tv - ac

with every term a SIGNED coordinate along the image line. This is the
cross-ratio (a, b; c, v) written out, v being the image of the line's point
at infinity, and it is exact: 2000 random homographies return the ground
ratio to 1.2e-13. Pitch, roll, height and focal length do not appear.

Taking the image ratio on its own instead - which is what an eye does -
is wrong by a median of 50 % over the same 2000, and by 896-fold at worst.
The vanishing point is not a correction to the answer. It is the answer.

**One known length turns the ratio into metres**, and the regulation
supplies them: §169 gives a red line 一○公分, §171 a chevron stripe
二○公分 with 間隔三○公分. A ruler that the law defines, lying on the
ground next to the thing in question.

What this cannot do is measure between two points that are not on one
ground line, or anything at all when the line runs into the horizon inside
the span being measured. Both are refusals here rather than numbers.
"""

from __future__ import annotations

import math

import numpy as np

# A point this far off the fitted line is not on that line.
# The photographs are 3072 px wide, so this is 0.1 % of the frame; it is
# loose enough for a hand-placed point and tight enough that the two edges
# of a different marking do not pass.
COLLINEAR_TOL_PX = 3.0

# `ab` is the ruler. Below this it is too few pixels to divide by: a 1 px
# error on a 12 px ruler is 8 % before anything else goes wrong.
MIN_RULER_PX = 12.0

# How close C may come to the vanishing point, as a fraction of the way
# from A. At tc/tv = 1 the denominator is zero and the length is infinite,
# which is correct - C is on the horizon - and useless.
MAX_TOWARDS_VP = 0.90


# The vanishing point must lie along the fitted line, not merely near it in
# pixels: it is usually thousands of pixels away, where a small angular
# error is a large perpendicular one. 1 degree, as a slope.
VP_OFF_AXIS_TOL = math.tan(math.radians(1.0))


def _axis(a, b, c):
    """The line through all three points, by total least squares.

    Defining the axis by `a` and `b` alone - which is what this did first -
    makes the direction only as good as the ruler is long, and the ruler is
    the SHORT thing here: a 20 cm stripe is 76 px where the length wanted
    is 1248. Moving a and b by 0.2 px each turns the axis by 0.005 rad,
    which is 6.5 px of perpendicular offset out at c, and c is then refused
    for not being on a line it is on. `measure` refused 279 of 300
    perturbations at a fifth of a pixel of jitter before this.

    Fitting to all three spreads that error over the whole span instead of
    levering it off the short end.

    Returns the origin (the foot of `a`), the unit direction oriented from
    `a` towards `b`, the ruler's length along it, and the largest residual.
    """
    P = np.array([np.asarray(p, float) for p in (a, b, c)])
    mid = P.mean(0)
    _, _, vt = np.linalg.svd(P - mid, full_matrices=False)
    d = vt[0] / np.linalg.norm(vt[0])

    t = (P - mid) @ d
    residual = float(np.abs((P - mid) - np.outer(t, d)).max())

    if t[1] < t[0]:                      # orient a -> b
        d, t = -d, -t

    origin = mid + d * t[0]

    return origin, d, float(t[1] - t[0]), residual


def _coord(p, a, d):
    """Signed position of `p` along the axis, and its distance off it."""
    w = np.asarray(p, float) - a
    t = float(w @ d)
    return t, float(np.hypot(*(w - d * t)))


def _vanishing_coord(v, a, d):
    """The vanishing point's signed position, or inf when it is at infinity.

    `v` may be a pixel (2 values) or homogeneous (3). A homogeneous v with
    w = 0 is a direction: the lines are parallel in the image, the ratio is
    affine, and the third factor is 1.
    """
    v = np.asarray(v, float)

    if v.size == 3:
        if abs(v[2]) < 1e-9:
            along = float(v[:2] @ d)
            off = float(np.hypot(*(v[:2] - d * along)))
            if abs(along) < 1e-12 or off > abs(along) * VP_OFF_AXIS_TOL:
                return None, off          # not this line's vanishing point
            return np.inf * np.sign(along), 0.0
        v = v[:2] / v[2]

    return _coord(v, a, d)


def length_ratio(a, b, c, v):
    """D(A,C) / D(A,B) on the ground. `None` when the geometry refuses.

    Refusals are returned rather than raised because a frame that cannot
    be measured is an ordinary outcome here, not an error.
    """
    a0, d, ab, residual = _axis(a, b, c)

    if ab < MIN_RULER_PX or residual > COLLINEAR_TOL_PX:
        return None

    tc, _ = _coord(c, a0, d)
    tv, off_v = _vanishing_coord(v, a0, d)

    if tv is None:
        return None

    if not np.isinf(tv) and off_v > abs(tv) * VP_OFF_AXIS_TOL:
        return None

    if abs(tc) < 1e-12:
        return 0.0

    if np.isinf(tv):
        return tc / ab

    # The vanishing point landing on A itself is the one case the ratio
    # test below cannot reach, because it divides by tv.
    if abs(tv) < 1e-9:
        return None

    # Nothing may sit near the point at infinity, and this covers the
    # horizon falling between the points as well. A span test was written
    # here too, and mutation testing showed it dead: v inside the span puts
    # |tv| at or below max(|ab|, |tc|), so one of these ratios is already at
    # least 1. It is deleted rather than left, because dead code reads as a
    # road someone has already been down. Shape 4 in isolation/SHAPES.md,
    # and E55's rule.
    if abs(tc / tv) > MAX_TOWARDS_VP or abs(ab / tv) > MAX_TOWARDS_VP:
        return None

    return (tc / ab) * ((tv - ab) / (tv - tc))


def ground_length(a, b, c, v, known_ab_m):
    """D(A,C) in metres, given D(A,B). `None` on the same refusals."""
    r = length_ratio(a, b, c, v)

    return None if r is None else r * known_ab_m


def measure(a, b, c, v, known_ab_m, jitter_px=1.5, trials=200, seed=0):
    """The length with the spread its own inputs give it.

    A single number from four hand-placed points would be a claim about
    pixels. Jittering each of them by `jitter_px` and reporting the range
    is a claim about the road, and it is the same construction
    `vanishing.angle_uncertainty` uses on angles.

    `v` may be a single vanishing point or an ensemble of them, shape
    (N, 2) or (N, 3), in which case the trials draw from it and the spread
    carries the vanishing point's own uncertainty as well.
    """
    point = ground_length(a, b, c, v if np.asarray(v).ndim == 1
                          else np.asarray(v)[0], known_ab_m)

    if point is None:
        return {"ok": False, "why": "the geometry refuses these four points",
                "m": None}

    rng = np.random.default_rng(seed)
    vs = np.atleast_2d(np.asarray(v, float))
    got, refused = [], 0

    for _ in range(trials):
        jab = [np.asarray(p, float) + rng.normal(0, jitter_px, 2)
               for p in (a, b, c)]
        vi = vs[rng.integers(len(vs))]
        L = ground_length(*jab, vi, known_ab_m)

        if L is None:
            refused += 1
        else:
            got.append(L)

    if len(got) < trials // 2:
        return {"ok": False,
                "why": f"{refused} of {trials} perturbations refused, so the "
                       f"reading sits on the edge of what the geometry allows",
                "m": None}

    got = np.array(got)

    return {"ok": True,
            "m": float(np.median(got)),
            "m_lo": float(np.percentile(got, 5)),
            "m_hi": float(np.percentile(got, 95)),
            "ruler_m": float(known_ab_m),
            "trials": trials,
            "refused": refused,
            "jitter_px": jitter_px}
