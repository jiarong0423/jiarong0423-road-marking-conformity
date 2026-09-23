"""The same road at four dates, measured by one pipeline.

A marking was redesigned here in May 2026 after a councillor's site
inspection. That makes a natural experiment for the tool rather than for the
road: if a check like this is worth building, it has to be able to say
whether a redesign improved the geometry, and say it in the regulation's own
terms.

Three quantities, chosen because each needs a different part of the method:

  **angle** - the chevron's stripes and the taper's edge, both as ground
  bearings. Needs the projection and nothing else; the camera height cancels.

  **rate** - the taper edge's bearing minus the road's own, which inverts
  through rate = 155/V² into the design speed the taper actually suits.
  Also dimensionless.

  **extent** - the chevron band's width. This one needs a scale, and the
  scale is §171's own 50 cm stripe period recovered by autocorrelation, so
  the thing measured and the thing calibrating stay separate.

Street View supplies the fov and pitch in the request. The phone supplies a
35 mm equivalent in EXIF and its pitch off the horizon.

    /opt/anaconda3/bin/python3 scripts/compare_epochs.py --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marking.rectify import focal_px, ground_angle  # noqa: E402

RESULTS = ROOT / "results" / "epochs.json"
STRIPE_PERIOD_M = 0.50  # §171: 20 cm stripe, 30 cm gap
# The road's own direction is not assumed to be the camera's. It is read off
# the vanishing point, which the same parallel lines already produced - a
# handheld photograph from the pavement points wherever the photographer
# stood, and taking bearings under 10 degrees to be "the road" quietly
# assumed otherwise. The edge and stripe windows are then relative to it.
EDGE_WINDOW = (4.0, 26.0)
STRIPE_WINDOW = (30.0, 80.0)


def markings(image: np.ndarray) -> np.ndarray:
    height = image.shape[0]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    level, _ = cv2.threshold(hsv[:, :, 2], 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.inRange(hsv, (0, 0, int(level)), (180, 60, 255))
    mask[:int(height * 0.36), :] = 0
    mask[int(height * 0.96):, :] = 0

    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def geometry(path: Path):
    """Focal length and pitch, from whichever source the image carries."""
    image = cv2.imread(str(path))
    height, width = image.shape[:2]
    sidecar = path.with_suffix(".json")

    if sidecar.exists():
        meta = json.loads(sidecar.read_text())

        return image, focal_px(meta["fov"], width), float(meta["pitch"])

    from PIL import Image
    from PIL.ExifTags import TAGS

    tags = {TAGS.get(k, k): v
            for k, v in Image.open(path).getexif().get_ifd(0x8769).items()}
    f_px = float(tags["FocalLengthIn35mmFilm"]) * np.hypot(width, height) / 43.267
    point = vanishing_point(image)

    if point is None:
        raise SystemExit(f"{path.name}: no horizon could be found")

    pitch = np.degrees(np.arctan((point[1] - height / 2) / f_px))

    return image, f_px, float(pitch)


def vanishing_point(image: np.ndarray):
    """Where the road's parallel lines meet, or None when too few are found.

    Returning None rather than raising: a frame with no usable road lines is
    an ordinary outcome for this pipeline, and the caller declines on it.
    """
    height = image.shape[0]
    found = cv2.HoughLinesP(cv2.Canny(markings(image), 40, 130), 1,
                            np.pi / 1440, threshold=max(20, int(height / 34)),
                            minLineLength=max(30, int(height / 24)),
                            maxLineGap=max(5, int(height / 90)))

    if found is None or len(found) < 4:
        return None

    segments = np.asarray(found).reshape(-1, 4)
    bearing = np.degrees(np.arctan2(segments[:, 3] - segments[:, 1],
                                    segments[:, 2] - segments[:, 0])) % 180
    keep = ((bearing > 100) & (bearing < 170)) | ((bearing > 10) & (bearing < 80))

    if keep.sum() < 4:
        return None

    rows = [[y2 - y1, x1 - x2] for x1, y1, x2, y2 in segments[keep]]
    values = [(y2 - y1) * x1 + (x1 - x2) * y1 for x1, y1, x2, y2 in segments[keep]]
    point, *_ = np.linalg.lstsq(np.array(rows, float), np.array(values, float),
                                rcond=None)

    return point


def road_bearing(image, f_px, pitch):
    """The road's own ground bearing, from the vanishing point its parallel
    lines define. A point at infinity has no ground intersection, so the
    bearing is taken from a segment aimed at it from the image centre."""
    point = vanishing_point(image)

    if point is None:
        return None

    height, width = image.shape[:2]
    fov = 2 * np.degrees(np.arctan(width / 2 / f_px))
    # A short segment from low in the frame toward the vanishing point runs
    # along the road on the ground.
    near = np.array([width / 2, height * 0.92])
    direction = np.array(point) - near
    direction = direction / max(np.linalg.norm(direction), 1e-9)
    far = near + direction * height * 0.25

    return ground_angle([near[0], near[1], far[0], far[1]], fov, pitch,
                        (width, height))


def bearings(image, f_px, pitch):
    height, width = image.shape[:2]
    fov = 2 * np.degrees(np.arctan(width / 2 / f_px))
    # Scaled to the frame, so a 640 px Street View tile and a 4096 px phone
    # photograph are asked for the same thing in road terms rather than in
    # pixels. The first version used fixed pixel counts and found nothing in
    # the two low-contrast epochs.
    found = cv2.HoughLinesP(cv2.Canny(markings(image), 40, 130), 1,
                            np.pi / 1440,
                            threshold=max(25, int(height / 22)),
                            minLineLength=max(35, int(height / 12)),
                            maxLineGap=max(6, int(height / 90)))

    if found is None:
        return np.empty(0), np.empty(0)

    angles, weights = [], []

    for segment in np.asarray(found).reshape(-1, 4):
        angle = ground_angle(segment, fov, pitch, (width, height))

        if angle is not None:
            angles.append(angle)
            weights.append(float(np.hypot(segment[2] - segment[0],
                                          segment[3] - segment[1])))

    return np.array(angles), np.array(weights)


def family(angles, weights, window):
    pick = (angles >= window[0]) & (angles <= window[1])

    if pick.sum() < 3:
        return None

    return float(np.average(angles[pick], weights=weights[pick]))


def measure(path: Path) -> dict:
    image, f_px, pitch = geometry(path)
    angles, weights = bearings(image, f_px, pitch)
    road = road_bearing(image, f_px, pitch)
    found = {"road": road}

    if road is not None:
        relative = angles - road
        found["edge"] = family(relative, weights, EDGE_WINDOW)
        found["stripe"] = family(relative, weights, STRIPE_WINDOW)
        # Report the edge and stripe as absolute bearings for comparison
        # with earlier runs, having selected them relative to the road.
        for key in ("edge", "stripe"):
            if found[key] is not None:
                found[key] += road
    else:
        found["edge"] = found["stripe"] = None
    out = {"file": path.name, "f_px": round(f_px, 1), "pitch": round(pitch, 2),
           "segments": int(angles.size),
           **{k: (round(v, 2) if v is not None else None)
              for k, v in found.items()}}

    if found["road"] is not None and found["edge"] is not None:
        relative = found["edge"] - found["road"]
        rate = float(np.tan(np.radians(relative)))
        out["taper_relative_deg"] = round(relative, 2)
        out["taper_rate"] = round(rate, 4)
        out["equivalent_kmh"] = round(float((155 / rate) ** 0.5), 1)

    if found["road"] is not None and found["stripe"] is not None:
        out["stripe_to_road_deg"] = round(found["stripe"] - found["road"], 2)

    if found["edge"] is not None and found["stripe"] is not None:
        out["stripe_to_edge_deg"] = round(found["stripe"] - found["edge"], 2)

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    sources = [
        ("2022-11", ROOT / "output/epochs/e1_2022-11.jpg", "開工當月, 速限 50"),
        ("2024-09", ROOT / "output/epochs/e2_2024-09.jpg", "圍籬進場"),
        ("2025-06", ROOT / "output/epochs/e3_2025-06.jpg", "槽化線, 速限 30"),
        ("2026-09", ROOT / "data/field-2026-09-20/IMG_20260920_155843.jpg",
         "2026-05 標線調整後"),
    ]
    rows = []

    print(f"{'epoch':10}{'road':>8}{'edge':>8}{'stripe':>8}"
          f"{'taper°':>9}{'≈km/h':>8}  note")

    for epoch, path, note in sources:
        if not path.exists():
            print(f"{epoch:10}  missing {path}")
            continue

        row = measure(path)
        row["epoch"] = epoch
        row["note"] = note
        rows.append(row)

        def cell(key, width=8, digits=1):
            value = row.get(key)

            return f"{value:>{width}.{digits}f}" if value is not None \
                else f"{'-':>{width}}"

        print(f"{epoch:10}{cell('road')}{cell('edge')}{cell('stripe')}"
              f"{cell('taper_relative_deg', 9)}{cell('equivalent_kmh')}  {note}")

    if args.write:
        RESULTS.write_text(json.dumps({
            "site": "116 縣道 (樹林中正路), 25.00269,121.42374, heading 128",
            "required_taper_deg": {"50": 3.5, "40": 5.5, "30": 9.8, "20": 21.2},
            "regulation": "§171 chevron, §182 lane line, taper L = W·V²/155",
            "epochs": rows,
        }, indent=2, ensure_ascii=False) + "\n")
        print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    main()
