"""The drawing must not invent, and must not silently drop characters.

Both failures happened while this module was written. The surface tint
covered the photograph it was meant to annotate, and the panel dropped
fourteen traditional characters mid-sentence because PIL loads face 0 of
a font collection and face 0 of Songti.ttc is Songti SC.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from marking.draw import cjk_font, wrap_cjk, overlay, panel, sheet, _PROBE


def _frame():
    rng = np.random.default_rng(3)
    im = np.full((400, 300, 3), 120, np.uint8)
    im[200:] = 90
    return (im + rng.integers(-6, 6, im.shape)).clip(0, 255).astype(np.uint8)


def test_the_font_chosen_can_set_the_narration():
    """Face 0 of Songti.ttc passes a name check and fails this one."""
    f = cjk_font(14)
    if f is None:
        pytest.skip("no CJK font on this host")
    from PIL import Image, ImageDraw
    blank = Image.new("L", (44, 44), 0)
    ImageDraw.Draw(blank).text((4, 2), "", font=f, fill=255)
    notdef = np.array(blank)
    for ch in _PROBE:
        im = Image.new("L", (44, 44), 0)
        ImageDraw.Draw(im).text((4, 2), ch, font=f, fill=255)
        g = np.array(im)
        assert g.sum() >= 50, f"{ch} drew nothing"
        assert not np.array_equal(g, notdef), f"{ch} drew .notdef"


def test_wrapping_counts_characters_not_spaces():
    """textwrap breaks on whitespace and Chinese sentences have none."""
    line = "先看你左手邊。那裡立著施工圍籬，在你行車的高度佔掉畫面寬度的四成四。"
    out = wrap_cjk(line, 12)
    assert len(out) > 1, "one long line means it did not wrap"
    assert "".join(out) == line, "wrapping must not lose or add a character"
    for piece in out:
        width = sum(1 if ord(c) < 0x2E80 else 2 for c in piece)
        assert width <= 12 * 2 + 2


def test_a_finding_without_geometry_is_not_drawn():
    """The drawing may only show what the measurement produced."""
    im = _frame()
    empty = {"findings": [{"code": "LANE_TOO_NARROW", "measured": {}}]}
    out = overlay(im, empty, show_surfaces=False)
    assert out.shape == im.shape
    # nothing to draw, so nothing but the carriageway outline may change
    changed = (out != im).any(axis=2).mean()
    assert changed < 0.08, f"{changed:.3f} of the frame changed for no geometry"


def test_overlay_leaves_the_photograph_visible():
    """The first version tinted most of the frame and hid the evidence."""
    im = _frame()
    r = {"findings": [{"code": "EDGE_NOT_CARRIAGEWAY",
                       "measured": {"px": [40, 200, 60, 90],
                                    "axis_px": [[50, 210], [80, 280]]}}]}
    out = overlay(im, r, show_surfaces=False)
    assert (out != im).any(axis=2).mean() < 0.25


def test_a_label_stays_inside_the_frame():
    im = _frame()
    r = {"findings": [{"code": "CARRIAGEWAY_OCCUPIED",
                       "measured": {"px": [250, 5, 45, 40], "side": "right"}}]}
    out = overlay(im, r, show_surfaces=False)
    assert out.shape == im.shape


def test_sheet_is_wider_than_the_photograph():
    im = _frame()
    r = {"findings": [], "scenario": ["測試"], "taper": {"state": "CANNOT_MEASURE",
                                                        "why": "test"}}
    s = sheet(im, r, width=300)
    assert s.shape[1] == im.shape[1] + 300
    assert s.shape[0] == im.shape[0]


def test_the_panel_draws_the_unmeasured_block():
    """G18. `assess()` has returned `site_description_not_measured` since
    G00 and this panel did not draw it, while its heading said "composed
    only from the above" - so on every rendered figure the disclosure was
    invisible and the page read as though the whole scene had been
    measured.

    Asserted on pixels, because the point is that a reader sees it: the
    amber marker colour must appear, and it must not appear when the
    list is empty.
    """
    import numpy as np
    from marking.draw import AMBER, panel

    im = np.full((900, 600, 3), 200, np.uint8)
    base = {"scenario": ["量到的一句"], "findings": [], "taper": {}}

    def amber_px(p):
        return int(np.all(p == np.array(AMBER, np.uint8), axis=2).sum())

    without = panel(im, dict(base, site_description_not_measured=[]))
    withit = panel(im, dict(base,
                            site_description_not_measured=["未量測的一句"]))
    assert amber_px(withit) > amber_px(without), (
        "the unmeasured block is not drawn; a category the picture does "
        "not show is not a category")


def test_the_panel_no_longer_claims_the_scenario_is_everything():
    """The old heading asserted completeness the page cannot support."""
    import inspect
    from marking import draw

    src = inspect.getsource(draw.panel)
    assert "composed only from the above" not in src
    assert "no number is drawn that the measurement did not produce" not in src
