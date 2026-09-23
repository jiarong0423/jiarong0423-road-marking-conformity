"""One call: a photograph of a lane taper in, a verdict out, or a refusal.

The verdict answers the question the site poses - is the taper long enough
for a driver to react to it - by comparing the taper rate the marking
actually has against the rate 施工之交通管制守則 requires at the posted
speed. Both are dimensionless, so no camera height is needed and none is
asked for.

Three states, and the third is the point:

    WITHIN_REFERENCE         clear of the reference by more than the doubt
    STEEPER_THAN_REFERENCE   past it by more than the doubt
    INDETERMINATE            nearer the reference than the doubt allows
    CANNOT_MEASURE           the image does not support a measurement

The third and fourth are different refusals. CANNOT_MEASURE means the
photograph does not show what it needs to show. INDETERMINATE means it does,
the measurement succeeded, and the answer still cannot be given because the
rate sits inside the guard band. Reporting the second as a verdict is how a
measurement becomes an accusation: at the 50 km/h this road carried before
the works, the reference rate is 0.062 and this site measures 0.070, which
without a guard band reads as a breach and with one reads as not knowing.

The first two are deliberately not called compliant and non-compliant. The
formula they use is 施工之交通管制守則, written by 高速公路局 for national
freeways, and this site is a 縣道; whether it applies to that road class as
a matter of law is not settled, and docs/markings-regulation.md records that
as unresolved. A gate that returned "does not comply" would be asserting a
legal finding this project has not earned. It returns a measurement against
a named reference, and says whose reference it is.

Six numbers produced during this project's development were wrong, and every
one of them would have been returned as a confident verdict by a gate without
the third state. The checks that reject them are not tuned thresholds; each
is a property the regulation fixes, so failing one means the thing being
measured is not the marking:

    §171  the chevron's arms lie at 45 degrees to its band. A family of
          lines that does not is not the arms, whatever else it is. This
          alone rejects the 84.1%, the 25% and the 16%.
    §171  the arms repeat every 50 cm - 20 cm of paint, 30 cm of gap.

One thing §171 does not fix is the datum for its 45 degrees: relative to the
direction of travel, to the road's centreline, or to the chevron's own
boundary line. On a straight road all three agree and nobody notices; on a
taper, which is where chevrons mostly are, they differ. The angle here is
measured against the chevron's own boundary, and every result says so,
because picking one datum silently would be passing my choice off as the
regulation's.

Measurement happens in the bird's eye plane, where a kernel is a length and
a measured angle is a ground angle. The frontal image is where the earlier
failures lived.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field

import cv2
import numpy as np

from .rectify import focal_px

PX_PER_H = 260.0          # bird's eye pixels per camera height
NEAR, FAR = 0.6, 4.0      # camera heights ahead; IPM assumes flat ground
HALF = 2.2                # camera heights either side
ARM_TO_BAND = 45.0        # degrees, 設置規則 §171 斜四五度
ARM_TOLERANCE = 12.0      # degrees; wider than paint is laid, narrow enough
                          # that a bisector at 0-15 degrees cannot pass

# The guard band, under JCGM 106. Two terms, and the larger one is mine.
#
#   construction  第02898章 標線 §3.3.4 puts a marking's lateral position
#                 within ±5 cm of the drawing. Both ends of a 14.9 m taper
#                 independently at that limit contributes 0.0047 to the rate.
#   measurement   three captures of one taper from one viewpoint, differing
#                 only in lens, returned 0.080, 0.068 and 0.062: sd 0.0092.
#
# So the band is set by this pipeline rather than by the painting, and the
# way to decide more cases is to measure better. n = 3 is thin and this
# number will move.
RATE_SD = 0.0092          # spread of the pipeline itself, three captures
GUARD_K = 2.0

# The term that was missing, and it is the one that matters.
#
# `road_bearing_deg` is supplied by the caller, and the rate moves 0.0157
# per degree of it - measured by sweeping it, not assumed. The number this
# project used, 141.6, had no derivation. scripts/road_bearing.py measures
# it two independent ways and neither is good enough:
#
#   four field points     144.17 +- 8.10 deg   (they scatter 3.3 m across)
#   eight panorama tracks 139.57 +- 7.19 deg   (3.5 m, a car weaving in lane)
#   and they disagree by  4.60 deg
#
# Carrying the disagreement, the bearing is 141.87 +- 8.32 deg, which is
# +-0.131 on the rate: fourteen times the pipeline's own spread, and larger
# than every reference rate this gate compares against (0.172 at 30 km/h,
# 0.062 at 50, 0.043 at 60).
#
# So no taper verdict here is supportable, and the gate now says so instead
# of returning one. The fix is not a better external number: it is to
# measure the road's direction from the same frame as the chevron, where
# the common error cancels. Until that is built, this stands.
BEARING_SE_DEG = 8.32
RATE_PER_DEG = 0.0157


@dataclass
class Verdict:
    state: str          # WITHIN_REFERENCE | STEEPER_THAN_REFERENCE | CANNOT_MEASURE
    reason: str
    basis: dict = field(default_factory=lambda: {
        "taper_formula": "L = W_L·V²/155 (V <= 60 km/h)",
        "formula_source": "施工之交通管制守則, 交通部臺灣區國道高速公路局, "
                          "96年11月修訂, 第9頁",
        "formula_applies_to": "國道. Applicability to 縣道 is NOT established; "
                              "this is a measurement against that reference, "
                              "not a finding of non-compliance",
        "angle_datum": "the chevron's own 周圍邊線. §171 says 斜四五度 but "
                       "does not state the datum; on a taper the three "
                       "candidate datums differ",
        "geometry_source": "道路交通標誌標線號誌設置規則 §171",
        "guard_band": "JCGM 106, k=2. Construction tolerance ±5 cm on a "
                      "marking's lateral position, given identically by "
                      "交通部高速公路局 施工技術規範 107/03 第02898章 "
                      "§3.1(7)D and 臺北市政府 第02898章 TPE V4.0 111/04 "
                      "§3.3.4 - a central agency and a city, seven years "
                      "apart, so a national figure rather than a local one. "
                      "Measurement sd 0.0092 from three captures of one "
                      "taper, n=3, which is the larger term",
    })
    taper_rate: float | None = None
    required_rate: float | None = None
    ratio_too_steep: float | None = None
    posted_kmh: float | None = None
    equivalent_kmh: float | None = None
    band_deg: float | None = None
    arm_deg: float | None = None
    arm_to_band_deg: float | None = None
    arms: int = 0
    checks: dict = field(default_factory=dict)

    def as_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


def _required_rate(posted_kmh: float) -> float:
    """W/L from L = W·V²/155, 施工之交通管制守則 p.9, for V <= 60."""
    return 155.0 / (posted_kmh ** 2)


def _birdseye(image, fov_deg, pitch_deg):
    height, width = image.shape[:2]
    f = focal_px(fov_deg, width)
    t = math.radians(pitch_deg)
    rotate = np.array([[1, 0, 0],
                       [0, math.cos(t), -math.sin(t)],
                       [0, math.sin(t), math.cos(t)]])
    out_w = int(2 * HALF * PX_PER_H)
    out_h = int((FAR - NEAR) * PX_PER_H)
    jj, ii = np.meshgrid(np.arange(out_w), np.arange(out_h))
    ground = np.stack([(jj - out_w / 2) / PX_PER_H,
                       np.ones_like(jj, dtype=float),
                       FAR - ii / PX_PER_H], -1)
    cam = ground @ rotate
    with np.errstate(divide="ignore", invalid="ignore"):
        u = cam[..., 0] / cam[..., 2] * f + width / 2
        v = cam[..., 1] / cam[..., 2] * f + height / 2
    bad = (cam[..., 2] <= 1e-6) | ~np.isfinite(u) | ~np.isfinite(v)
    u[bad] = -1
    v[bad] = -1
    return cv2.remap(image, u.astype(np.float32), v.astype(np.float32),
                     cv2.INTER_LINEAR, borderValue=0)


def _paint(bev):
    lightness = cv2.cvtColor(bev, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    covered = bev.sum(2) > 0
    # the background scale is a length: 30 cm of road, not a pixel count
    local = cv2.GaussianBlur(lightness, (0, 0), 0.30 * PX_PER_H)
    mask = ((lightness - local) > 12) & covered
    return cv2.morphologyEx(mask.astype(np.uint8) * 255, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))), covered


def _directions(paint, road_in_bev):
    """The chevron's boundary and its arms, told apart by the road.

    Not by which carries the most line length. A chevron has many arms and
    one or two boundary lines, so the arms win that contest, and taking the
    strongest as the boundary swapped the two on every capture here: the
    45-degree check still passed, because the pair really are 45 degrees
    apart, and the taper rate came out five times too steep.

    The boundary is the family that runs with the road, which is why the
    road's bearing is an argument. The arms are then the family §171 puts
    45 degrees from it.
    """
    edges = cv2.Canny(paint, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, int(0.12 * PX_PER_H),
                            minLineLength=int(0.25 * PX_PER_H),
                            maxLineGap=int(0.06 * PX_PER_H))
    if lines is None:
        return None
    seg = lines.reshape(-1, 4)
    angle = np.array([math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
                      for x1, y1, x2, y2 in seg])
    weight = np.array([math.hypot(x2 - x1, y2 - y1) for x1, y1, x2, y2 in seg])
    hist, _ = np.histogram(angle, bins=180, range=(0, 180), weights=weight)
    hist = np.convolve(np.r_[hist, hist, hist], np.ones(5) / 5, "same")[180:360]

    def off(a, b):
        return abs(((a - b + 90) % 180) - 90)

    # the boundary runs with the road: strongest direction within 30 degrees
    near_road = [(hist[i], i) for i in range(180)
                 if off(i, road_in_bev) <= 30.0]
    if not near_road:
        return None, None, None, len(seg)
    band = max(near_road)[1]
    window = [(hist[i], i) for i in range(180)
              if abs(off(i, band) - ARM_TO_BAND) <= ARM_TOLERANCE]
    if not window:
        return band, None, None, len(seg)
    arm = max(window)[1]
    return band, arm, float(off(arm, band)), len(seg)


def assess(image, fov_deg: float, pitch_deg: float, posted_kmh: float,
           heading_deg: float | None = None,
           road_bearing_deg: float | None = None) -> Verdict:
    """The whole gate. Everything it refuses, it refuses for a stated reason.

    `heading_deg` is where the camera looked and `road_bearing_deg` is where
    the road runs, both as compass bearings. The gate needs the difference
    and will not guess it. Taking the bird's eye image's own vertical as the
    road - which is the camera's forward direction, not the road's - put the
    taper rate at 1.88 instead of 0.202 on this site's own photographs,
    because the camera was pointing 13.6 degrees off the carriageway.

    That is the same fault as sorting lines into "road" and "edge" by which
    angle window they fall in: an assumption about where the camera was
    aimed, buried where it does not show up in the answer. The road's
    direction is a fact about the road, so it is an input.
    """
    checks = {}
    if heading_deg is None or road_bearing_deg is None:
        return Verdict("CANNOT_MEASURE",
                       "the camera's heading and the road's bearing are both "
                       "needed: a taper rate is measured against the road, "
                       "and the photograph only knows where the camera was "
                       "pointed",
                       checks={"heading_given": heading_deg is not None,
                               "road_bearing_given": road_bearing_deg is not None})
    # in the bird's eye plane the camera looks up the image, so the road sits
    # at 90 degrees plus however far it runs off the camera's heading
    off = ((road_bearing_deg - heading_deg + 180.0) % 360.0) - 180.0
    road_in_bev = (90.0 + off) % 180.0
    checks["camera_to_road_deg"] = round(off, 2)
    checks["road_direction_in_bev_deg"] = round(road_in_bev, 2)
    bev = _birdseye(image, fov_deg, pitch_deg)
    paint, covered = _paint(bev)
    checks["near_field_in_frame"] = round(float(covered.mean()), 3)
    if covered.mean() < 0.35:
        return Verdict("CANNOT_MEASURE",
                       f"only {covered.mean()*100:.0f}% of the near field is in "
                       f"the photograph; the ground plane is mostly off-frame",
                       checks=checks)

    found = _directions(paint, road_in_bev)
    if found is None:
        return Verdict("CANNOT_MEASURE", "no line segments in the near field",
                       checks=checks)
    band, arm, sep, nseg = found
    checks["line_segments"] = nseg
    if band is None:
        return Verdict("CANNOT_MEASURE",
                       "no line family runs within 30 degrees of the road, so "
                       "the chevron's boundary is not in this photograph",
                       checks=checks)
    if arm is None:
        return Verdict("CANNOT_MEASURE",
                       f"no family of lines lies {ARM_TO_BAND:.0f} +- "
                       f"{ARM_TOLERANCE:.0f} degrees from the dominant "
                       f"direction, so the chevron's arms are not present "
                       f"(§171)",
                       band_deg=float(band), checks=checks)

    # separate the arms from the boundary lines by direction, not by size
    def line_element(metres, deg):
        n = max(3, int(metres * PX_PER_H)) | 1
        k = np.zeros((n, n), np.uint8)
        c, t = n // 2, math.radians(deg)
        for s in np.linspace(-n / 2, n / 2, n * 4):
            x, y = int(round(c + s * math.cos(t))), int(round(c + s * math.sin(t)))
            if 0 <= x < n and 0 <= y < n:
                k[y, x] = 1
        return k

    arms_mask = cv2.morphologyEx(paint, cv2.MORPH_OPEN, line_element(0.45, arm))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(arms_mask, 8)
    axis = np.array([math.cos(math.radians(arm)), math.sin(math.radians(arm))])
    measured = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < (0.09 * PX_PER_H) ** 2:
            continue
        ys, xs = np.nonzero(lbl == i)
        pts = np.stack([xs, ys], 1).astype(np.float32)
        centre = pts.mean(0)
        along = (pts - centre) @ axis
        if along.max() - along.min() < 0.35 * PX_PER_H:
            continue
        _, _, v = np.linalg.svd(pts - centre, full_matrices=False)
        measured.append((centre,
                         math.degrees(math.atan2(v[0][1], v[0][0])) % 180))
    checks["arms"] = len(measured)
    if len(measured) < 5:
        return Verdict("CANNOT_MEASURE",
                       f"only {len(measured)} arms survive; a chevron shows "
                       f"more and a measurement from this many would not be "
                       f"one", band_deg=float(band), arm_deg=float(arm),
                       arms=len(measured), checks=checks)

    # re-measure the angle on what was actually kept. The direction above
    # was looked for in a 45-degree window, so it cannot be its own check.
    z = np.exp(2j * np.radians(np.array([a for _, a in measured])))
    coherence = float(abs(z.sum()) / len(z))
    remeasured = abs(((math.degrees(np.angle(z.sum()) / 2) - band + 90) % 180) - 90)
    checks["arm_angle_coherence"] = round(coherence, 3)
    checks["arm_to_band_remeasured_deg"] = round(remeasured, 1)
    if coherence < 0.55:
        return Verdict("CANNOT_MEASURE",
                       f"the arms do not share a direction (coherence "
                       f"{coherence:.2f}); they are not one marking",
                       band_deg=float(band), arm_deg=float(arm),
                       arms=len(measured), checks=checks)
    if abs(remeasured - ARM_TO_BAND) > ARM_TOLERANCE:
        return Verdict("CANNOT_MEASURE",
                       f"the arms kept lie {remeasured:.0f} degrees from the "
                       f"band, not the {ARM_TO_BAND:.0f} of §171, so they are "
                       f"not the chevron's arms",
                       band_deg=float(band), arm_deg=float(arm),
                       arm_to_band_deg=round(remeasured, 1),
                       arms=len(measured), checks=checks)

    # The taper rate is a chord, not a tangent.
    #
    # 施工之交通管制守則 defines it as L = W_L·V²/155, and the MUTCD as
    # L = WS²/60: in both, W is the total lateral offset and L the total
    # longitudinal run. That is an end-to-end quantity. The angle of the
    # boundary at any one place along it is not, and a real taper is eased
    # at its ends rather than laid out as one straight line.
    #
    # Measuring the local direction instead gave rates from 0.063 to 0.168
    # on four captures of one taper, and the spread was not noise: a 40
    # degree lens frames the steep middle, a 90 degree lens takes in the
    # eased ends as well and flattens the dominant direction. The estimator
    # was reading the lens.
    #
    # So the chord is taken between the ends of the boundary, and if both
    # ends are not in the photograph there is no chord to take. That is a
    # refusal. Falling back to the local angle would be answering a
    # different question quietly.
    road_dir = np.array([math.cos(math.radians(road_in_bev)),
                         math.sin(math.radians(road_in_bev))])
    road_nrm = np.array([-road_dir[1], road_dir[0]])
    boundary = cv2.morphologyEx(paint, cv2.MORPH_OPEN, line_element(1.2, band))
    bn, blbl, bst, _ = cv2.connectedComponentsWithStats(boundary, 8)
    runs = [i for i in range(1, bn) if bst[i, cv2.CC_STAT_AREA] > (0.15 * PX_PER_H) ** 2]
    if not runs:
        return Verdict("CANNOT_MEASURE",
                       "the chevron's boundary line is not long enough to "
                       "take a chord from", band_deg=float(band),
                       arm_deg=float(arm), arms=len(measured), checks=checks)
    keep = max(runs, key=lambda i: bst[i, cv2.CC_STAT_AREA])
    ys, xs = np.nonzero(blbl == keep)
    pts = np.stack([xs, ys], 1).astype(np.float32)
    along = pts @ road_dir
    across = pts @ road_nrm
    run_m = float(along.max() - along.min()) / PX_PER_H
    checks["boundary_run_camera_heights"] = round(run_m, 2)
    # the chord needs enough of the taper to be a chord and not a tangent
    if run_m < 1.5:
        return Verdict("CANNOT_MEASURE",
                       f"only {run_m:.1f} camera heights of the boundary are "
                       f"in frame; a chord over so little is a tangent by "
                       f"another name, and the taper is defined end to end",
                       band_deg=float(band), arm_deg=float(arm),
                       arms=len(measured), checks=checks)
    # robust ends: the 5th and 95th percentile along the road, so a stray
    # pixel at either extreme cannot set the chord
    lo_cut, hi_cut = np.percentile(along, 5), np.percentile(along, 95)
    lo_side = across[along <= np.percentile(along, 15)]
    hi_side = across[along >= np.percentile(along, 85)]
    offset = abs(float(np.median(hi_side) - np.median(lo_side))) / PX_PER_H
    run = float(hi_cut - lo_cut) / PX_PER_H
    checks["chord_offset_camera_heights"] = round(offset, 3)
    checks["chord_run_camera_heights"] = round(run, 3)
    if run <= 0:
        return Verdict("CANNOT_MEASURE", "the boundary has no extent along "
                       "the road", checks=checks)
    rate = offset / run
    rel = math.degrees(math.atan(rate))
    required = _required_rate(posted_kmh)
    if rate <= 0:
        return Verdict("CANNOT_MEASURE", "the band is parallel to the road; "
                       "there is no taper here", checks=checks)
    ratio = rate / required
    equivalent = math.sqrt(155.0 / rate)
    bearing_term = RATE_PER_DEG * BEARING_SE_DEG
    guard = GUARD_K * math.hypot(RATE_SD, bearing_term)
    checks["guard_band"] = round(guard, 4)
    checks["guard_from_pipeline"] = round(GUARD_K * RATE_SD, 4)
    checks["guard_from_road_bearing"] = round(GUARD_K * bearing_term, 4)
    checks["decides_within_below"] = round(required - guard, 4)
    checks["decides_steeper_above"] = round(required + guard, 4)
    common = dict(taper_rate=round(rate, 3), required_rate=round(required, 3),
                  ratio_too_steep=round(ratio, 2), posted_kmh=posted_kmh,
                  equivalent_kmh=round(equivalent, 1), band_deg=float(band),
                  arm_deg=float(arm), arm_to_band_deg=round(remeasured, 1),
                  arms=len(measured), checks=checks)
    checks["band_to_road_deg"] = round(rel, 2)
    if abs(rate - required) <= guard:
        return Verdict("INDETERMINATE",
                       f"the taper measures {rate:.3f} against a reference of "
                       f"{required:.3f} at {posted_kmh:.0f} km/h, and the two "
                       f"are closer than the +-{guard:.3f} this measurement "
                       f"can resolve. Neither answer is available", **common)
    if rate < required:
        return Verdict("WITHIN_REFERENCE",
                       f"the taper is clear of what the reference asks at "
                       f"{posted_kmh:.0f} km/h by more than the "
                       f"+-{guard:.3f} of doubt", **common)
    return Verdict("STEEPER_THAN_REFERENCE",
                   f"the taper is {ratio:.1f} times steeper than the reference "
                   f"asks at {posted_kmh:.0f} km/h, by more than the "
                   f"+-{guard:.3f} of doubt; its geometry suits about "
                   f"{equivalent:.0f} km/h", **common)
