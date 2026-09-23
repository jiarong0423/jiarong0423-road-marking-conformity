"""The geometry, checked against cases whose answer is known without it.

Written first because the rotation's sign was wrong on the first attempt and
every point came back above the horizon - a failure that is obvious here and
would have been a plausible-looking wrong angle further downstream.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marking.rectify import focal_px, ground_angle, ground_from_image

SIZE = (640, 640)


class Focal(unittest.TestCase):
    def test_ninety_degrees_is_half_the_width(self):
        """tan(45) is 1, so f is exactly half the width. The one case that
        can be checked without a calculator."""
        self.assertAlmostEqual(focal_px(90, 640), 320.0, places=6)

    def test_narrower_is_longer(self):
        self.assertGreater(focal_px(40, 640), focal_px(60, 640))
        self.assertGreater(focal_px(60, 640), focal_px(90, 640))


class Nadir(unittest.TestCase):
    """Straight down, the image *is* the ground plane up to a scale, so every
    angle must survive unchanged."""

    def angle(self, segment):
        return ground_angle(segment, 60, -90, SIZE)

    def test_a_vertical_image_line_runs_along_the_ground_forward_axis(self):
        self.assertAlmostEqual(self.angle((320, 300, 320, 400)), 0.0, places=4)

    def test_a_horizontal_image_line_crosses_it(self):
        self.assertAlmostEqual(self.angle((300, 320, 400, 320)), 90.0, places=4)

    def test_a_forty_five_degree_image_line_stays_forty_five(self):
        self.assertAlmostEqual(self.angle((300, 300, 400, 400)), 45.0, places=4)


class Horizon(unittest.TestCase):
    def test_a_ray_that_does_not_descend_has_no_ground_point(self):
        """Looking level, the image centre points at the horizon and never
        meets the ground. NaN is the honest answer, not a huge number."""
        out = ground_from_image([[320, 320]], 60, 0, SIZE)
        self.assertTrue(np.isnan(out).all())

    def test_the_angle_declines_rather_than_guessing(self):
        self.assertIsNone(ground_angle((320, 300, 320, 310), 60, 0, SIZE))


class Invariance(unittest.TestCase):
    """The same ground line seen through different lenses is the same line.

    This is the property the whole method rests on: if a measured angle
    depends on the field of view the request happened to ask for, the method
    is measuring the camera rather than the road.
    """

    def test_a_ground_line_reprojects_to_the_same_angle_at_any_fov(self):
        pitch = -30
        # Take a segment on the ground, project it into each lens, and read
        # the angle back. Round trip through the pinhole model.
        for bearing in (0.0, 22.5, 45.0, 67.5):
            ground = np.array([[0.0, 3.0],
                               [np.sin(np.radians(bearing)) * 2,
                                3.0 + np.cos(np.radians(bearing)) * 2]])
            read = []

            for fov in (40, 60, 90):
                f = focal_px(fov, 640)
                t = np.radians(pitch)
                rotate = np.array([[1, 0, 0],
                                   [0, np.cos(t), -np.sin(t)],
                                   [0, np.sin(t), np.cos(t)]])
                pixels = []

                for x, z in ground:
                    world = np.array([x, 1.0, z])
                    camera = rotate.T @ world
                    pixels += [320 + f * camera[0] / camera[2],
                               320 + f * camera[1] / camera[2]]

                read.append(ground_angle(pixels, fov, pitch, SIZE))

            for value in read:
                self.assertAlmostEqual(value, bearing, places=3,
                                       msg=f"bearing {bearing}, read {read}")


if __name__ == "__main__":
    unittest.main()
