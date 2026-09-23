"""The gate, rebuilt on what the camera cannot spoil.

The first gate rectified the image with the pitch the Street View API
reported and compared the chevron's boundary against a road bearing the
caller typed in. Both inputs turned out to be unavailable: the API's pitch
carries a degree or two of the survey car's suspension, and the bearing
measured 141.87 ± 8.32° two independent ways, which is ±0.131 on a rate
whose thresholds are 0.172, 0.062 and 0.043. It answered INDETERMINATE to
everything, correctly.

Nothing here uses either.

A family of parallel ground lines meets at a vanishing point v; its 3D
direction is K⁻¹v with K holding only the focal length; and the angle
between two directions does not change when the camera rotates. So the
chevron's boundary, its arms and the road each supply their own direction
from the same photograph, and the taper rate is the angle between two of
them. Pitch and bearing are not bounded here, they are absent.

Which family is which is decided by §171 rather than by an angle window -
the mistake that produced 18.3 and 18.7 km/h under two different names:

    the arms lie 45° from the boundary, so the pair of families whose
    angle is nearest 45° is the chevron, and that identifies both at once
    the road is then the remaining family closest to the boundary, because
    a taper departs from the road by a few degrees, not by forty-five

If no pair sits near 45° there is no chevron in the photograph and the gate
says so. If no third family remains, the road's own direction is not
visible and the gate says that instead. Neither is a fallback to something
weaker.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

import cv2
import numpy as np

from .extract import markings, road_region
from .vanishing import intrinsics, vanishing_point, angle_between, angle_uncertainty
from .sequential import taper_with_hatching

ARM_TO_BAND = 45.0        # 設置規則 §171, 斜四五度
ARM_TOL = 12.0
ROAD_MAX_DEV = 25.0
GUARD_K = 2.0

# The spread across the four captures that agree, in degrees. Grouping by
# angle produced nothing usable; the sequential search with §171's
# bordering rule gives 10.40, 11.21, 10.07 and 10.01 over three fields of
# view, three pitches and two panorama positions. n = 4 is thin and this
# will move, which is said in the basis rather than left to be discovered.
ANGLE_SD_DEG = 0.55


@dataclass
class Verdict:
    state: str
    reason: str
    taper_rate: float | None = None
    required_rate: float | None = None
    posted_kmh: float | None = None
    taper_deg: float | None = None
    taper_deg_sd: float | None = None
    arm_to_boundary_deg: float | None = None
    guard_band: float | None = None
    families: dict | None = None
    basis: dict = field(default_factory=lambda: {
        "angle": "from vanishing points and K; invariant to camera rotation, "
                 "so no pitch, no road bearing and no scale are used",
        "identification": "the road is the dominant direction by RANSAC on "
                          "the sphere; its segments are removed; the taper "
                          "edge is searched only 1-20° from it, the range "
                          "the taper formula defines; and §171 picks it out "
                          "as the candidate that borders hatching",
        "uncertainty_basis": "0.55° from four captures that agree (10.40, "
                             "11.21, 10.07, 10.01) across three fields of "
                             "view, three pitches and two panorama "
                             "positions. n=4 is thin",
        "taper_formula": "L = W·V²/155 (V ≤ 60), 施工之交通管制守則 p.9, "
                         "交通部臺灣區國道高速公路局",
        "formula_applies_to": "國道. 新北市's own chain - 施工期間使用道路交通"
                              "維持作業規定, 設置規則, 道路挖掘作業審查原則 - "
                              "states no taper length at all, so this is a "
                              "measurement against a reference nothing here "
                              "imposes, not a finding of non-compliance",
        "uncertainty": "line endpoints jittered 1.5 px, 200 draws, which asks "
                       "where a threshold fell on a painted edge",
    })

    def as_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


def _segments(image):
    """Marking-shaped line segments inside the trafficable surface.

    `roi` was `carriageway()`, which decides by surface uniformity. It
    keeps walls, which are uniform, and rejects asphalt that has been
    dug and patched, which this road is. ANDing the paint mask with it
    therefore deleted the markings and kept the clutter: drawn on F07
    on 2026-09-22, every segment sat on the site scaffolding, the
    hoarding panels and the strokes of a painted character, and the
    double white line running across the middle of the frame - plainly
    visible, the thing the §167 detector exists to find - carried not
    one segment.

    Everything downstream reads this. The §167 detector was rebuilt
    four times against an input that did not contain its target.
    """
    roi = road_region(image)
    mask, _, _ = markings(image, min_response=8.0)
    if roi is not None:
        mask = cv2.bitwise_and(mask, roi)
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/720, 40,
                            minLineLength=max(25, image.shape[1]//25),
                            maxLineGap=6)
    if lines is None:
        return [], roi
    return [tuple(map(float, s)) for s in lines.reshape(-1, 4)], roi


def _families(segs, min_members=3, window=9.0):
    """Group segments by image bearing. Grouping, not identification."""
    if not segs:
        return []
    ang = np.array([math.degrees(math.atan2(y2-y1, x2-x1)) % 180
                    for x1, y1, x2, y2 in segs])
    wt = np.array([math.hypot(x2-x1, y2-y1) for x1, y1, x2, y2 in segs])
    hist, _ = np.histogram(ang, bins=180, range=(0, 180), weights=wt)
    hist = np.convolve(np.r_[hist, hist, hist], np.ones(5)/5, "same")[180:360]
    out, taken = [], np.zeros(180, bool)
    for i in np.argsort(hist)[::-1]:
        if taken[i] or hist[i] <= 0:
            continue
        lo = [(i + d) % 180 for d in range(-int(window), int(window)+1)]
        if any(taken[j] for j in lo):
            continue
        for j in lo:
            taken[j] = True
        members = [s for s, a in zip(segs, ang)
                   if min(abs(a-i), 180-abs(a-i)) <= window]
        if len(members) >= min_members:
            out.append({"deg": float(i), "segments": members,
                        "length": float(sum(math.hypot(x2-x1, y2-y1)
                                            for x1, y1, x2, y2 in members))})
        if len(out) >= 5:
            break
    return out


def assess(image, fov_deg: float, posted_kmh: float) -> Verdict:
    """A photograph and the lens it was taken with. Nothing about the pose.

    Three inputs the previous gate needed and could not have - the camera's
    pitch, the road's bearing and a metric scale - are absent here rather
    than bounded. What replaces them: the road's own markings supply its
    direction, the angle between two directions is invariant to camera
    rotation, and a rate is dimensionless.
    """
    h, w = image.shape[:2]
    segs, roi = _segments(image)
    info = {"segments": len(segs), "roi_found": roi is not None}
    if len(segs) < 6:
        return Verdict("CANNOT_MEASURE",
                       f"{len(segs)} marking-shaped line segments on the "
                       f"carriageway; too few to find a direction",
                       families=info)

    r = taper_with_hatching(segs, fov_deg, w, h)
    info["candidates"] = r.get("candidates")
    info["road_segments"] = r.get("road_count")
    if not r.get("ok"):
        return Verdict("CANNOT_MEASURE", r.get("why", "no taper found"),
                       families=info)

    deg = r["taper_deg"]
    rate = r["taper_rate"]
    required = 155.0 / posted_kmh**2
    # the doubt in the rate follows from the doubt in the angle
    rate_sd = abs(math.tan(math.radians(deg + ANGLE_SD_DEG)) - rate)
    guard = GUARD_K * rate_sd
    info["arms_length_px"] = r.get("arms_length_px")
    info["borders_hatching"] = True
    common = dict(taper_rate=round(rate, 4), required_rate=round(required, 4),
                  posted_kmh=posted_kmh, taper_deg=round(deg, 2),
                  taper_deg_sd=ANGLE_SD_DEG, guard_band=round(guard, 4),
                  families=info)
    if abs(rate - required) <= guard:
        return Verdict("INDETERMINATE",
                       f"the taper measures {rate:.3f} against {required:.3f} "
                       f"at {posted_kmh:.0f} km/h, closer than the "
                       f"±{guard:.3f} this measurement resolves", **common)
    if rate < required:
        return Verdict("WITHIN_REFERENCE",
                       f"clear of the reference at {posted_kmh:.0f} km/h by "
                       f"more than the ±{guard:.3f} of doubt", **common)
    return Verdict("STEEPER_THAN_REFERENCE",
                   f"{rate/required:.1f} times steeper than the reference at "
                   f"{posted_kmh:.0f} km/h, by more than the ±{guard:.3f} of "
                   f"doubt; the geometry suits about "
                   f"{math.sqrt(155/rate):.0f} km/h", **common)
