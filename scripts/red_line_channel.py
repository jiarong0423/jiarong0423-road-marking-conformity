"""Does LAB's a* find the kerbside red line better than a BGR difference?

§169's line is red paint on a concrete kerb, photographed in whatever
light the day gave. The detector in situation.py thresholds
`r - (g+b)/2`, which is a brightness-weighted quantity: the same paint in
shade and in sun gives different values, and a sunlit grey kerb can pass
it. CIE L*a*b* separates lightness from chroma by construction, so a* -
the green-to-red axis - is the channel that asks the question the
regulation implies, which is what colour the paint is and not how bright
the day was.

This compares the two over every field photograph and both Street View
sets, on two things that can be counted without hand-labelling:

  separation  - how far the a* (or BGR) response over the pixels the
                incumbent detector calls red sits above the response over
                the rest of the frame, in units of the rest's spread.
                A channel that answers the question has a large one.
  stability   - the spread of the chosen threshold's effect across
                photographs taken minutes apart in changing light. The
                red line does not move between them; a channel that
                tracks the light rather than the paint does.

Writes results/red_line_channel.json.

    python3 scripts/red_line_channel.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def bgr_response(bgr):
    b, g, r = cv2.split(bgr.astype(np.int16))
    return (r - (g + b)//2).astype(np.float32)


def lab_a_response(bgr):
    a = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:, :, 1].astype(np.float32)
    return a - 128.0          # OpenCV stores a* offset by 128


def separation(resp, mask):
    """How far the marked pixels sit above the rest, in the rest's spread."""
    inside, outside = resp[mask], resp[~mask]
    if inside.size < 50 or outside.size < 50:
        return None
    sd = float(outside.std())
    if sd < 1e-6:
        return None
    return float((inside.mean() - outside.mean()) / sd)


def main() -> int:
    paths = []
    idx = ROOT / "results" / "field_index_2026-09-20.csv"
    if idx.exists():
        for row in csv.DictReader(idx.open()):
            p = ROOT / "data" / "field-2026-09-20" / row["file"]
            if p.exists():
                paths.append((row["no"], p))
    for name in ("e1_2022-11", "e2_2024-09", "e3_2025-06"):
        p = ROOT / "output" / "epochs" / f"{name}.jpg"
        if p.exists():
            paths.append((name, p))

    rows = []
    for label, path in paths:
        im = cv2.imread(str(path))
        if im is None:
            continue
        f = 1400 / max(im.shape[:2])
        if f < 1:
            im = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        # the incumbent's own positives are the common reference set, so
        # neither channel is scored on a mask it produced itself
        b, g, r = cv2.split(im.astype(np.int16))
        ref = ((r - (g + b)//2 > 14) & (r > 55))
        if ref.sum() < 50:
            continue
        rows.append({
            "id": label,
            "reference_px": int(ref.sum()),
            "bgr_separation": separation(bgr_response(im), ref),
            "lab_a_separation": separation(lab_a_response(im), ref),
        })

    usable = [x for x in rows
              if x["bgr_separation"] is not None
              and x["lab_a_separation"] is not None]
    bgr = np.array([x["bgr_separation"] for x in usable])
    lab = np.array([x["lab_a_separation"] for x in usable])
    out = {
        "question": "which channel separates §169's red paint from the rest "
                    "of the frame",
        "method": "both channels scored on the same reference set - the "
                  "pixels the incumbent BGR rule calls red - so neither is "
                  "graded on a mask it produced. Separation is the "
                  "difference of means over the standard deviation of the "
                  "pixels outside the set.",
        "n_images": len(usable),
        "n_images_seen": len(rows),
        "bgr_separation_median": round(float(np.median(bgr)), 3),
        "lab_a_separation_median": round(float(np.median(lab)), 3),
        "lab_a_wins": int((lab > bgr).sum()),
        "bgr_wins": int((bgr > lab).sum()),
        "per_image": usable,
    }
    (ROOT / "results" / "red_line_channel.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print(f"n = {out['n_images']} images")
    print(f"  BGR   r-(g+b)/2  separation median {out['bgr_separation_median']}")
    print(f"  LAB   a*         separation median {out['lab_a_separation_median']}")
    print(f"  a* better on {out['lab_a_wins']}, BGR better on {out['bgr_wins']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
