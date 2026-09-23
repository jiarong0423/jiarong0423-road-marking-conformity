"""A photograph warped onto the ground plane, so two dates can be compared.

Widths across a road cannot be read off a perspective photograph - the same
paint is wide near the camera and narrow far from it. On the ground plane it
is one number. That is all this does: undo the projection, so a before and an
after can be laid side by side and measured with a ruler.

It needs the focal length and the pitch, and nothing else. The camera height
is not needed for a ratio or an angle, only for an absolute metre, because it
scales the whole plane uniformly.

  Street View: `fov` came from the request, so f = (w/2)/tan(fov/2), and the
  pitch came from the request too.

  A phone: EXIF carries FocalLengthIn35mmFilm, and f = f35 * diagonal / 43.267
  in pixels. The pitch is not in EXIF, so it is read off the horizon - the
  vanishing point of the road's own parallel lines sits on it, and
  pitch = -atan((vy - cy) / f).

  python3 scripts/birdseye.py <image> --out <png> [--metres-per-unit 1.6]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marking.rectify import focal_px  # noqa: E402


def phone_focal(path: Path, width: int, height: int) -> float | None:
    """Pixels, from the 35 mm equivalent EXIF records."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except ImportError:
        return None

    exif = Image.open(path).getexif().get_ifd(0x8769)
    tags = {TAGS.get(k, k): v for k, v in exif.items()}

    if "FocalLengthIn35mmFilm" not in tags:
        return None

    return float(tags["FocalLengthIn35mmFilm"]) * np.hypot(width, height) / 43.267


def road_vanishing_point(image: np.ndarray) -> tuple[float, float] | None:
    """Where the road's parallel lines meet. Its height gives the pitch.

    Only the markings are used, thresholded where the frame's own histogram
    splits, because a constant chosen on one photograph does not survive the
    next one's light.
    """
    height, width = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    level, _ = cv2.threshold(hsv[:, :, 2], 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.inRange(hsv, (0, 0, int(level)), (180, 70, 255))
    mask[:int(height * 0.40), :] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    found = cv2.HoughLinesP(cv2.Canny(mask, 50, 150), 1, np.pi / 1440,
                            threshold=int(height / 30),
                            minLineLength=int(height / 20),
                            maxLineGap=int(height / 100))

    if found is None:
        return None

    segments = np.asarray(found).reshape(-1, 4)
    bearing = np.degrees(np.arctan2(segments[:, 3] - segments[:, 1],
                                    segments[:, 2] - segments[:, 0])) % 180
    # Lines running up the frame toward the horizon, not across it.
    keep = ((bearing > 100) & (bearing < 170)) | ((bearing > 10) & (bearing < 80))

    if keep.sum() < 4:
        return None

    rows, values = [], []

    for x1, y1, x2, y2 in segments[keep]:
        rows.append([y2 - y1, x1 - x2])
        values.append((y2 - y1) * x1 + (x1 - x2) * y1)

    point, *_ = np.linalg.lstsq(np.array(rows, float), np.array(values, float),
                                rcond=None)

    return float(point[0]), float(point[1])


def birdseye(image, f_px, pitch_deg, span=12.0, ahead=(1.5, 10.0), px_per_unit=90):
    """Warp to a top-down view. Units are camera heights unless converted.

    `span` is the width of the strip to show and `ahead` how far in front,
    both in camera heights. A phone at about 1.6 m over a road makes one unit
    1.6 m, so a span of 12 is roughly 19 m - a carriageway and its shoulders.

    Keep `ahead` short. Near the horizon a handful of pixels stretch across
    the whole far end of the plane, and the warp turns them into smear that
    looks like data. Ten camera heights is about sixteen metres and is where
    the paint is still readable.

    The output keeps the ground's own aspect ratio, so a square on the road
    is a square in the picture and a width can be measured with a ruler.
    """
    height, width = image.shape[:2]
    tilt = np.radians(pitch_deg)
    rotate = np.array([[1, 0, 0],
                       [0, np.cos(tilt), -np.sin(tilt)],
                       [0, np.sin(tilt), np.cos(tilt)]])
    near, far = ahead
    corners = np.array([[-span / 2, near], [span / 2, near],
                        [span / 2, far], [-span / 2, far]], float)
    pixels = []

    for x, z in corners:
        camera = rotate.T @ np.array([x, 1.0, z])
        pixels.append([width / 2 + f_px * camera[0] / camera[2],
                       height / 2 + f_px * camera[1] / camera[2]])

    # Ground y grows away from the camera; image y grows downward, so the far
    # edge is the top of the output.
    out_w = int(span * px_per_unit)
    out_h = int((far - near) * px_per_unit)
    target = np.array([[0, out_h - 1], [out_w - 1, out_h - 1],
                       [out_w - 1, 0], [0, 0]], np.float32)
    matrix = cv2.getPerspectiveTransform(np.array(pixels, np.float32), target)

    return cv2.warpPerspective(image, matrix, (out_w, out_h)), matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--span", type=float, default=12.0)
    parser.add_argument("--near", type=float, default=1.5)
    parser.add_argument("--far", type=float, default=10.0)
    parser.add_argument("--pitch", type=float,
                        help="degrees, negative looks down; read off the "
                             "horizon when omitted")
    parser.add_argument("--fov", type=float, help="degrees, for Street View")
    args = parser.parse_args()

    image = cv2.imread(str(args.image))

    if image is None:
        raise SystemExit(f"cannot read {args.image}")

    height, width = image.shape[:2]
    sidecar = args.image.with_suffix(".json")
    meta = json.loads(sidecar.read_text()) if sidecar.exists() else {}

    fov = args.fov or meta.get("fov")
    f_px = focal_px(fov, width) if fov else phone_focal(args.image, width, height)

    if f_px is None:
        raise SystemExit("no field of view and no EXIF focal length")

    pitch = args.pitch if args.pitch is not None else meta.get("pitch")

    if pitch is None:
        point = road_vanishing_point(image)

        if point is None:
            raise SystemExit("could not find the horizon; pass --pitch")

        # Looking down puts the horizon above centre, so vy < cy. The
        # downward angle is atan((cy - vy)/f) and the API convention makes
        # down negative, which is the same as atan((vy - cy)/f). Written the
        # other way round first, and every phone photograph came out pitched
        # up.
        pitch = np.degrees(np.arctan((point[1] - height / 2) / f_px))
        print(f"  horizon at y={point[1]:.0f} of {height} -> pitch {pitch:.2f}°")

    print(f"  f {f_px:.0f} px, pitch {pitch:.2f}°, "
          f"strip {args.span:.0f} wide from {args.near:.0f} to {args.far:.0f} "
          f"camera heights")
    warped, _ = birdseye(image, f_px, pitch, args.span, (args.near, args.far))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.out), warped)
    print(f"  wrote {args.out}")


if __name__ == "__main__":
    main()
