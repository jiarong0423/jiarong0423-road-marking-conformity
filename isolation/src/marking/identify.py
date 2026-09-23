"""Which group of lines is which, decided by a measured property.

The angle is the quantity being measured, so it must not also be the thing
that decides what is being measured - that is the same circularity as
calibrating on the object under test. An earlier version sorted line groups
into "road", "taper edge" and "stripes" by which angle window they fell in,
which quietly assumed the camera faced along the road. It returned 18.3 km/h
for a photograph taken from the pavement, with no indication anything was
wrong.

§171 gives a property that is not the angle. The chevron's stripes are 20 cm
wide at 30 cm spacing - a 50 cm period repeating along the band. The boundary
lines are two continuous 15 cm lines and repeat at nothing. So:

    periodic  -> stripes
    not       -> an edge or the road

Periodicity is read by autocorrelating brightness along the group's own
direction. A real period puts peaks at integer multiples of itself; noise
does not, and that check is what separates a measurement from a coincidence.

Nothing here looks at the bearing.
"""

from __future__ import annotations

import numpy as np


def _profile_along(mask: np.ndarray, bearing_deg: float,
                   samples: int = 400) -> np.ndarray | None:
    """Mean brightness sampled along a direction, for autocorrelation.

    The band is swept perpendicular to `bearing_deg`, so a set of parallel
    stripes crossing that direction shows up as a repeating signal.
    """
    height, width = mask.shape[:2]
    angle = np.radians(bearing_deg)
    along = np.array([np.cos(angle), np.sin(angle)])
    across = np.array([-along[1], along[0]])
    centre = np.array([width / 2, height * 0.7])
    reach = min(width, height) * 0.35
    steps = np.linspace(-reach, reach, samples)
    values = []

    for step in steps:
        point = centre + along * step
        # Average a short chord across the band, so one stray pixel does not
        # carry a sample.
        chord = [point + across * t for t in np.linspace(-reach * 0.08,
                                                         reach * 0.08, 9)]
        picked = [mask[int(y), int(x)] for x, y in chord
                  if 0 <= int(x) < width and 0 <= int(y) < height]

        if not picked:
            return None

        values.append(float(np.mean(picked)))

    return np.array(values)


def periodicity(mask: np.ndarray, bearing_deg: float,
                min_lag: int = 6) -> dict:
    """How periodic the marking is along a direction, and at what lag.

    Returns the first autocorrelation peak, its height, and how well the
    following peaks sit on integer multiples of it. `integer_error` near
    zero with a peak above about 0.3 is a genuine repeat.
    """
    signal = _profile_along(mask, bearing_deg)

    if signal is None or signal.std() < 1e-6:
        return {"periodic": False, "reason": "no signal along that direction"}

    centred = signal - signal.mean()
    correlation = np.correlate(centred, centred, "full")[len(centred) - 1:]
    correlation = correlation / correlation[0]
    limit = min(len(correlation) - 1, len(signal) // 3)
    peaks = [i for i in range(min_lag, limit)
             if correlation[i] > correlation[i - 1]
             and correlation[i] >= correlation[i + 1]
             and correlation[i] > 0.18]

    if not peaks:
        return {"periodic": False, "reason": "no autocorrelation peak"}

    first = peaks[0]
    # A real period puts the later peaks on its multiples. Measure how far
    # off they are, as a fraction of the period.
    multiples = [abs(p / first - round(p / first)) for p in peaks[1:4]]
    error = float(np.mean(multiples)) if multiples else 1.0

    return {
        "periodic": bool(correlation[first] > 0.30 and error < 0.12
                         and len(peaks) >= 2),
        "lag": int(first),
        "strength": round(float(correlation[first]), 3),
        "peaks": [int(p) for p in peaks[:4]],
        "integer_error": round(error, 3),
    }


def classify(mask: np.ndarray, clusters: list[tuple[float, float]]) -> dict:
    """Label line groups without looking at their bearings.

    `clusters` is (bearing, weight) per group. Returns the labelling, or a
    refusal when the groups cannot be told apart - which is the point. A
    wrong label is a wrong answer delivered confidently; declining is not.
    """
    if len(clusters) < 2:
        return {"ok": False, "reason": f"only {len(clusters)} line group(s); "
                                       f"need the stripes and at least one edge"}

    scored = []

    for bearing, weight in clusters:
        result = periodicity(mask, bearing)
        scored.append({"bearing": round(bearing, 2), "weight": round(weight),
                       **result})

    periodic = [s for s in scored if s.get("periodic")]

    if len(periodic) != 1:
        return {"ok": False, "groups": scored,
                "reason": f"{len(periodic)} groups look periodic; the stripes "
                          f"should be exactly one"}

    stripes = periodic[0]
    rest = sorted((s for s in scored if s is not stripes),
                  key=lambda s: -s["weight"])

    return {"ok": True, "stripe": stripes, "others": rest, "groups": scored}
