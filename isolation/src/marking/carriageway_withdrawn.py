"""`extract.carriageway` — withdrawn 2026-09-22. Kept for the record.

WHAT IT DID WRONG. It decided what is road by SURFACE UNIFORMITY. A wall
is uniform. A sky is uniform. Asphalt that has been dug and patched is
not — and this road, whose patching is the subject of the project, is
the least uniform surface in every frame.

Drawn and looked at on F42: the mask covered 75.5 % of the frame,
including the sky, the shop frontages and the restaurant eaves that were
then reported as a §167 double white line, while punching holes in the
road itself. On F01 and five other frames it returned None.

WHY IT MATTERED MORE THAN IT LOOKED. `gate2._segments()` did
`mask AND roi`, so this deleted the paint and kept the clutter. Every
detector downstream reads that. The §167 detector was rebuilt four times
against an input that did not contain its target.

THE SAME BUG, TWICE. Commit 1accb3b, 2026-09-21 11:43, "Stop cutting the
chevron out before measuring it" — the region step was already caught
destroying the object under inspection. The response was to patch this
function with an inpaint, and the metric used to judge the patch was how
much PAINT SURVIVED, which is circular: it can improve while the mask
takes in the sky. It was not replaced, and the same class of failure was
found again a day later one layer down.

REPLACED BY `extract.road_region`, which asks position, colour,
connection to the bottom of the frame, and size — and nothing about
texture.
"""
import cv2
import numpy as np

from marking.extract import markings, dark_light_dark   # noqa: F401


def carriageway(bgr, min_frac=0.06):
    """The asphalt a vehicle can actually be on.

    The extractor was finding markings on the opposite carriageway and in
    the verge. A fixed rectangle would cut those off and also cut off part
    of the road, so the region is taken from the surface itself.

    The site owner's account of this location is the reason it is worth
    doing properly: the right-hand edge is a raised concrete gutter, and
    the kerbside red line, the drain covers and a row of road studs are all
    on top of it. A motorcycle squeezed by a wider vehicle cannot move
    right - there is a step and then studs - so the only room is left,
    onto the chevron, through a taper measured elsewhere in this project as
    too short for anyone to react to. That is not a marking问题 alone; the
    lane has one escape and the marking governs it.

    Asphalt is dark, unsaturated and smooth. Concrete gutter, painted red
    line and vegetation are none of those. The mask keeps the largest such
    region touching the bottom of the frame, which is the surface the
    camera is standing on.
    """
    # The markings are removed before the surface is judged. A chevron is
    # textured by its own stripes, so a roughness test run on the raw frame
    # calls it "not road" and cuts it out.
    #
    # This was a median filter, on the argument that one wide enough
    # swallows a marking and leaves the surface underneath. Measured on 46
    # photographs it does almost nothing: at matched frame retention it
    # keeps 43.3% of marking pixels where doing no preprocessing at all
    # keeps 35.3%, and after it the markings are still 3.6 times rougher
    # than the road. Widening the kernel from 45 to 91 px does not help.
    # On the one Street View frame that shows the chevron intact, the
    # region this produced overlapped the marking mask by 0.9% when chance
    # alone would give 9% - it was cutting holes exactly where the paint
    # was, and every measurement downstream was made through it.
    #
    # Inpainting the marking mask does what the median filter was meant to
    # do. Over the same 46 photographs it keeps 88.6% against 43.3%, and
    # it wins on all 46, worst case 67.4%.
    h, w = bgr.shape[:2]
    paint, _, _ = markings(bgr, min_response=8.0, both_directions=True)
    if paint.any():
        flat = cv2.inpaint(bgr, cv2.dilate(paint, np.ones((9, 9), np.uint8)),
                           9, cv2.INPAINT_TELEA)
    else:
        flat = bgr
    lab = cv2.cvtColor(flat, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(flat, cv2.COLOR_BGR2HSV)
    light = lab[:, :, 0].astype(np.float32)
    sat = hsv[:, :, 1].astype(np.float32)

    # texture: asphalt is fine-grained, the gutter's joints and the verge
    # are not. A local standard deviation separates them.
    blur = cv2.GaussianBlur(light, (0, 0), 3)
    rough = cv2.GaussianBlur(np.abs(light - blur), (0, 0), 9)

    # No brightness test. The first version excluded anything above the
    # 75th percentile and so excluded the chevron, which is the thing being
    # measured - it correctly found the trafficable asphalt and correctly
    # left the marked-out area outside it. Paint and asphalt are both grey
    # and both smooth; vegetation is saturated and the gutter has joints.
    road = ((sat < 60) & (rough < np.percentile(rough, 75))).astype(np.uint8)*255
    road = cv2.morphologyEx(road, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    road = cv2.morphologyEx(road, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(road, 8)
    best, best_area = None, 0
    for i in range(1, n):
        ys, xs = np.nonzero(lbl == i)
        if ys.max() < h - 3:                 # must reach the bottom of the frame
            continue
        if st[i, cv2.CC_STAT_AREA] > best_area:
            best, best_area = i, st[i, cv2.CC_STAT_AREA]
    if best is None or best_area < min_frac*h*w:
        return None
    mask = ((lbl == best).astype(np.uint8))*255
    # the markings sit inside the surface, so close over them
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))


