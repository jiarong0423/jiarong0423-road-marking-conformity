"""Image to ground plane, from the field of view the request asked for.

A screenshot of the Street View viewer cannot give a ground angle, because
the browser re-projects the panorama at whatever zoom the viewer was at and
the focal length of the crop is unknown. The Static API takes `fov`, so

    f = (width / 2) / tan(fov / 2)

in pixels, and with the pitch the request also fixed, the rotation from
camera to ground is known.

**The camera height is not needed for an angle.** It scales the ground plane
uniformly and a uniform scale preserves angles, so the height is set to 1 and
the map is metric up to that unknown factor. A length would need it; a
compliance check on 45 degrees does not.
"""

from __future__ import annotations

import numpy as np


def focal_px(fov_deg: float, width_px: int) -> float:
    return (width_px / 2) / np.tan(np.radians(fov_deg) / 2)


def ground_from_image(points, fov_deg: float, pitch_deg: float,
                      size: tuple[int, int]) -> np.ndarray:
    """Pixel coordinates to ground coordinates, in camera-height units.

    `pitch_deg` follows the Street View API: negative looks down. Returns
    (X, Z) with Z forward along the optical axis and X to the right; points
    at or above the horizon come back as NaN, because a ray that does not
    descend never meets the ground.
    """
    width, height = size
    f = focal_px(fov_deg, width)
    centre = np.array([width / 2, height / 2])
    uv = np.atleast_2d(np.asarray(points, float)) - centre
    rays = np.column_stack([uv[:, 0] / f, uv[:, 1] / f, np.ones(len(uv))])

    # Rotate the camera's pitch out, so the ground is the plane y = 1 -
    # image coordinates put y downward, so a ground point is below the
    # camera and its world y is positive. The sign here was wrong first
    # time and every point came back above the horizon; it is fixed by the
    # nadir test in tests/test_rectify.py rather than by re-deriving it.
    t = np.radians(pitch_deg)
    rotate = np.array([[1, 0, 0],
                       [0, np.cos(t), -np.sin(t)],
                       [0, np.sin(t), np.cos(t)]])
    world = rays @ rotate.T

    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(world[:, 1] > 1e-9, 1.0 / world[:, 1], np.nan)

    return np.column_stack([world[:, 0] * scale, world[:, 2] * scale])


def ground_angle(segment, fov_deg: float, pitch_deg: float,
                 size: tuple[int, int]) -> float | None:
    """A line segment's bearing on the ground, degrees from the forward axis.

    0 is along the direction of travel, 90 is across it. Returns None when
    either end is above the horizon.
    """
    x1, y1, x2, y2 = segment
    ends = ground_from_image([[x1, y1], [x2, y2]], fov_deg, pitch_deg, size)

    if np.isnan(ends).any():
        return None

    dx, dz = ends[1] - ends[0]

    return float(np.degrees(np.arctan2(abs(dx), abs(dz))))
