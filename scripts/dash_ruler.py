"""Metres from one photograph, with the lane line's own dashes as the ruler.

道路交通標誌標線號誌設置規則 §182 (quoted in docs/markings-regulation.md): 車道線 is a white
dashed line, segment 4 m, gap 6 m, width 10 cm. Consecutive dashes are therefore 10 m apart.
In a photograph the dash centres form a 1-D projective ladder: t = (a s + b) / (c s + 1), with
t = 10 m x index. The ladder fixes the road's vanishing point on the dash line; with the
camera's focal length (EXIF f35 = 24 mm, 2840 px) and zero roll that gives the road plane, and
the dashes give the metric scale. Then any two points on the road surface can be measured.

Inputs (read by eye / by threshold from IMG_20260923_063437.jpg, P64, and recorded here):
  the centres of the first seven dashes, and the two ends of the island's slanted end edge
  (the lane-side corner, and where it meets the base of the bridge wall; the owner confirmed
  both on the photograph).

    python3 -B scripts/dash_ruler.py        (writes results/dash_ruler_P64.json)
"""
import json, numpy as np
from scipy.optimize import least_squares

F = 2840.1; CX, CY = 1536, 2048
K = np.array([[F, 0, CX], [0, F, CY], [0, 0, 1.0]]); KI = np.linalg.inv(K)
DASHES = np.array([(1982, 1667), (2006, 1629), (2020, 1604), (2031, 1588), (2038, 1577), (2044, 1566), (2048, 1560)], float)
CORNER, WALL = (1955, 1714), (1786, 1650)


def run(D):
    c = D.mean(0); _, _, vt = np.linalg.svd(D - c); d = vt[0]; d = d if d[1] < 0 else -d
    sp = (D - c) @ d; sp -= sp.min(); t = 10.0 * np.arange(len(D))
    model = lambda p, x: (p[0] * x + p[1]) / (p[2] * x + 1)
    r = least_squares(lambda p: model(p, sp) - t, [0.5, 0, -0.001])
    V = D[np.argmin(sp)] + d * (-1 / r.x[2])
    d_f = KI @ np.array([V[0], V[1], 1.0]); d_f /= np.linalg.norm(d_f)
    n = K.T @ np.array([0.0, 1.0, -V[1]]); n /= np.linalg.norm(n)
    e_f = d_f - np.dot(d_f, n) * n; e_f /= np.linalg.norm(e_f); e_l = np.cross(n, e_f)
    def plan(P):
        o = []
        for u, v in np.atleast_2d(P):
            rr = KI @ np.array([u, v, 1.0]); X = rr / np.dot(n, rr); o.append((np.dot(X, e_l), np.dot(X, e_f)))
        return np.array(o)
    pd = plan(D); gaps = np.linalg.norm(np.diff(pd, axis=0), axis=1); k = 10.0 / gaps.mean()
    axis = np.degrees(np.arctan2(*(pd[-1] - pd[0])[:2]))
    q = plan(np.array([CORNER, WALL], float)) * k; dd = q[1] - q[0]
    ang = abs(np.degrees(np.arctan2(dd[0], dd[1])) - axis); ang = ang if ang <= 90 else 180 - ang
    return {"horizon_y": round(float(V[1])), "metres_per_plan_unit": round(float(k), 2),
            "dash_spacing_spread_pct": round(float(100 * gaps.std() / gaps.mean()), 1),
            "length_m": round(float(np.linalg.norm(dd)), 1), "angle_to_road_axis_deg": round(float(ang), 1),
            "taper_len_over_lateral": round(float(1 / np.tan(np.radians(ang))), 1)}


subsets = {f"first_{k}_dashes": run(DASHES[:k]) for k in (4, 5, 6, 7)}
vals = lambda key: [s[key] for s in subsets.values()]
out = {
    "ruler": "道路交通標誌標線號誌設置規則 §182: lane line dash 4 m + gap 6 m = 10 m per dash",
    "photograph": "evidence/field-2026-09-23/IMG_20260923_063437.jpg (P64)",
    "dash_centres_px": DASHES.astype(int).tolist(), "corner_px": CORNER, "wall_base_px": WALL,
    "assumptions": ["consecutive dashes, none skipped", "road plane, camera roll 0", "the wall-base end may sit on the ramp, so the length is less certain than the angle"],
    "subsets": subsets,
    "slanted_end_edge": {"length_m": round(float(np.median(vals("length_m"))), 1),
                         "angle_deg": round(float(np.median(vals("angle_to_road_axis_deg"))), 1),
                         "taper_len_over_lateral": round(float(np.median(vals("taper_len_over_lateral"))), 1),
                         "angle_range_deg": [min(vals("angle_to_road_axis_deg")), max(vals("angle_to_road_axis_deg"))]},
    "not_claimed": "this edge is the island's far end; it is not asserted to be the lane-shift taper of design table 4.2.7",
}
# error simulation: dash centres +-2 px, corner +-6 px, wall end +-10 px (fixed seed, 400 trials)
def _trial(rng):
    D = DASHES[:6] + rng.normal(0, 2.0, (6, 2)); global CORNER, WALL
    c0, w0 = CORNER, WALL
    CORNER = tuple(np.array(c0, float) + rng.normal(0, 6, 2)); WALL = tuple(np.array(w0, float) + rng.normal(0, 10, 2))
    try:
        r = run(D)
    except Exception:
        r = None
    CORNER, WALL = c0, w0
    return r
_rng = np.random.default_rng(7); _t = [x for x in (_trial(_rng) for _ in range(400)) if x]
_a = np.array([x["angle_to_road_axis_deg"] for x in _t]); _l = np.array([x["length_m"] for x in _t])
out["monte_carlo"] = {"trials": len(_t), "angle_deg": {"median": round(float(np.median(_a)), 1), "p10": round(float(np.percentile(_a, 10)), 1), "p90": round(float(np.percentile(_a, 90)), 1)},
                      "length_m": {"median": round(float(np.median(_l)), 1), "p10": round(float(np.percentile(_l, 10)), 1), "p90": round(float(np.percentile(_l, 90)), 1)},
                      "perturbation": "dash centres 2 px, corner 6 px, wall end 10 px (1 sigma)"}
json.dump(out, open("results/dash_ruler_P64.json", "w"), indent=2)
print(json.dumps(out["slanted_end_edge"]))
