"""The road's bearing, with the uncertainty it was missing.

An adversarial pass found that the taper rate moves 0.0157 per degree of
this number, and that the number itself - 141.6 - appears in the repository
as a bare constant with no derivation. A 0.6 degree error in it produces as
much change as the entire declared measurement uncertainty, and none of that
error was in the guard band. Replacing a hidden assumption with a visible
unvalidated constant is not an improvement, and the gate's own docstring
argued for making it an input precisely so it could be measured.

So it is measured here, two independent ways, and the disagreement between
them is part of the answer.

  field points   four coordinates read off the map along this stretch. A
                 line is fitted to them in a local metric frame and the
                 standard error of its direction comes from the residuals.
  panoramas      eight Street View capture positions along the same 84 m,
                 which Google surveyed independently of anything I did.

Neither is the road's true centreline. Both are samples of where it runs,
and if they agree the bearing is established to about their spread.
"""
import json, math
import numpy as np

LAT0 = 25.0026
M_PER_DEG_LAT = 110946.0
M_PER_DEG_LON = 101751.0 * math.cos(math.radians(LAT0))


def to_metres(pts):
    a = np.array(pts, float)
    return np.column_stack([(a[:, 1] - a[0, 1]) * M_PER_DEG_LON,   # east
                            (a[:, 0] - a[0, 0]) * M_PER_DEG_LAT])  # north


def bearing_with_error(pts, label):
    """Total least squares on the points, and the direction's standard error."""
    xy = to_metres(pts)
    c = xy.mean(0)
    u, s, vt = np.linalg.svd(xy - c, full_matrices=False)
    d = vt[0]
    bearing = math.degrees(math.atan2(d[0], d[1])) % 360      # from north, clockwise
    n = len(xy)
    perp = np.array([-d[1], d[0]])
    resid = (xy - c) @ perp
    spread = float(np.linalg.norm((xy - c) @ d))              # along-track extent
    if n > 2 and spread > 0:
        # the direction's standard error for a line fit: the perpendicular
        # scatter divided by the along-track lever arm
        sigma_perp = float(np.sqrt((resid ** 2).sum() / (n - 2)))
        se_deg = math.degrees(sigma_perp / (spread / math.sqrt(n)))
    else:
        sigma_perp, se_deg = float("nan"), float("nan")
    print(f"{label}")
    print(f"  {n} points over {np.hypot(*(xy[-1]-xy[0])):.1f} m")
    print(f"  bearing {bearing:.2f} deg")
    print(f"  perpendicular residuals: {' '.join(f'{r:+.2f}' for r in resid)} m")
    print(f"  sigma_perp {sigma_perp:.2f} m  ->  standard error {se_deg:.2f} deg\n")
    return bearing, se_deg, resid


FIELD = [(25.0029827, 121.4235667), (25.0027105, 121.4237733),
         (25.0025588, 121.4238886), (25.0025653, 121.4239653)]
b1, e1, r1 = bearing_with_error(FIELD, "four field points (read off the map)")

panos = json.load(open("results/pano_sequence.json"))
PANO = [(p["lat"], p["lon"]) for p in sorted(panos, key=lambda p: p["along_m"])
        if p["date"] == "2025-06"]
b2, e2, r2 = bearing_with_error(PANO, "eight 2025-06 Street View positions")

print(f"the two disagree by {abs(b1-b2):.2f} deg")
print(f"  field points     {b1:.2f} +- {e1:.2f}")
print(f"  panorama track   {b2:.2f} +- {e2:.2f}")
combined = math.sqrt(((e1**2 + e2**2)/2) + (b1-b2)**2/2)
print(f"  taking the disagreement as part of the error: "
      f"{(b1+b2)/2:.2f} +- {combined:.2f} deg\n")

SENS = 0.0157          # rate per degree, measured by the adversarial sweep
print("what that does to the taper rate")
print(f"  sensitivity {SENS} per degree (measured, not assumed)")
for name, err in (("field points alone", e1), ("panorama track alone", e2),
                  ("both, with their disagreement", combined)):
    print(f"  {name:32s} {err:5.2f} deg  ->  +-{SENS*err:.4f} on the rate")
print(f"\n  the measurement sd already in the guard band is 0.0092")
print(f"  the bearing term is {SENS*combined/0.0092:.1f}x that, and was absent")
print(f"  combined in quadrature: "
      f"{math.hypot(0.0092, SENS*combined):.4f}, so k=2 gives "
      f"+-{2*math.hypot(0.0092, SENS*combined):.3f} rather than +-0.018")
json.dump({"field_bearing_deg": round(b1,2), "field_se_deg": round(e1,2),
           "pano_bearing_deg": round(b2,2), "pano_se_deg": round(e2,2),
           "disagreement_deg": round(abs(b1-b2),2),
           "combined_bearing_deg": round((b1+b2)/2,2),
           "combined_se_deg": round(combined,2),
           "rate_sensitivity_per_deg": SENS,
           "rate_term_from_bearing": round(SENS*combined,4)},
          open("results/road_bearing.json","w"), indent=2)
