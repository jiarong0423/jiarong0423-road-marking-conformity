"""Finding the paint, by what a marking looks like across itself.

A local brightness threshold asks "is this pixel brighter than its
surroundings", and on a road surface that is true of gravel, wet patches,
tyre scuff and the lit side of every crack. On eight bird's eye frames it
returned 270 components of which almost none were markings: the population
test the LiDAR literature uses - a family is dashes when over half fall
within ±10% of the regulated size - scored 4%.

A marking is not "bright". It is **bright with dark either side, at a
particular width**. That is the dark-light-dark transition, and the filter
for it is a bar detector: positive over the marking's width, negative over
a flank each side, zero mean so flat asphalt of any brightness returns
nothing. Bertozzi and Broggi's lane detector, and the symmetrical local
threshold family after it, are all this shape.

Two choices matter and both are made here without the camera's pose, which
is the point - the pose is what the rest of this project could never pin
down:

  width    a marking's width in pixels changes with range, so the filter is
           run at a range of widths and the strongest response kept. A
           marking at any depth answers at one of them. Nothing needs to
           know which depth it is at.
  symmetry a bar detector alone fires on a step - the edge of a resurfaced
           patch, a kerb line. Requiring the two flanks to resemble each
           other rejects those, and that is what the "symmetrical" in
           symmetrical local threshold refers to.
"""

from __future__ import annotations

import cv2
import numpy as np

# px. A 15-20 cm line spans a few pixels at the horizon and tens of them in
# the foreground of a wide-angle frame, so the range has to cover both. The
# first attempt stopped at 26 and missed the chevron entirely - its near
# stripes are wider than that.
WIDTHS = (2, 3, 5, 8, 12, 18, 26, 36, 50)


def dark_light_dark(gray, widths=WIDTHS, symmetry_tol=0.55):
    """Response of a zero-mean bar detector, strongest scale per pixel.

    Returns the response, the width that produced it, and the symmetry
    ratio, so a caller can see why a pixel was kept rather than only that
    it was.
    """
    img = gray.astype(np.float32)
    best = np.full(img.shape, -np.inf, np.float32)
    scale = np.zeros(img.shape, np.float32)
    sym = np.zeros(img.shape, np.float32)

    for w in widths:
        # the bar, and a flank of the same width each side, one dimensional
        # across the marking. Horizontal here; the caller rotates the image
        # if the markings run the other way.
        k = np.zeros((1, 3*w), np.float32)
        k[0, :w] = -0.5/w
        k[0, w:2*w] = 1.0/w
        k[0, 2*w:] = -0.5/w
        r = cv2.filter2D(img, cv2.CV_32F, k)

        # A bar must be filled, not speckled. The mean over the bar is the
        # same for a solid line and for gravel scattered at the same
        # density, and a synthetic test caught exactly that: 4000 bright
        # specks returned 80.0 against a real bar's 80.0. The darkest part
        # of the bar separates them - paint has no dark part.
        floor = cv2.erode(img, np.ones((1, w), np.float32))
        flank_mean = cv2.filter2D(img, cv2.CV_32F,
                                  np.concatenate([np.full((1, w), 0.5/w),
                                                  np.zeros((1, w)),
                                                  np.full((1, w), 0.5/w)],
                                                 axis=1).astype(np.float32))
        filled = np.clip((floor - flank_mean) / (np.abs(r) + 1e-6), 0.0, 1.0)

        # the two flanks on their own, to ask whether they match
        kl = np.zeros((1, 3*w), np.float32); kl[0, :w] = 1.0/w
        kr = np.zeros((1, 3*w), np.float32); kr[0, 2*w:] = 1.0/w
        left = cv2.filter2D(img, cv2.CV_32F, kl)
        right = cv2.filter2D(img, cv2.CV_32F, kr)
        with np.errstate(divide="ignore", invalid="ignore"):
            s = 1.0 - np.abs(left - right)/(np.abs(left) + np.abs(right) + 1e-6)

        # Symmetry multiplies rather than gates. Used as a gate it let a
        # step through at full amplitude - one bright side is a resurfacing
        # boundary, not a line, and the synthetic test scored it equal to a
        # real bar. Multiplied, an asymmetric pair is suppressed in
        # proportion to how asymmetric it is.
        r = r * np.clip(s, 0.0, 1.0) * filled

        # Paint is a line, gravel is a dot. Two adjacent bright specks are
        # a two-pixel bar and the filter is right to say so - what they are
        # not is a bar that continues. Averaging the response along the
        # bar's own length leaves a marking almost untouched and divides a
        # speck by the length of the window. This is the last of the four
        # things a road surface contains that is not a marking.
        run = max(9, int(6*w)) | 1
        r = cv2.filter2D(r, cv2.CV_32F, np.ones((run, 1), np.float32)/run)

        take = (r > best) & (s > symmetry_tol)
        best[take] = r[take]
        scale[take] = w
        sym[take] = s[take]

    best[~np.isfinite(best)] = 0.0
    return best, scale, sym


