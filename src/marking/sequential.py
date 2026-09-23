"""Find the road first, then look where the regulation says the taper is.

Grouping line segments by image bearing cannot separate a taper edge from
the lane line it runs beside. On four captures of this site every pairwise
angle between families came out between 13 and 80 degrees and not one was
in single digits, because a compliant taper is 3.5 to 5.5 degrees off the
carriageway while the grouping window was 9. The quantity was smaller than
the resolution of the step meant to isolate it, and no window setting fixes
that: wider merges, narrower splinters one marking into several.

The answer is not to group. It is to search, and to let the regulation say
where:

    1. the lane lines are the most redundant structure in a road
       photograph, so the dominant vanishing point is theirs. Take it by
       RANSAC on the sphere, where parallel lines are great circles.
    2. remove the segments that voted for it.
    3. a taper's boundary must lie within a few degrees of the road -
       L = W·V²/155 puts it at 5.5 degrees at 40 km/h and 3.5 at 50, and
       even a taper three times too steep is under 20. So search the
       remainder only inside that corridor. A second direction found there
       is the taper edge; the lane line cannot swallow it because the lane
       line has already been removed.

The corridor is the point. It is not a threshold chosen to make the answer
come out: it is the range the regulation defines, and a boundary outside it
is not a taper at all.
"""

from __future__ import annotations

import math

import numpy as np

from .vanishing import intrinsics, angle_between


def _great_circles(segments, K_inv):
    """Each image line as a plane normal on the sphere.

    A line through two image points is the plane through the camera centre
    containing them; its normal is what a vanishing point must be
    perpendicular to. Parallel lines share that perpendicular.
    """
    out = []
    for x1, y1, x2, y2 in segments:
        a = K_inv @ np.array([x1, y1, 1.0])
        b = K_inv @ np.array([x2, y2, 1.0])
        n = np.cross(a, b)
        norm = np.linalg.norm(n)
        if norm > 1e-9:
            out.append(n / norm)
    return np.array(out) if out else np.zeros((0, 3))


def dominant_direction(segments, K, iters=600, tol_deg=1.2, seed=0):
    """The direction most of these lines share, by RANSAC on the sphere."""
    K_inv = np.linalg.inv(K)
    normals = _great_circles(segments, K_inv)
    if len(normals) < 2:
        return None
    rng = np.random.default_rng(seed)
    tol = math.radians(tol_deg)
    best = (0, None)
    for _ in range(iters):
        i, j = rng.choice(len(normals), 2, replace=False)
        d = np.cross(normals[i], normals[j])
        n = np.linalg.norm(d)
        if n < 1e-9:
            continue
        d = d / n
        # a line belongs if its plane contains the direction
        resid = np.abs(normals @ d)
        inl = resid < math.sin(tol)
        if inl.sum() > best[0]:
            best = (int(inl.sum()), d, inl)
    if best[1] is None or best[0] < 3:
        return None
    count, d, inl = best
    # refine on the inliers: the direction is the null space of their normals
    _, _, vt = np.linalg.svd(normals[inl])
    d = vt[-1]
    resid = np.degrees(np.arcsin(np.clip(np.abs(normals @ d), 0, 1)))
    return {"direction": d, "inliers": np.asarray(inl),
            "count": int(inl.sum()),
            "residual_deg": float(resid[inl].mean())}


