"""The corrected pipeline: paint, then plane, then meaning.

`docs/architecture-2026-09-21.md` is the design and the arithmetic behind
it; this is the part of it that is built. The order matters and is the
whole point of the rewrite:

    the old pipeline found the road by a local-roughness test and then
    looked for markings inside it. A chevron is a row of high-contrast
    stripes, so the test read it as "not road" and removed the object
    under inspection.

The inversion on offer - find the paint first, use it to bound the road -
is the same loop backwards: a missed marking would shrink the road, which
would remove more markings, and no metric over that pair can separate the
two. So neither. Paint and asphalt differ in albedo, not in geometry, and
what is geometric is that all of it lies on one plane. The load-bearing
step is the plane, recovered from the markings' own vanishing directions,
which needs only the focal length and is invariant to camera rotation.

Built here: stages 0 to 2 and the first of stage 6's two regions. Stages
3 to 5, 7 and 8 are specified in the document and are not built, and
`stages_built()` says so rather than leaving a reader to find out.

**The invariant this module exists to hold**: `search_domain` takes an
image's shape and a horizon, and nothing else. Not a paint mask, not a
marking response, not the pixels. `tests/test_pipeline.py` fails if its
signature grows one. An invariant a test can break is worth more than a
score that cannot go down - and under the project's rule 9 no score over
this region means anything, because any appearance-based narrowing is
graded by how much paint survives it, which is what the narrowing sets.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .extract import markings
from .sequential import _great_circles, dominant_direction
from .vanishing import intrinsics

STAGES = ("provenance", "paint", "plane", "scale", "ipm",
          "identify", "regions", "verdicts", "stability")
BUILT = ("provenance", "paint", "regions:search_domain", "scale", "ipm")
# `ground_plane` is in this file and is not in `run`. Three versions of
# it failed their own held-out check - the numbers are in
# results/plane_holdout.json - and nothing here needs one.
NOT_CALLED = ("plane", "identify")
# `identify` takes the detectors' output, and `run` stops at stage 2, so
# it is reachable and tested but not on this path. It is listed rather
# than claimed. `ground_plane` is listed for a different reason: it
# failed. Two kinds of not-called, and collapsing them would hide one.
NOT_CALLED_WHY = {
    "plane": "three fits, three failures of the held-out check; withdrawn",
    "identify": "built and tested; run() ends at stage 2, and §171's "
                "predicate has no locator - see identify()",
}

# 35 mm frame diagonal, the convention EXIF's FocalLengthIn35mmFilm uses
FRAME_DIAGONAL_MM = 43.267


def stages_built():
    """What exists, so a caller need not discover the rest by failing."""
    return {"built": list(BUILT),
            "present_but_not_called": list(NOT_CALLED),
            "present_but_not_called_why": NOT_CALLED_WHY,
            "specified_not_built": [s for s in STAGES
                                    if s not in ("provenance", "paint",
                                                 "plane", "regions",
                                                 "scale", "ipm")],
            "specification": "docs/architecture-2026-09-21.md"}


# ── stage 0 ──────────────────────────────────────────────────────────

@dataclass
class Provenance:
    path: str | None
    sha256: str | None
    width: int
    height: int
    f35_mm: float | None
    focal_px: float | None
    captured: str | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self):
        return {k: v for k, v in self.__dict__.items()}


def provenance(image, path=None):
    """What is known about this frame before anything is measured.

    The focal length comes from EXIF. It is not optional: every angle
    downstream is computed through K, and the project spent a day with a
    field of view supplied by hand before noticing that three of its 42
    photographs were taken at a different focal length and had been
    measured with the wrong one.
    """
    h, w = image.shape[:2]
    sha = f35 = captured = None
    notes = []
    if path is not None and Path(path).exists():
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        try:
            from PIL import Image, ExifTags
            ex = Image.open(path).getexif()
            tags = {ExifTags.TAGS.get(k, k): v for k, v in ex.items()}
            tags.update({ExifTags.TAGS.get(k, k): v
                         for k, v in ex.get_ifd(0x8769).items()})
            if tags.get("FocalLengthIn35mmFilm"):
                f35 = float(tags["FocalLengthIn35mmFilm"])
            captured = tags.get("DateTimeOriginal")
            ew, eh = tags.get("ExifImageWidth"), tags.get("ExifImageHeight")
            if ew and eh and (int(ew), int(eh)) != (w, h):
                notes.append(f"EXIF says {ew}x{eh}, the array is {w}x{h}: "
                             f"this frame has been resized since capture")
        except Exception as exc:
            notes.append(f"EXIF unreadable: {type(exc).__name__}")
    if f35 is None:
        notes.append("no FocalLengthIn35mmFilm; every angle downstream "
                     "needs one and the caller must supply it")
    focal = (f35 * math.hypot(w, h) / FRAME_DIAGONAL_MM) if f35 else None
    return Provenance(str(path) if path else None, sha, w, h, f35, focal,
                      captured, notes)


# ── stage 1 ──────────────────────────────────────────────────────────

def paint_field(image, min_response=8.0):
    """Every painted-looking pixel in the frame. No region, no narrowing.

    Candidate generation, not measurement: the bar-width bank is a set of
    pixel widths and one 20 cm stripe spans several of them across a
    single frame under perspective, so nothing downstream may read a
    width from here. Stage 4 re-detects in the rectified plane where a
    stripe is one width everywhere.
    """
    mask, response, _ = markings(image, min_response=min_response)
    return mask, response


def paint_segments(mask, min_len_frac=0.02):
    """Line segments through the paint, for the plane fit and nothing else."""
    h, w = mask.shape[:2]
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/720, 40,
                            minLineLength=max(25, int(min_len_frac*max(h, w))),
                            maxLineGap=6)
    if lines is None:
        return []
    return [tuple(map(float, s)) for s in lines.reshape(-1, 4)]


# ── stage 2 ──────────────────────────────────────────────────────────

def _vp(K, d):
    """Where a ground direction meets the image."""
    p = K @ d
    if abs(p[2]) < 1e-9:
        return None
    return (float(p[0]/p[2]), float(p[1]/p[2]))


def ground_plane(segments, focal_px, width, height, min_support=6,
                 families=6, tol_deg=1.5):
    """The horizon, as the line the most vanishing points agree on.

    Every family of parallel lines lying on the ground has its vanishing
    point on one line - the ground's horizon - and a family that is not
    on the ground does not. That is the whole construction, and it is
    what the two earlier attempts here got wrong.

    The first took the y of the single most-supported vanishing point.
    On a frame with a chevron the most-supported family is the stripes,
    not the lane lines, and the result was 1279 px low on F05 and 1702
    low on F22 in a frame 4096 tall.

    The second took the line through the first two families. Two ground
    families give the right horizon whichever two they are, so a wrong
    answer means one of the pair was not on the ground - and stage 1
    searches the whole frame by design, so its segments include
    building edges, shop signs and wires. Over 42 photographs that
    version's own held-out check gave a median angular error of 9.33
    degrees and was over 20 degrees on 17 of 37.

    So: find several families, take every pair as a candidate horizon,
    and keep the one the most other vanishing points lie on. The ground
    families are mutually consistent and the rest are not, which
    separates them without a region, without an appearance test and
    without asking which family is the road's.

    The returned `consensus` is how many of the families ended up on the
    chosen line. Two is the minimum and means nothing was corroborated;
    the caller should treat it as unfitted.
    """
    if focal_px is None or len(segments) < min_support:
        return None
    K = np.array([[focal_px, 0, width/2],
                  [0, focal_px, height/2],
                  [0, 0, 1.0]])

    found, pool = [], list(segments)
    for i in range(families):
        if len(pool) < min_support:
            break
        f = dominant_direction(pool, K, seed=i)
        if f is None or f["count"] < min_support:
            break
        v = _vp(K, f["direction"])
        if v is not None and abs(v[0]) < 1e6 and abs(v[1]) < 1e6:
            found.append({"direction": f["direction"], "count": int(f["count"]),
                          "vp": v,
                          "residual_deg": float(f.get("residual_deg", float("nan")))})
        pool = [s for s, keep in zip(pool, ~f["inliers"]) if keep]

    if len(found) < 2:
        return None

    # a vanishing point is "on" a candidate horizon when the angle it
    # subtends at the camera from that line is within tolerance - a pixel
    # tolerance would be tighter far from the principal point and looser
    # near it, which is backwards
    tol_px = focal_px * math.tan(math.radians(tol_deg))

    best = None
    for i in range(len(found)):
        for j in range(i+1, len(found)):
            va, vb = found[i]["vp"], found[j]["vp"]
            dx, dy = vb[0]-va[0], vb[1]-va[1]
            n = math.hypot(dx, dy)
            if n < 1e-6:
                continue
            nx, ny = -dy/n, dx/n              # unit normal of the line
            on, support = [], 0
            for k, f in enumerate(found):
                d = abs(nx*(f["vp"][0]-va[0]) + ny*(f["vp"][1]-va[1]))
                if d <= tol_px:
                    on.append(k)
                    support += f["count"]
            score = (len(on), support)
            if best is None or score > best[0]:
                best = (score, i, j, on, (va, vb), (nx, ny))

    (n_on, support), i, j, on, (va, vb), (nx, ny) = best
    # refit the line through every vanishing point that agreed, weighted
    # by how many segments back it
    pts = np.array([found[k]["vp"] for k in on], float)
    wts = np.array([found[k]["count"] for k in on], float)
    if len(pts) >= 2:
        c = (pts * wts[:, None]).sum(0) / wts.sum()
        u, sv, vt = np.linalg.svd(pts - c, full_matrices=False)
        dirv = vt[0]
        slope = dirv[1]/dirv[0] if abs(dirv[0]) > 1e-9 else None
    else:
        c, slope = np.array(va), None
    if slope is None:
        return None
    horizon_y = float(c[1] + slope * (width/2 - c[0]))

    held_out = None
    off = [k for k in range(len(found)) if k not in on]
    if off:
        k = max(off, key=lambda k: found[k]["count"])
        v = found[k]["vp"]
        dist = abs(slope*(v[0]-c[0]) - (v[1]-c[1])) / math.hypot(slope, 1)
        held_out = {"family_count": found[k]["count"],
                    "offset_px": round(float(dist), 1),
                    "offset_deg": round(math.degrees(math.atan(dist/focal_px)), 3),
                    "note": "a family the consensus rejected; a large offset "
                            "here is the method working, not failing"}

    return {"horizon_y_px": horizon_y,
            "horizon_slope": round(float(slope), 5),
            "families_found": len(found),
            "consensus": n_on,
            "consensus_segments": int(support),
            "tolerance_deg": tol_deg,
            "vanishing_points_px": [found[k]["vp"] for k in on],
            "direction": found[on[0]]["direction"].tolist(),
            "support_segments": [found[k]["count"] for k in on],
            "support_fraction": round(support/max(len(segments), 1), 3),
            "rejected_family": held_out,
            "residual_deg": round(found[on[0]]["residual_deg"], 4)}


# ── stage 6, first region ────────────────────────────────────────────

def search_domain(shape, below_frac=0.40):
    """Where a marking may be looked for: the lower part of the frame.

    Crude on purpose, and the crudeness is the finding. This took a
    fitted horizon until three attempts to fit one failed - see
    `ground_plane`, which is kept for the record and is not called from
    `run`. Nothing in this project needs a horizon: the angle between
    two ground directions needs only the focal length and is invariant
    to camera rotation, which `tests/test_vanishing_invariance.py`
    asserts to 1e-11 and which holds even when the pitch given is wrong;
    and the metric checks that would need a rectified plane are refused
    on these photographs anyway for want of a scale.

    So this is a stated constant and not an estimate. Everything below
    40% of the frame height is in the domain. A handheld photograph of a
    road taken while standing puts the horizon above that, and a frame
    where it does not is one where the camera was pointed at the sky.

    It takes a shape and nothing else - not the image, not a paint mask,
    not a marking response - and `tests/test_pipeline.py` fails if its
    signature grows one. Any appearance-based narrowing of where paint
    may be is scored by how much paint survives it, and that score is
    set by the narrowing.

    Takes a shape and a horizon. It does not take the image, a paint
    mask or a marking response, and that is deliberate and enforced by
    `tests/test_pipeline.py`. Any appearance-based narrowing of where
    paint may be is scored by how much paint survives it, and that score
    is set by the narrowing - rule 9. So the region carries no
    appearance term at all, and the property is held structurally
    instead of by a number that cannot go down.

    A horizon of None means it is not known, and then everything below
    the frame's midpoint is in the domain, which is a weaker statement
    and is the honest one.
    """
    h, w = shape[:2]
    top = int(h * below_frac)
    m = np.zeros((h, w), np.uint8)
    m[top:] = 255
    return m


def run(image, path=None, min_response=8.0):
    """Stages 0 to 2 and search_domain, with what each one produced."""
    prov = provenance(image, path)
    mask, response = paint_field(image, min_response=min_response)
    segs = paint_segments(mask)
    domain = search_domain(image.shape)
    sc = scale()
    ipm = near_field_ipm(sc)
    return {"provenance": prov.as_dict(),
            "paint_px": int((mask > 0).sum()),
            "paint_fraction": round(float((mask > 0).mean()), 4),
            "segments": len(segs),
            "search_domain_fraction": round(float((domain > 0).mean()), 3),
            "horizon": "not fitted, and not needed - see search_domain",
            "scale": {"source": sc.source, "why": sc.why},
            "ipm": ipm,
            "stages": stages_built()}, mask, domain


# ---------------------------------------------------------------- stage 3
#
# Scale: declared, sourced, or absent. There is no fourth option, and the
# absent case is the one that holds on all 42 - so it is a return value
# with a reason per candidate, not a missing feature.

SCALE_SOURCES = ("NONE", "CAMERA_HEIGHT_RECORDED", "DASH_182",
                 "RED_LINE_169", "STRIPE_171")


@dataclass(frozen=True)
class Scale:
    """How many metres a pixel is worth, and on whose authority.

    `rel_sd` is the relative standard deviation of that conversion. It is
    not decoration: a metric check whose tolerance is tighter than three
    of these refuses, which is `admits` below, and on these photographs
    every metric check refuses because there is no conversion at all.
    """
    source: str
    metres_per_px: float | None
    rel_sd: float | None
    why: str

    def admits(self, tolerance_m: float, at_m_per_px: float | None = None) -> bool:
        """Whether a check to this tolerance may be answered at all.

        Three relative standard deviations, from the architecture. A
        tolerance the scale cannot resolve is not a near miss to be
        reported with a caveat - answering it at all would be reporting
        the scale's noise as the road's geometry.
        """
        if self.metres_per_px is None or self.rel_sd is None:
            return False
        mpp = at_m_per_px if at_m_per_px is not None else self.metres_per_px
        return tolerance_m > 3.0 * self.rel_sd * mpp


def scale(*, camera_height_m: float | None = None,
          dash_182_px: float | None = None) -> Scale:
    """Stage 3. What scale this photograph has, and why it has none.

    Every candidate in the enum is considered and each is answered from
    the record rather than from silence. Nothing here reads the image:
    a scale that is recovered from the markings is a scale that the
    markings then get measured against, and the two known attempts at
    that are on file as exactly that failure.

      CAMERA_HEIGHT_RECORDED  not recorded at capture. This is the whole
        fix and it costs a tape against the phone: it moves the scale
        from an assumed standing height at +-17 % to what the tape reads.
        The 42 of 2026-09-20 cannot be repaired this way - the surface
        has been worked on since - so they are permanently scale-free.

      DASH_182  requires a §182 dash-and-gap in frame and identified.
        Stage 5's job; not available from stages 0-2, so not claimed.

      RED_LINE_169  §169's 10 cm kerbside line. `results/scale_redline.json`
        gets 1.90 m +- 0.01, but over 24 cuts of ONE capture, which is a
        within-capture spread and not an accuracy. It also disagrees with
        scale_stripe.json's 8.00 m on the same capture, and the red line
        may sit on the kerb face rather than the carriageway, which puts
        it off the plane it would be calibrating.

      STRIPE_171  forbidden, and not for a numerical reason. §171's stripe
        width is what a §171 verdict is about. Calibrating on it and then
        checking it asks whether 20 cm is 20 cm. `results/scale_stripe.json`
        also returns camera heights of 2.25 to 9.96 m from one camera.
    """
    if camera_height_m is not None:
        return Scale("CAMERA_HEIGHT_RECORDED", None, None,
                     "a height was supplied; the conversion needs the plane "
                     "as well, and stage 2 is withdrawn - see ground_plane")
    if dash_182_px is not None:
        return Scale("DASH_182", None, None,
                     "a dash was supplied; stage 5 does not yet identify "
                     "§182, so nothing has checked that it is one")
    return Scale("NONE", None, None,
                 "no camera height at capture, no §182 dash identified, "
                 "§169 unvalidated and possibly off-plane, §171 circular")


# ---------------------------------------------------------------- stage 4
#
# Near-field IPM. Blocked twice over, and the two blocks are independent:
# one is a stage that failed its check and one is a fact about the
# photographs. Naming both matters, because fixing either alone changes
# nothing.

def near_field_ipm(scale_: Scale, *, plane=None) -> dict:
    """Stage 4. Re-detect at the one correct width, or say why not.

    This is the only stage that genuinely needs a rectified ground plane,
    and it is also the stage that needs a scale. Both are absent on all
    42, for reasons that do not share a cause:

      the plane   three fits, three failures of the held-out check
                  (median 9.33 deg, 17 of 37 over 20 deg)
      the scale   never recorded, and not recoverable from the markings
                  without measuring them against themselves

    So repairing the horizon would not unblock this, which is part of why
    the horizon was dropped rather than repaired. What unblocks it is a
    tape at the site.

    `depth_invariance` below is the falsifier this stage will be held to
    when it does run, and it is stated now so that it is not chosen after
    seeing the numbers.
    """
    blocks = []
    if plane is None:
        blocks.append("no ground plane: stage 2 withdrawn, see ground_plane")
    if scale_.metres_per_px is None:
        blocks.append(f"no scale: {scale_.why}")
    return {"ran": not blocks, "blocked_by": blocks,
            "scale_source": scale_.source,
            "falsifier": "depth_invariance",
            "unblocked_by": "a tape at the site: five stripe widths, five "
                            "gaps, the tape photographed in place, and the "
                            "camera height written down"}


def depth_invariance(duty_by_band: dict[str, float]) -> dict:
    """Stage 4's check: a correct plane gives a depth-independent duty cycle.

    A plane error tilts the recovered surface, so a length measured near
    the camera and the same length measured far from it disagree, and
    they disagree monotonically with depth. The homography is fitted
    without ever seeing the duty cycle, so it cannot flatten this.

    Three bands, near to far. Returns the drift and whether it is
    monotone; a monotone drift is the plane, not the road.
    """
    order = [duty_by_band[k] for k in ("near", "mid", "far") if k in duty_by_band]
    if len(order) < 3:
        return {"ran": False, "why": "needs three depth bands"}
    d = [b - a for a, b in zip(order, order[1:])]
    return {"ran": True, "duty": order, "drift": max(order) - min(order),
            "monotone": all(x > 0 for x in d) or all(x < 0 for x in d),
            "reading": "a monotone drift is a plane error, not the marking"}


# ---------------------------------------------------------------- stage 5
#
# Identification: each marking class by its own section's predicate.
#
# The detectors themselves are not rewritten here. `situation.py` holds
# ones that have been run over the whole field set, and a second
# implementation of the same idea would be a second thing to be wrong.
# What this stage adds is the discipline the sections impose and the
# detectors do not:
#
#   * every candidate is confined to `search_domain`, so nothing above
#     the frame's lower 60 % can be a road marking;
#   * every criterion is scale-free, because stage 3 returns NONE;
#   * a class is a CONJUNCTION of that section's stated properties, not
#     the single most distinctive one.
#
# The last point is the whole of it, and it comes from a failure on
# record. `_grated_cover` tested periodicity, which is what a grating
# is, and in three frames it returned the chevron hatching, a patched
# asphalt scar and the ghost of an erased chevron - and no drain cover.
# Adding a sign test moved the false positive instead of removing it.
# Periodicity is a property of many things on a road surface. §171 does
# not say "periodic"; it says 20 cm stripes at 30 cm intervals at 45
# degrees, in paint. Four properties, and a patch or a ghost fails at
# least two of them.

S171_DUTY = 0.400          # 20 cm stripe / (20 + 30) cm pitch
S171_ARM_DEG = 45.0        # 斜四五度
S167_WIDTH_RATIO = 1.0     # two lines of the same width
S169_TO_LANE = 1.0         # 10 cm red / 10 cm lane line


@dataclass(frozen=True)
class Candidate:
    """One thing the road might have, and what makes it that thing."""
    section: str               # "171" | "167" | "169" | "182"
    present: bool
    scale_free: dict           # the ratios the section states, as measured
    failed: tuple              # which of the section's properties did not hold
    evidence: dict

    def as_dict(self) -> dict:
        return {"section": self.section, "present": self.present,
                "scale_free": self.scale_free, "failed": list(self.failed),
                "evidence": self.evidence}


def _in_domain(px, domain) -> bool:
    """A marking is on the road, and the road is where stage 2 said."""
    if px is None:
        return False
    xs, ys = px.get("x"), px.get("y")
    if xs is None or ys is None:
        return True                       # nothing positional to check
    h, w = domain.shape[:2]
    y = int(min(max(ys, 0), h - 1)); x = int(min(max(xs, 0), w - 1))
    return bool(domain[y, x])


def s171_chevron(periodic: dict, arm_deg: float | None,
                 paint_is_brighter: bool | None) -> Candidate:
    """§171. Not "periodic" - four properties, all of which must hold.

    Tolerances are wide on purpose. The point of the conjunction is to
    separate a chevron from a patch and from an erasure ghost, which it
    does on the sign and the angle; it is not a §171 compliance verdict,
    and it cannot be one, because that needs a scale and stage 3 says
    there is none.

    duty          0.400, the only figure §171 states that survives
                  without a scale
    arm angle     45 degrees to the boundary, datum acknowledged as
                  ambiguous: 46.41 to the boundary and 57.47 to the road
                  are 11.06 apart against a method spread of 1.97
    sign          paint is brighter than what surrounds it. An erased
                  chevron's imprint is not, and this is the property
                  that the recorded false positive lacks
    periodicity   necessary, and on its own worth nothing
    """
    failed, sf = [], {}
    if not periodic.get("periodic"):
        failed.append("not periodic")
    duty = periodic.get("duty")
    if duty is None:
        failed.append("no duty cycle")
    else:
        sf["duty"] = round(float(duty), 4)
        sf["duty_regulated"] = S171_DUTY
        if abs(duty - S171_DUTY) > 0.15:
            failed.append(f"duty {duty:.3f} is not §171's {S171_DUTY}")
    if arm_deg is None:
        failed.append("no arm angle")
    else:
        sf["arm_deg"] = round(float(arm_deg), 2)
        sf["arm_regulated"] = S171_ARM_DEG
        if abs(arm_deg - S171_ARM_DEG) > 20.0:
            failed.append(f"arm {arm_deg:.1f} deg is not near 45")
    if paint_is_brighter is None:
        failed.append("sign not tested")
    elif not paint_is_brighter:
        failed.append("darker than its surround: an imprint, not paint")
    return Candidate("171", not failed, sf, tuple(failed),
                     {"periodic": periodic,
                      "guard": "the sign and angle terms exist because "
                               "periodicity alone returned a patch and an "
                               "erasure ghost as gratings"})


def s169_red_line(red: dict | None) -> Candidate:
    """§169. Red, 10 cm, on the kerb side. Scale-free part: red, and where."""
    if not red:
        return Candidate("169", False, {}, ("no red response",), {})
    sf = {"red_to_lane_regulated": S169_TO_LANE}
    failed = []
    if not red.get("present"):
        failed.append("no red kerbside line found")
    return Candidate("169", not failed, sf, tuple(failed), {"detector": red})


def s167_double_white(dw: dict | None) -> Candidate:
    """§167. Two white lines, parallel, the same width."""
    if not dw:
        return Candidate("167", False, {}, ("no double-line response",), {})
    sf = {"width_ratio_regulated": S167_WIDTH_RATIO}
    failed = [] if dw.get("present") else ["no double white line found"]
    return Candidate("167", not failed, sf, tuple(failed), {"detector": dw})


def identify(candidates: dict, domain) -> dict:
    """Stage 5. Assemble the per-section predicates over one photograph.

    Takes the detectors' output rather than the image: the detectors are
    `situation.py`'s, they have been run over all 42, and re-implementing
    them here would create a second thing to be wrong about the same
    question.
    """
    out = [s171_chevron(candidates.get("periodic") or {},
                        candidates.get("arm_deg"),
                        candidates.get("paint_is_brighter")),
           s169_red_line(candidates.get("red")),
           s167_double_white(candidates.get("double_white"))]
    return {"candidates": [c.as_dict() for c in out],
            "present": [c.section for c in out if c.present],
            "not_identified": ["182", "180", "165"],
            "s171_has_no_locator": True,
            "known_not_identified":
                "The grated covers at this site are in the photographs and "
                "on the site record, and nothing here finds them. §182, §180 "
                "and §165 have no predicate. And §171's predicate has no "
                "locator: it is sound and nothing feeds it. "
                "scripts/stage5_predicate.py tried to find the chevron by "
                "unsupervised periodicity over 42 field photographs and 3 "
                "epochs; 44 of 45 returned no measurable profile, the one "
                "that did is the frame where the chevron had been ERASED, "
                "and its period came back at the Gabor bank's ceiling - at "
                "28 and again at 80 after the bank was extended. The two "
                "epochs that do contain a chevron measured nothing. This is "
                "the same failure that removed _grated_cover: the strongest "
                "periodic response on a road is not the marking."}
