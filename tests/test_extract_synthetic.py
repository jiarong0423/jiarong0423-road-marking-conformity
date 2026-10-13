"""Does the bar detector fire on a bar, and stay quiet on everything else?

The extractor was tuned twice against a photograph with no ground truth,
and both times the threshold that looked best was the one that produced the
expected picture. That is the circularity every withdrawn number in this
project shares. So the filter is checked here against images where the
answer is known before it is pointed at a road.

Four things a road surface contains, and only the first is a marking:

    bar       bright, a fixed width, dark either side - paint
    step      bright on one side only - the edge of a resurfaced patch
    gradient  brightness rising smoothly - sun across the carriageway
    noise     bright specks - gravel, scuff

A filter that cannot separate these on a synthetic image will not separate
them on asphalt, and no threshold will rescue it.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from marking.extract import dark_light_dark  # noqa: E402

H, W = 200, 400
BG = 90.0
PAINT = 170.0


def canvas():
    return np.full((H, W), BG, np.float32)


def with_bar(width, x=200):
    img = canvas()
    img[:, x - width//2: x + (width + 1)//2] = PAINT
    return img


def peak_on(img, x, halfwidth=30):
    r, s, y = dark_light_dark(img)
    return float(r[:, max(0, x-halfwidth):x+halfwidth].max())


@pytest.mark.parametrize("width", [3, 5, 8, 12, 18, 26, 36])
def test_a_bar_of_any_width_responds(width):
    """The point of running several scales: a marking answers at its own."""
    peak = peak_on(with_bar(width), 200)
    assert peak > 0.5 * (PAINT - BG), (
        f"a {width} px bar {PAINT-BG:.0f} brighter than its surround "
        f"returned only {peak:.1f}")


def test_a_step_does_not():
    """One bright side is a resurfacing boundary, not a line."""
    img = canvas()
    img[:, 200:] = PAINT
    bar = peak_on(with_bar(12), 200)
    step = peak_on(img, 200)
    assert step < 0.4 * bar, (
        f"a step returned {step:.1f} against a bar's {bar:.1f}; the flanks "
        f"are not being compared")


def test_a_gradient_does_not():
    """Sun across the road changes brightness without any marking in it."""
    img = canvas() + np.linspace(0, 80, W, dtype=np.float32)[None, :]
    bar = peak_on(with_bar(12), 200)
    grad = float(dark_light_dark(img)[0].max())
    assert grad < 0.25 * bar, (
        f"a smooth gradient returned {grad:.1f} against a bar's {bar:.1f}")


def test_speckle_does_not_beat_a_bar():
    """Gravel is bright and small; paint is bright and wide."""
    rng = np.random.default_rng(0)
    img = canvas()
    ys = rng.integers(0, H, 4000)
    xs = rng.integers(0, W, 4000)
    img[ys, xs] = PAINT
    bar = peak_on(with_bar(12), 200)
    speck = float(dark_light_dark(img)[0].max())
    assert speck < 0.6 * bar, (
        f"speckle returned {speck:.1f} against a bar's {bar:.1f}")


def test_the_widest_scale_does_not_swallow_a_wide_bright_region():
    """The fault that flooded the road.

    Taking the strongest response over scales without normalising lets the
    largest kernel answer for any broad bright area, because its flanks
    land on something darker somewhere. A 120 px bright region is wider
    than any marking and must not out-respond a real 12 px bar.
    """
    img = canvas()
    img[:, 140:260] = PAINT           # far wider than any marking
    broad = float(dark_light_dark(img)[0].max())
    bar = peak_on(with_bar(12), 200)
    assert broad < bar, (
        f"a 120 px bright region returned {broad:.1f}, a 12 px bar "
        f"{bar:.1f}: the scales are not being penalised and the largest "
        f"kernel is answering for everything")
