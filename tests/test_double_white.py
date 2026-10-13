"""§167's detector, which shipped for weeks with no test at all.

It returned nothing on all 42 field photographs because it applied a
"long and unbroken" rule to raw Hough fragments. With that fixed it
returned five, and all five were drawn and looked at: the corrugation
ribs of a construction hoarding, and the roof edge of a restaurant.
Nought of five were road markings.

Both failures are asserted here, because both are the kind that a test
of "does it return something" would have passed.
"""
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marking.situation import _double_white, _merge_collinear, _on_road  # noqa: E402

H, W = 1200, 900
GAP = 26


def _dark():
    return np.full((H, W, 3), 60, np.uint8)


def _pair(img, x, y0, y1, gap=GAP, width=9, colour=235):
    """Two parallel bright lines with the background between them."""
    for dx in (-gap // 2, gap // 2):
        cv2.line(img, (x + dx, y0), (x + dx, y1), (colour,) * 3, width)
    return img


def _roi(x0, x1, y0, y1):
    m = np.zeros((H, W), np.uint8)
    m[y0:y1, x0:x1] = 255
    return m


GROUND_Y = int(H * 0.40)      # below this a line may be a road marking


def _fragment(y0=560):
    """Hough does not return one line; it returns pieces of one.

    Default y puts them below GROUND_Y, where a road marking can be.
    """
    segs = []
    for x in (450 - GAP // 2, 450 + GAP // 2):
        for a, b in ((y0, y0+185), (y0+200, y0+385), (y0+400, y0+585)):
            segs.append((x, a, x, b))
    return segs


def test_a_pair_low_in_the_frame_is_found():
    img = _pair(_dark(), 450, 560, 1145)
    got = _double_white(_fragment(), img)
    assert got is not None, "two parallel lines on the road were missed"
    assert abs(got["gap_px"] - GAP) < 6
    assert got["length_px"] >= H * 0.15


def test_the_same_pair_high_in_the_frame_is_not():
    """The roofline case. Identical pixels, higher up.

    F11 is a factory roofline at y 1339-1461 and F42 a restaurant's
    eaves at y 920-1153, both in frames 4096 tall. Both were reported
    as §167 double white lines. Neither is on the ground.
    """
    img = _pair(_dark(), 450, 60, 645)
    assert _double_white(_fragment(y0=60), img) is None, (
        "a pair above the ground band was reported as a road marking; "
        "this is the factory roofline and the restaurant eaves")


def test_fragments_of_one_line_become_one_line():
    """Without this the length rule can never be met.

    The gaps here are 15 px in a frame 1200 tall, 1.2 %. The tolerance
    is 2 % of frame height, which on the 4096 px originals is 82 px.
    """
    merged = _merge_collinear([(400, 300, 400, 485), (400, 500, 400, 685),
                               (400, 700, 400, 900)])
    assert len(merged) == 1
    ln = math.hypot(merged[0][2] - merged[0][0], merged[0][3] - merged[0][1])
    assert ln > 590, ln


def test_two_different_lines_do_not_merge():
    merged = _merge_collinear([(400, 300, 400, 900), (600, 300, 600, 900)])
    assert len(merged) == 2


def test_lines_at_an_angle_to_each_other_do_not_merge():
    merged = _merge_collinear([(400, 300, 400, 900), (400, 900, 700, 1100)])
    assert len(merged) == 2


def test_on_road_needs_both_ends_below_the_band():
    shape = (H, W, 3)
    assert _on_road((400, 600, 400, 1100), shape)
    assert not _on_road((400, 300, 400, 1100), shape)   # upper end too high
    assert not _on_road((400, 100, 400, 400), shape)    # both too high
    assert _on_road((400, GROUND_Y, 400, 1100), shape)  # exactly on the line


def test_a_pair_too_far_apart_is_not_a_double_line():
    """§167 sizes them like a 分向限制線, not like a lane."""
    img = _pair(_dark(), 450, 560, 1145, gap=300)
    segs = [(450 - 150, a, 450 - 150, b) for a, b in
            ((560, 745), (760, 945), (960, 1145))]
    segs += [(450 + 150, a, 450 + 150, b) for a, b in
             ((560, 745), (760, 945), (960, 1145))]
    assert _double_white(segs, img) is None


def test_a_dashed_line_does_not_merge_into_a_solid_one():
    """The property §167 turns on, and the reason the gap rule is tight.

    §184's 車道線 is dashed and may be crossed; §167's is solid and may
    not. If fragment-joining closed a dash gap, a lane line would
    become a prohibition. The gaps here are 200 px in a frame 1200
    tall - what a dashed line looks like - against a 2 % tolerance.
    """
    merged = _merge_collinear([(400, 100, 400, 300), (400, 500, 400, 700),
                               (400, 900, 400, 1100)])
    assert len(merged) == 3, "a dashed line was joined into a solid one"


def test_the_appearance_mask_no_longer_decides_anything():
    """The gate this replaced, and why it had to go.

    `carriageway()` decides by surface uniformity. A wall is uniform;
    asphalt that has been dug and patched is not. Drawn and looked at,
    its mask on F42 covered 75.5 % of the frame including the sky, the
    shop frontages and the eaves it then reported as a double white
    line, while punching holes in the road itself. On F01 it returned
    None altogether.

    A detector for a road marking cannot take its idea of "road" from
    that. The parameter stays in the signature so the caller does not
    look as though it never had one, and passing any mask at all -
    right, wrong or absent - must now change nothing.
    """
    img = _pair(_dark(), 450, 560, 1145)
    base = _double_white(_fragment(), img)
    assert base is not None
    for roi in (None, _roi(0, W, 0, H), _roi(0, 1, 0, 1),
                np.zeros((H, W), np.uint8)):
        assert _double_white(_fragment(), img, roi) == base, (
            "the carriageway mask still changes the §167 verdict")


def test_one_painted_stroke_is_not_a_pair_of_lines():
    """The defect that let the roof edges, the kerb and a character
    stroke through: the "gap must be darker" test sampled the wrong
    point.

    `mid = mi + ni*((mj-mi)@ni)/2` keeps only the perpendicular
    component and drops the along-line offset. On F07 two segments were
    174 px apart along their length, so the sample landed 87 px away
    from the real midpoint - on asphalt at L* 161 instead of inside the
    paint at L* 227 - and one painted stroke was reported as a pair
    with its own width, 19.1 px, given as their gap.

    Here: one wide bright stroke, and two segments on its two edges,
    offset along the stroke so that a perpendicular-only sample lands
    off the end of it.
    """
    import numpy as np
    img = _dark()
    cv2.line(img, (450, 560), (450, 1145), (235,) * 3, 40)   # ONE stroke
    half = 20
    segs = [(450 - half, 560, 450 - half, 900),              # left edge
            (450 + half, 805, 450 + half, 1145)]             # right edge, offset
    assert _double_white(segs, img, _roi(200, 700, 500, 1200)) is None, (
        "one stroke was reported as a double line")


def test_two_lines_that_do_not_overlap_are_not_a_pair():
    """A double line's members run alongside each other. Two segments
    end to end are one line, or two, but not a pair."""
    img = _pair(_dark(), 450, 560, 1145)
    segs = [(450 - GAP // 2, 560, 450 - GAP // 2, 780),
            (450 + GAP // 2, 930, 450 + GAP // 2, 1145)]
    assert _double_white(segs, img, _roi(200, 700, 500, 1200)) is None