def markings(bgr, min_response=10.0, both_directions=True):
    """A mask of pixels that look like paint across themselves.

    The threshold is on the response itself, which is in units of
    brightness difference: how much brighter the bar is than the mean of
    its two flanks. That is a physical quantity and comparable between
    images, unlike a percentile, which keeps a fixed share of whatever is
    in front of it - including a frame with no markings at all.
    """
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:, :, 0]
    r1, s1, y1 = dark_light_dark(g)
    if both_directions:
        # markings that run across the image are found by asking the same
        # question down the columns
        r2, s2, y2 = dark_light_dark(g.T)
        r2, s2, y2 = r2.T, s2.T, y2.T
        take = r2 > r1
        r1[take], s1[take], y1[take] = r2[take], s2[take], y2[take]
    mask = (r1 >= min_response).astype(np.uint8)*255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    return mask, r1, s1


def carriageway(*_a, **_k):
    """Withdrawn 2026-09-22. Use `road_region`.

    It decided by surface uniformity, so it kept walls and sky and
    rejected patched asphalt. The body is in
    isolation/src/marking/carriageway_withdrawn.py with the evidence.
    This raises rather than returning something, because it was wrong
    quietly for two days and a quiet wrong answer is what did the damage.
    """
    raise NotImplementedError(
        "carriageway() is withdrawn: it selected by surface uniformity and "
        "kept walls while rejecting patched road. Use road_region(). See "
        "isolation/src/marking/carriageway_withdrawn.py")


# --------------------------------------------------------------- road region
#
# What `carriageway()` was for, done by the questions a person actually
# asks when they look at the photograph and say "that is the road".
#
# `carriageway()` asked one question - is this surface uniform - and it
# is the wrong one. A wall is uniform. Asphalt that has been dug and
# patched is not, and this road has been dug and patched repeatedly,
# which is the thing the project is about. Drawn and looked at on
# 2026-09-21 its mask covered 75.5 % of F42 including the sky, the shop
# frontages and the eaves that were then reported as a §167 double white
# line, while punching holes in the road itself. On F01 it returned None.
#
# Four filters in series, cheapest first, none of them a texture test:

GROUND_FRAC = 0.40       # 1. a road is the ground, and the ground is below
ASPHALT_SAT = 90         # 2. asphalt is grey; so is its paint
BOTTOM_BAND = 0.02       # 3. the road you stand on reaches your feet
MIN_AREA_FRAC = 0.05     # 4. and it is the big one, not a puddle


def road_region(bgr, ground_frac=GROUND_FRAC):
    """The part of the frame that can be road, by position and continuity.

    Returns a uint8 mask, or None when nothing survives - and None here
    means "this photograph does not show a road surface I can bound",
    which is an answer.

    The four filters, in order, and why each one is not a texture test:

      below      A road is the ground. A handheld photograph taken while
                 standing puts the horizon above 40 % of the frame; one
                 where it does not was pointed at the sky. This alone
                 removes the two §167 false positives that were drawn
                 and identified - a factory roofline at y 1339 and a
                 restaurant's eaves at y 920, in frames 4096 tall.
      grey       Asphalt is unsaturated and so is the paint on it. This
                 removes the yellow and blue shop signage, the green
                 corrugated cladding and the orange barriers, all of
                 which sit low in these frames. It says nothing about
                 how rough the surface is.
      connected  The road you are standing on touches the bottom of your
                 photograph. A roof, a wall and a parked van do not.
                 This is the strong one, and it is the one a person uses
                 without noticing.
      largest    Of what is left, the road is the big component.

    A patched, cracked, rutted surface passes all four. That is the
    whole point of not asking about texture.
    """
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    m = np.zeros((h, w), np.uint8)
    m[int(h * ground_frac):] = 255                        # below
    m[hsv[:, :, 1] > ASPHALT_SAT] = 0                     # grey

    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))

    n, lbl, st, _ = cv2.connectedComponentsWithStats(m, 8)
    band = int(h * (1 - BOTTOM_BAND))
    best, best_area = None, 0
    for i in range(1, n):                                 # connected, largest
        area = int(st[i, cv2.CC_STAT_AREA])
        if area < MIN_AREA_FRAC * h * w or area <= best_area:
            continue
        if not (lbl[band:] == i).any():
            continue
        best, best_area = i, area
    if best is None:
        return None
    out = np.where(lbl == best, 255, 0).astype(np.uint8)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45)))
    # Re-apply the colour rule last. Closing a component fills its holes,
    # and the holes are the barriers, the signage and the vehicles - the
    # first version put every one of them back and the mask came out as a
    # plain horizontal band with the hoarding inside it. Anything the
    # grey rule removed stays removed.
    out[hsv[:, :, 1] > ASPHALT_SAT] = 0
    return cv2.morphologyEx(out, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