def corridor_direction(segments, K, reference, lo_deg, hi_deg,
                       iters=600, tol_deg=1.2, seed=1):
    """A second direction, searched only where the regulation allows one."""
    K_inv = np.linalg.inv(K)
    normals = _great_circles(segments, K_inv)
    if len(normals) < 2:
        return None
    rng = np.random.default_rng(seed)
    tol = math.radians(tol_deg)
    best = (0, None, None)
    for _ in range(iters):
        i, j = rng.choice(len(normals), 2, replace=False)
        d = np.cross(normals[i], normals[j])
        n = np.linalg.norm(d)
        if n < 1e-9:
            continue
        d = d / n
        sep = math.degrees(math.acos(
            float(np.clip(abs(d @ reference), -1.0, 1.0))))
        if not (lo_deg <= sep <= hi_deg):
            continue                      # outside what a taper can be
        inl = np.abs(normals @ d) < math.sin(tol)
        if inl.sum() > best[0]:
            best = (int(inl.sum()), d, inl)
    if best[1] is None or best[0] < 3:
        return None
    count, d, inl = best
    _, _, vt = np.linalg.svd(normals[inl])
    d = vt[-1]
    if d @ best[1] < 0:
        d = -d
    sep = math.degrees(math.acos(float(np.clip(abs(d @ reference), -1.0, 1.0))))
    # The corridor gates the sample, but the SVD refit that follows can
    # walk the direction back out of it, and the refined separation was
    # returned regardless. That is how a 75-degree spread appeared on a
    # search whose whole range is 19 degrees wide: readings outside the
    # corridor are not tapers by the corridor's own definition.
    if not (lo_deg <= sep <= hi_deg):
        return None
    return {"direction": d, "inliers": np.asarray(inl), "count": int(inl.sum()),
            "separation_deg": float(sep)}


def taper(segments, fov_deg, width, height, corridor=(1.0, 20.0)):
    """Road first, then the taper edge inside the regulated corridor.

    The corridor's upper bound is deliberately generous - 20 degrees is
    four times steeper than 40 km/h requires - because the gate's job is to
    measure a taper that may be wrong, not to assume it is right. Its lower
    bound keeps the search off the lane line itself.
    """
    K = intrinsics(fov_deg, width, height)
    road = dominant_direction(segments, K)
    if road is None:
        return {"ok": False, "why": "no dominant direction; the road's own "
                                    "markings are not resolvable here"}
    rest = [s for s, keep in zip(segments, ~road["inliers"]) if keep]
    if len(rest) < 3:
        return {"ok": False, "road_count": road["count"],
                "why": f"only {len(rest)} segments once the road's own lines "
                       f"are removed; nothing left for a taper edge"}
    edge = corridor_direction(rest, K, road["direction"], *corridor)
    if edge is None:
        return {"ok": False, "road_count": road["count"],
                "remaining": len(rest),
                "why": f"no second direction between {corridor[0]:.0f} and "
                       f"{corridor[1]:.0f} degrees of the road, which is "
                       f"where a taper must lie"}
    sep = edge["separation_deg"]
    return {"ok": True, "road_count": road["count"],
            "road_residual_deg": round(road["residual_deg"], 3),
            "remaining": len(rest), "edge_count": edge["count"],
            "taper_deg": round(sep, 3), "taper_rate": round(math.tan(math.radians(sep)), 4),
            "road_direction": road["direction"].tolist(),
            "edge_direction": edge["direction"].tolist()}


def _image_line(segments):
    """A line fitted through a bundle of segments, in image coordinates."""
    pts = np.array([[x, y] for x1, y1, x2, y2 in segments
                    for x, y in ((x1, y1), (x2, y2))], float)
    c = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    d = vt[0] / np.linalg.norm(vt[0])
    return c, d, np.array([-d[1], d[0]])


