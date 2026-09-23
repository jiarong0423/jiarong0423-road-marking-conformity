"""The chevron's angle on the ground, and the datum the law does not give.

Article 171 says a chevron's diagonal stripes are 斜四五度 and does not say
45 degrees to what. On a straight section the candidate datums agree. On a
taper they do not, and tapers are where chevrons mostly are.

This measures both readings on one location and reports them together,
because choosing one and presenting it as the law's meaning would be
inventing a regulation.

The field of view comes from the Street View Static API request rather than
from a screenshot, which is the whole reason the ground angle is recoverable
at all: f = (width/2) / tan(fov/2). The camera height is not needed, because
it scales the ground plane uniformly and angles survive a uniform scale.

Several captures of one panorama at different fields of view and pitches are
the check on the method. If the angle depended on the lens the request asked
for, it would be measuring the camera.

    ./scripts/fetch_streetview.sh ...         # or use output/api/
    /opt/anaconda3/bin/python3 scripts/measure_chevron.py --write
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marking.rectify import ground_angle  # noqa: E402

RESULTS = ROOT / "results" / "chevron_angle.json"
# Three families are expected on the ground: the road's own direction, the
# chevron area's boundary, and the stripes. The windows are wide and only
# have to separate three well-spaced clusters; the numbers inside them are
# measured, not assumed.
FAMILIES = {"road": (0.0, 10.0), "boundary": (11.0, 25.0), "stripe": (40.0, 80.0)}
REGULATION = 45.0


def markings(image: np.ndarray) -> np.ndarray:
    """White paint, thresholded where the image's own histogram splits.

    Otsu rather than a constant: the road surface's brightness depends on the
    sun and a constant chosen on one frame does not survive the next.
    """
    height = image.shape[0]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    level, _ = cv2.threshold(hsv[:, :, 2], 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.inRange(hsv, (0, 0, int(level)), (180, 60, 255))
    # Above the horizon there is no ground, and the bottom strip is the
    # Google watermark.
    mask[:int(height * 0.34), :] = 0
    mask[int(height * 0.96):, :] = 0

    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def bearings(path: Path):
    """Every detected segment's ground bearing, with its pixel length."""
    meta = json.loads(path.with_suffix(".json").read_text())
    image = cv2.imread(str(path))
    height, width = image.shape[:2]
    found = cv2.HoughLinesP(cv2.Canny(markings(image), 50, 150), 1,
                            np.pi / 1440, threshold=30, minLineLength=25,
                            maxLineGap=6)

    if found is None:
        return meta, np.empty(0), np.empty(0)

    angles, weights = [], []

    for segment in np.asarray(found).reshape(-1, 4):
        angle = ground_angle(segment, meta["fov"], meta["pitch"],
                             (width, height))

        if angle is not None:
            angles.append(angle)
            weights.append(float(np.hypot(segment[2] - segment[0],
                                          segment[3] - segment[1])))

    return meta, np.array(angles), np.array(weights)


def family(angles, weights, window) -> float | None:
    """The length-weighted mean bearing inside a window, or None if empty."""
    pick = (angles >= window[0]) & (angles <= window[1])

    if pick.sum() < 3:
        return None

    return float(np.average(angles[pick], weights=weights[pick]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", default="output/api/*.jpg")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    captures = []

    for path in sorted(Path(".").glob(args.images.replace("output/", "output/"))
                       if "*" in args.images else [Path(args.images)]):
        meta, angles, weights = bearings(path)

        if angles.size < 6:
            continue

        found = {name: family(angles, weights, window)
                 for name, window in FAMILIES.items()}

        if found["stripe"] is None or found["boundary"] is None:
            continue

        captures.append({
            "file": path.name, "fov": meta["fov"], "pitch": meta["pitch"],
            "segments": int(angles.size),
            **{k: (round(v, 2) if v is not None else None)
               for k, v in found.items()},
            "stripe_to_boundary": round(found["stripe"] - found["boundary"], 2),
            "stripe_to_road": (round(found["stripe"] - found["road"], 2)
                               if found["road"] is not None else None),
        })

    if not captures:
        raise SystemExit("no capture yielded all the families")

    def summarise(key):
        values = np.array([c[key] for c in captures if c[key] is not None])

        return {"n": len(values), "mean": round(float(values.mean()), 2),
                "min": round(float(values.min()), 2),
                "max": round(float(values.max()), 2),
                "sd": round(float(values.std(ddof=1)), 2) if len(values) > 1 else None,
                "deviation_from_regulation":
                    round(float(values.mean()) - REGULATION, 2)}

    report = {
        "location": "116 縣道, 新北市; Street View panorama CLY3PO0CcluEBc0vpcvPOg, 2025-06",
        "regulation": "道路交通標誌標線號誌設置規則 §171, 斜四五度",
        "regulation_does_not_state_the_datum": True,
        "captures": captures,
        "stripe_to_boundary": summarise("stripe_to_boundary"),
        "stripe_to_road": summarise("stripe_to_road"),
        "reading": "the two datums the article leaves open give different "
                   "verdicts on the same stripes",
    }

    print(f"{'file':16}{'fov':>5}{'pitch':>7}{'road':>8}{'bound':>8}"
          f"{'stripe':>8}{'to bound':>10}{'to road':>9}")

    for c in captures:
        print(f"{c['file']:16}{c['fov']:>5}{c['pitch']:>7}"
              f"{(c['road'] if c['road'] is not None else float('nan')):>8.1f}"
              f"{c['boundary']:>8.1f}{c['stripe']:>8.1f}"
              f"{c['stripe_to_boundary']:>10.1f}"
              f"{(c['stripe_to_road'] if c['stripe_to_road'] is not None else float('nan')):>9.1f}")

    for name, key in (("to the chevron's own boundary", "stripe_to_boundary"),
                      ("to the direction of travel", "stripe_to_road")):
        s = report[key]
        print(f"\n  {name}: {s['mean']}°  ({s['min']}-{s['max']}, sd {s['sd']}, n={s['n']})")
        print(f"    against the regulation's 45°: {s['deviation_from_regulation']:+}°"
              f"{'  - inside this method own spread' if abs(s['deviation_from_regulation']) < (s['max'] - s['min']) else '  - outside it'}")

    if args.write:
        RESULTS.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    main()