def hatched_side(candidate_segments, others, K, reference_direction,
                 want_deg=45.0, tol_deg=14.0, reach_px=None, diag=None,
                 reach_frac=0.085):
    """Does this line have chevron arms along one side and not the other?

    §171 makes the chevron's boundary the line that borders hatching. A
    kerb line and a shadow edge also run within a few degrees of the road,
    which is why the corridor search alone returns 2.6 degrees on one
    capture and 15.6 on another; what none of them has is a population of
    marks at 45 degrees lying on one side of it.

    So the 45 is used to identify, not to filter. The score is how
    lopsided the arms are: a boundary has them on the hatched side only, a
    kerb line has none, and a line drawn down the middle of a chevron would
    have them on both and is rejected by the same asymmetry.
    """
    if len(others) < 3:
        return None
    # reach_px was a constant 140. A constant in pixels is a different
    # distance on the ground in every resolution, and that alone flipped
    # `borders` between 1000 and 1800 px on the same photograph. It is a
    # fraction of the diagonal now, so it means the same thing whatever
    # size the frame arrives at.
    if reach_px is None:
        reach_px = 140.0 if diag is None else reach_frac*diag
    c, d, n = _image_line(candidate_segments)
    K_inv = np.linalg.inv(K)
    left, right = 0.0, 0.0
    near_left, near_right = [], []       # how close the arms actually come
    for x1, y1, x2, y2 in others:
        mid = np.array([(x1+x2)/2, (y1+y2)/2])
        across = float((mid - c) @ n)
        if abs(across) > reach_px:
            continue
        a = K_inv @ np.array([x1, y1, 1.0])
        b = K_inv @ np.array([x2, y2, 1.0])
        dir3 = np.cross(np.cross(a, b), np.array([0.0, 0.0, 1.0]))
        m = np.linalg.norm(dir3)
        if m < 1e-9:
            continue
        # the arm's angle to this candidate, in 3D
        seg2 = np.array([x2-x1, y2-y1], float)
        s = seg2/np.linalg.norm(seg2)
        ang = math.degrees(math.acos(float(np.clip(abs(s @ d), -1, 1))))
        # A window on the arm's angle is a hard gate: an arm at 58.9
        # degrees counted and one at 59.1 did not, and compression moves
        # arms across that line. The angle now weights the arm instead of
        # admitting or refusing it, so nothing flips at a boundary.
        w_ang = math.exp(-0.5*((ang - want_deg)/tol_deg)**2)
        if w_ang < 0.05:
            continue
        w = math.hypot(x2-x1, y2-y1) * w_ang
        if across < 0:
            left += w; near_left.append(-across)
        else:
            right += w; near_right.append(across)
    total = left + right
    if total <= 0:
        return {"arms_total": 0.0, "lopsided": 0.0, "borders": False,
                "border_score": -6.0, "nearest_px": None}
    # Lopsidedness alone is trivially 1.0 for any line lying outside the
    # marking, because everything is then on one side of it. §171's word is
    # that the boundary *borders* the hatching, so the arms have to start at
    # it: the nearest arm on the hatched side must be close, and the far
    # side must be clear over the same distance.
    hatched_near = min(near_left) if left >= right else min(near_right)
    other_near = (min(near_right) if near_right else reach_px) if left >= right \
        else (min(near_left) if near_left else reach_px)
    # `borders` was two hard cutoffs and-ed together, and the same
    # physical line was bordering at JPEG quality 80 and not at 90 or 100.
    # The same two conditions, as a log-odds, say how much the arms look
    # like a border rather than whether they cross a line. It stays a
    # boolean for callers that want §171's yes or no, but the ranking uses
    # the graded score, so no candidate is admitted or dropped by a flip.
    near_ok = math.log(max(1e-6, 0.25*reach_px / max(hatched_near, 1e-6)))
    clear_ok = math.log(max(1e-6, other_near / max(2.0*hatched_near, 1e-6)))
    border_score = min(near_ok, 3.0) + min(clear_ok, 3.0)
    borders = hatched_near < 0.25*reach_px and other_near > 2.0*hatched_near
    return {"arms_total": total, "left": left, "right": right,
            "lopsided": abs(left - right)/total,
            "nearest_px": round(float(hatched_near), 1),
            "other_side_px": round(float(other_near), 1),
            "border_score": round(float(border_score), 3),
            "borders": bool(borders)}


def taper_with_hatching(segments, fov_deg, width, height,
                        corridor=(1.0, 20.0), attempts=6):
    """The corridor search, with §171 choosing between its candidates.

    The corridor narrows the search to where a taper can be. It does not
    say which of the lines in there is the chevron's boundary rather than
    the kerb or a shadow, and on this site's captures that ambiguity is
    the whole remaining spread - 2.64 to 15.58 degrees. Asking which
    candidate has hatching along one side answers it from the regulation.
    """
    K = intrinsics(fov_deg, width, height)
    road = dominant_direction(segments, K)
    if road is None:
        return {"ok": False, "why": "no dominant direction for the road"}
    rest = [s for s, keep in zip(segments, ~road["inliers"]) if keep]
    if len(rest) < 3:
        return {"ok": False, "why": f"only {len(rest)} segments off the road"}

    diag = math.hypot(width, height)
    sigma = math.radians(1.2)          # the RANSAC tolerance, as a spread

    def evidence(members, d):
        """How much better these segments are explained by d than by chance.

        The old score, arms x lopsided, weighed how much hatching borders a
        line and how one-sided it is. Both are properties of the line's
        surroundings; neither asks how much of the image actually supports
        the line. So a group of 3 segments could and did beat a group of
        30, and which of them won moved with the JPEG quality.

        A log-likelihood ratio asks the question the old score left out.
        Each member contributes log(foreground / background) for its own
        angular residual to the direction - a Gaussian of the RANSAC
        tolerance against a uniform over all the residuals a line could
        have - weighted by how long the segment is. Evidence then
        accumulates: thirty members outweigh three, and a long segment
        outweighs a short one, because that is what more evidence means.
        """
        if not members:
            return float("-inf")
        n = _great_circles(members, K_inv)
        if len(n) == 0:
            return float("-inf")
        r = np.arcsin(np.clip(np.abs(n @ d), 0.0, 1.0))
        w = np.array([math.hypot(x2-x1, y2-y1)/diag
                      for x1, y1, x2, y2 in members])[:len(n)]
        fg = -0.5*(r/sigma)**2 - math.log(sigma*math.sqrt(2*math.pi))
        bg = math.log(2.0/math.pi)
        return float(np.sum(w * (fg - bg)))

    K_inv = np.linalg.inv(K)
    tried, pool = [], list(rest)
    for k in range(attempts):
        edge = corridor_direction(pool, K, road["direction"], *corridor,
                                  seed=k)
        if edge is None:
            break
        members = [s for s, keep in zip(pool, edge["inliers"]) if keep]
        rest_of = [s for s in rest if s not in members]
        h = hatched_side(members, rest_of, K, road["direction"], diag=diag)
        tried.append({"taper_deg": round(edge["separation_deg"], 3),
                      "members": edge["count"],
                      "evidence": round(evidence(members, edge["direction"]), 2),
                      "arms": 0.0 if h is None else round(h["arms_total"], 1),
                      "border_score": -6.0 if h is None else h["border_score"],
                      "lopsided": 0.0 if h is None else round(h["lopsided"], 3),
                      "nearest_px": None if h is None else h.get("nearest_px"),
                      "borders": bool(h and h.get("borders"))})
        pool = [s for s, keep in zip(pool, ~edge["inliers"]) if keep]
        if len(pool) < 3:
            break

    if not tried:
        return {"ok": False, "why": "no candidate inside the corridor"}
    # the boundary is the candidate with the most hatching, and lopsided
    scored = [t for t in tried if t.get("borders")]
    if not scored:
        return {"ok": False, "candidates": tried,
                "why": "no candidate in the corridor borders hatching - arms "
                       "on one side, starting at the line, with the other "
                       "side clear. §171's boundary is not among them"}
    # §171 says which candidates are eligible - a boundary has hatching
    # starting at it on one side and clear on the other. Among those, the
    # one the image most supports wins.
    #
    # Eligibility used to be a boolean, and the same physical line was
    # eligible at JPEG quality 80 and not at 90 or 100. Ranking now adds
    # the graded bordering score to the alignment evidence, so a candidate
    # that is marginally bordering is ranked slightly lower rather than
    # dropped. The boolean is kept only to decide whether any candidate
    # resembles §171's boundary at all.
    pick = max(tried, key=lambda t: t["evidence"] + 0.25*t["border_score"])
    return {"ok": True, "taper_deg": pick["taper_deg"],
            "taper_rate": round(math.tan(math.radians(pick["taper_deg"])), 4),
            "arms_length_px": pick["arms"], "lopsided": pick["lopsided"],
            "evidence": pick["evidence"], "members": pick["members"],
            "road_count": road["count"], "candidates": tried}
