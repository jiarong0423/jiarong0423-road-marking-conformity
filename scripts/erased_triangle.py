#!/usr/bin/env python3
"""The island's old far end, measured in a top-down view of the owner's photograph P64.

A photograph taken standing up cannot compare the old island with today's: the far end is
foreshortened to a sliver. So the road plane is reprojected to a top-down view first, and the
comparison is made there, in metres.

  - the plane: the lane line's dashes fix the road's vanishing point and the scale
    (道路交通標誌標線號誌設置規則 §182: 4 m dash, 6 m gap; results/dash_ruler_P64.json);
    cv2.fitLine on the dash centres, then cv2.getPerspectiveTransform / cv2.warpPerspective
  - the paint: LAB lightness, cv2.adaptiveThreshold; cv2.HoughLinesP finds the island's
    right edge line and the first lane dash, whose length checks the ruler (4 m)
  - where today's stripes stop: the share of white paint per row along the wall, with the
    painted arrow masked out (cv2.connectedComponentsWithStats on the paint mask); the
    stripes end where it falls to zero and stays there for 2 m. (Texture alone cannot tell:
    the erased stripes still leave relief.)
  - the old edge: its two ends are the points the owner confirmed on the photograph for
    scripts/dash_ruler.py; how bright it is today is sampled here, against today's edge line
  - the triangle: cv2.contourArea, drawn with cv2.fillPoly / cv2.polylines and projected
    back onto the photograph with cv2.perspectiveTransform

Done by a person, not by OpenCV: the dash centres and the old edge's two ends (owner
confirmed), the line the triangle's tip touches (X = -4.3 m, owner confirmed; the
wall-side line OpenCV finds is recorded beside it), and the reading that the faint diagonal is the old edge and the arrow sits on
erased stripes (owner, 2026-10-14).

    /opt/anaconda3/bin/python3 -B scripts/erased_triangle.py
      writes results/erased_triangle_P64.json, docs/figures/erased-triangle-P64.jpg,
      docs/figures/erased-triangle-P64-topdown.jpg
"""
import json
import cv2
import numpy as np

PHOTO = "evidence/field-2026-09-23/IMG_20260923_063437.jpg"
F, CX, CY = 2840.1, 1536, 2048
K = np.array([[F, 0, CX], [0, F, CY], [0, 0, 1.0]])
DR = json.load(open("results/dash_ruler_P64.json"))
DASHES = np.array(DR["dash_centres_px"], np.float32)
CORNER, WALL = DR["corner_px"], DR["wall_base_px"]
HORIZON = DR["subsets"]["first_7_dashes"]["horizon_y"]
M = DR["subsets"]["first_7_dashes"]["metres_per_plan_unit"]
K_PX, X0, Z1, W_M, D_M = 50, -12.0, 40.0, 20.0, 38.5          # plan: 50 px per metre, X in [-12, 8], Z in [1.5, 40]

im = cv2.imread(PHOTO)
vx, vy, x0, y0 = cv2.fitLine(DASHES, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
VP = (x0 + vx * (HORIZON - y0) / vy, HORIZON)                   # the dash line meets the horizon
pitch, yaw = np.arctan2(CY - VP[1], F), np.arctan2(VP[0] - CX, F)
Rx = np.array([[1, 0, 0], [0, np.cos(-pitch), -np.sin(-pitch)], [0, np.sin(-pitch), np.cos(-pitch)]])
Ry = np.array([[np.cos(yaw), 0, -np.sin(yaw)], [0, 1, 0], [np.sin(yaw), 0, np.cos(yaw)]])
RI = np.linalg.inv(Ry @ Rx)


def to_px(X, Z):
    q = K @ (RI @ np.array([X / M, 1.0, Z / M])); return q[:2] / q[2]


def plan_px(X, Z): return ((X - X0) * K_PX, (Z1 - Z) * K_PX)


corners = [(-12, 1.5), (8, 1.5), (-12, 40), (8, 40)]
H = cv2.getPerspectiveTransform(np.float32([to_px(*c) for c in corners]), np.float32([plan_px(*c) for c in corners]))
size = (int(W_M * K_PX), int(D_M * K_PX))
top = cv2.warpPerspective(im, H, size)
valid = cv2.erode(cv2.warpPerspective(np.full(im.shape[:2], 255, np.uint8), H, size), np.ones((15, 15), np.uint8))


def to_plan(u, v):
    p = cv2.perspectiveTransform(np.float32([[[u, v]]]), H)[0, 0]; return p[0] / K_PX + X0, Z1 - p[1] / K_PX


L = cv2.cvtColor(top, cv2.COLOR_BGR2LAB)[:, :, 0]
paint = cv2.adaptiveThreshold(L, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 51, -18) & valid
segs = cv2.HoughLinesP(paint, 1, np.pi / 360, 80, minLineLength=4 * K_PX, maxLineGap=int(0.6 * K_PX)).reshape(-1, 4)
segs = [(x1 / K_PX + X0, Z1 - y1 / K_PX, x2 / K_PX + X0, Z1 - y2 / K_PX) for x1, y1, x2, y2 in segs]

# today's right edge line: the longest near-vertical segment within 0.3 m of the old edge's lane-side end
cx_, cz_ = to_plan(*CORNER)
right = max((s for s in segs if abs(s[0] - s[2]) < 0.1 and abs((s[0] + s[2]) / 2 - cx_) < 0.3 and min(s[1], s[3]) < 10),
            key=lambda s: abs(s[3] - s[1]))
right_x, right_end = (right[0] + right[2]) / 2, max(right[1], right[3])
# the first lane dash beyond it: a near-vertical segment on the same line, past the corner
dash = [s for s in segs if abs((s[0] + s[2]) / 2 - right_x) < 0.15 and min(s[1], s[3]) > cz_ + 2]
dash_len = max(abs(s[3] - s[1]) for s in dash)
dash_from = min(min(s[1], s[3]) for s in dash)

# stripe texture along the wall, the painted arrow masked out
wx_, wz_ = to_plan(*WALL)
slope = (wx_ - cx_) / (wz_ - cz_)
old_edge = lambda Z: cx_ + (Z - cz_) * slope
WALL_DETECTED = round(float(min(s[0] for s in segs if abs(s[0] - s[2]) < 0.1 and -4.6 < s[0] < -4.0)), 2)
WALL_X = -4.3          # the line the old triangle's tip touches, confirmed by the owner on the gridded photograph
n, lab, stats, _ = cv2.connectedComponentsWithStats(paint)
arrow = np.zeros_like(paint)
for i in range(1, n):
    x, y, w, h, a = stats[i]
    if a > 0.25 * K_PX * K_PX and h > 2.5 * K_PX and w < 1.2 * K_PX:    # a solid blob 2.5 m+ long, under 1.2 m wide
        arrow[lab == i] = 255
arrow = cv2.dilate(arrow, np.ones((9, 9), np.uint8))
def stripe_profile(C):
    """share of the row painted, between the tip line and the old edge, the arrow masked out.
    A softer threshold than the line finder's: at 25-30 m the stripes are a few pixels wide."""
    pm = cv2.adaptiveThreshold(L, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 51, C) & valid
    out = []
    for Z in np.arange(18, 38.01, 0.5):
        y = int((Z1 - Z) * K_PX); a, b = int((WALL_X + 0.35 - X0) * K_PX), int((old_edge(Z) - 0.15 - X0) * K_PX)
        if b - a < 0.3 * K_PX: break
        m = arrow[y - 12:y + 13, a:b] == 0
        out.append((round(float(Z), 1), round(100 * float((pm[y - 12:y + 13, a:b][m] > 0).mean()), 1)))
    return out


BARE, RUN = 1.0, 2.0      # per cent of the row painted; metres it must stay bare
def stripes_end_of(profile):
    return next(z for z, s in profile if all(t < BARE for zz, t in profile if z <= zz <= z + RUN))


profile, profile_check = stripe_profile(-6), stripe_profile(-8)
stripes_end, stripes_end_check = stripes_end_of(profile), stripes_end_of(profile_check)


# how sharply the island opens before the cone: Hough segments along its outer (main-road) edge
soft = cv2.adaptiveThreshold(L, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 51, -8) & valid
edge_segs = []
for x1, y1, x2, y2 in cv2.HoughLinesP(soft, 1, np.pi / 720, 60, minLineLength=3 * K_PX, maxLineGap=int(0.8 * K_PX)).reshape(-1, 4):
    Xa, Za, Xb, Zb = x1 / K_PX + X0, Z1 - y1 / K_PX, x2 / K_PX + X0, Z1 - y2 / K_PX
    if Za > Zb: Xa, Za, Xb, Zb = Xb, Zb, Xa, Za
    ang = float(np.degrees(np.arctan2(Xb - Xa, Zb - Za)))
    if 2 <= Za and Zb <= 21 and -7.5 < min(Xa, Xb) and max(Xa, Xb) < -3.5 and -15 < ang < -3:
        edge_segs.append((ang, float(np.hypot(Xb - Xa, Zb - Za))))
ang_w = np.repeat([a for a, _ in edge_segs], [max(1, int(round(l * 10))) for _, l in edge_segs])
OPEN = {"segments": len(edge_segs), "angle_deg_median": round(float(np.median(-ang_w)), 1),
        "angle_deg_p25_p75": [round(float(np.percentile(-ang_w, 25)), 1), round(float(np.percentile(-ang_w, 75)), 1)]}
OPEN["ratio_length_per_lateral"] = round(float(1 / np.tan(np.radians(OPEN["angle_deg_median"]))), 1)


# the lanes after the island: white-line peaks across each row (LAB lightness above its own
# running mean), matched to the wall-side line, the lane line and the asphalt edge
def peaks(Z):
    y = int((Z1 - Z) * K_PX); a = int((-6 - X0) * K_PX); row = L[y - 15:y + 16, a:int((5 - X0) * K_PX)].astype(np.float32).mean(0)
    w = np.where(row - cv2.blur(row.reshape(1, -1), (61, 1)).ravel() > 10)[0]
    return [round((a + g.mean()) / K_PX + X0, 2) for g in (np.split(w, np.where(np.diff(w) > 3)[0] + 1) if len(w) else []) if len(g) >= 3]


def nearest(ps, want, tol=0.35):
    c = [p for p in ps if abs(p - want) <= tol]; return min(c, key=lambda p: abs(p - want)) if c else None


lane_rows = {}
for Z in np.arange(30, 39.01, 1.0):
    ps = peaks(Z); lane_rows[round(float(Z), 1)] = {"wall_side": nearest(ps, -4.3), "lane_line": nearest(ps, -1.2), "asphalt_edge": nearest(ps, 2.95)}
med = lambda k: round(float(np.median([r[k] for r in lane_rows.values() if r[k] is not None])), 2)
WB = json.load(open("results/width_budget.json"))
LANES = {"wall_side_x_m": med("wall_side"), "lane_line_x_m": med("lane_line"), "asphalt_edge_x_m": med("asphalt_edge")}
LANES["left_lane_m"] = round(LANES["lane_line_x_m"] - LANES["wall_side_x_m"], 2)
LANES["right_lane_to_asphalt_edge_m"] = round(LANES["asphalt_edge_x_m"] - LANES["lane_line_x_m"], 2)
LANES["side_by_side_needed_m"] = {r["vehicle"]: r["required_m"] for r in WB["rows"]}
LANES["spare_in_left_lane_m"] = {r["vehicle"]: round(LANES["left_lane_m"] - r["required_m"], 2) for r in WB["rows"]}
bus = next(r for r in WB["rows"] if r["vehicle"].startswith("大型車"))
car = next(r for r in WB["rows"] if r["vehicle"].startswith("小客車 (typical"))
LANES["spare_with_typical_car_m"] = round(LANES["left_lane_m"] - car["required_m"], 2)
LANES["spare_with_bus_or_truck_m"] = round(LANES["left_lane_m"] - bus["required_m"], 2)
LANES["rows_used"] = {z: v for z, v in lane_rows.items()}


def line_strength(X, Z):
    y, x = int((Z1 - Z) * K_PX), int((X - X0) * K_PX); row = L[y - 3:y + 4, x - 30:x + 31].mean(0)
    return float(row[22:39].max() - np.median(row))


today_edge = round(float(np.median([line_strength(right_x, z) for z in np.arange(right_end - 6, right_end - 1, 1.0)])), 1)
old_edge_s = round(float(np.median([line_strength(old_edge(z), z) for z in np.arange(cz_ + 1, cz_ + 4, 0.5)])), 1)

tip_z = cz_ + (WALL_X - cx_) / slope
tri = [(WALL_X, stripes_end), (old_edge(stripes_end), stripes_end), (WALL_X, tip_z)]
area = cv2.contourArea(np.float32([[x, z] for x, z in tri]))

# figures: top-down comparison, and the same lines drawn back on the photograph
ov = top.copy(); P = np.int32([plan_px(*p) for p in tri])
cv2.fillPoly(ov, [P], (58, 69, 224)); topf = cv2.addWeighted(ov, 0.45, top, 0.55, 0); cv2.polylines(topf, [P], True, (122, 138, 255), 3)
for a, b, col in [((right_x, 1.5), (right_x, right_end), (80, 255, 80)), ((cx_, cz_), (old_edge(stripes_end), stripes_end), (80, 255, 80)),
                  ((WALL_X, stripes_end), (old_edge(stripes_end), stripes_end), (255, 255, 255))]:
    cv2.line(topf, tuple(int(v) for v in plan_px(*a)), tuple(int(v) for v in plan_px(*b)), col, 4)
cv2.line(topf, tuple(int(v) for v in plan_px(right_x + 0.35, dash_from)), tuple(int(v) for v in plan_px(right_x + 0.35, dash_from + dash_len)), (0, 220, 255), 4)
XL = int((-7 - X0) * K_PX)
for Z in range(14, 41, 2):
    y = int((Z1 - Z) * K_PX); cv2.line(topf, (XL, y), (XL + 30, y), (0, 255, 255), 2); cv2.putText(topf, f"{Z} m", (XL + 34, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
for X in range(-11, 8):
    x = int((X - X0) * K_PX); cv2.line(topf, (x, 0), (x, 25), (255, 0, 255), 2); cv2.putText(topf, str(X), (x + 4, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
crop = topf[0:int(26 * K_PX), int((-7 - X0) * K_PX):int((4 - X0) * K_PX)].copy()
LEGEND = [((122, 138, 255), "red: old island end, painted over"), ((255, 255, 255), "white: where today's stripes stop (OpenCV)"),
          ((80, 255, 80), "green: today's edge line, and the faint old edge"), ((0, 220, 255), "yellow: one lane dash, 4 m (the ruler)")]


def legend(img, x, y, scale=0.62):
    h = 30 * len(LEGEND) + 16; ov = img.copy(); cv2.rectangle(ov, (x, y), (x + 560, y + h), (20, 20, 20), -1); img[:] = cv2.addWeighted(ov, 0.7, img, 0.3, 0)
    for i, (col, txt) in enumerate(LEGEND):
        yy = y + 26 + 30 * i; cv2.line(img, (x + 12, yy - 6), (x + 52, yy - 6), col, 5); cv2.putText(img, txt, (x + 62, yy), cv2.FONT_HERSHEY_SIMPLEX, scale, (240, 240, 240), 2)


legend(crop, 8, crop.shape[0] - 30 * len(LEGEND) - 26, 0.5)
cv2.imwrite("docs/figures/erased-triangle-P64-topdown.jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 88])

HI = np.linalg.inv(H)
back = lambda pts: np.int32(cv2.perspectiveTransform(np.float32([[plan_px(*p) for p in pts]]), HI)[0])
photo = im.copy(); ov = photo.copy(); cv2.fillPoly(ov, [back(tri)], (58, 69, 224)); photo = cv2.addWeighted(ov, 0.5, photo, 0.5, 0)
cv2.polylines(photo, [back(tri)], True, (122, 138, 255), 3)
cv2.polylines(photo, [back([(right_x, 2), (right_x, right_end)])], False, (80, 255, 80), 6)
cv2.polylines(photo, [back([(cx_, cz_), (old_edge(stripes_end), stripes_end)])], False, (80, 255, 80), 4)
cv2.polylines(photo, [back([(WALL_X, stripes_end), (old_edge(stripes_end), stripes_end)])], False, (255, 255, 255), 4)
photo = photo[1350:2600, 1000:2800].copy(); legend(photo, 20, 20, 0.75)
cv2.putText(photo, "P64, the owner's photo. Measured in a top-down reprojection (lane dashes as the ruler)", (20, photo.shape[0] - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
cv2.imwrite("docs/figures/erased-triangle-P64.jpg", photo, [cv2.IMWRITE_JPEG_QUALITY, 88])

out = {
    "photograph": PHOTO,
    "why_top_down": "standing up, the far end is foreshortened to a sliver; the old and new island can only be compared in a reprojected plan view",
    "ruler": {"metres_per_plan_unit": M, "horizon_y": HORIZON, "vanishing_point_px": [round(float(v), 1) for v in VP],
              "first_dash_m": [round(float(dash_from), 1), round(float(dash_from + dash_len), 1)], "first_dash_length_m": round(float(dash_len), 2),
              "check": "§182 lane dash is 4 m"},
    "today": {"right_edge_x_m": round(float(right_x), 2), "right_edge_line_ends_m": round(float(right_end), 1),
              "stripes_end_m": stripes_end, "stripes_end_m_at_threshold_-8": stripes_end_check, "bare_below_pct": BARE, "bare_for_m": RUN,
              "paint_pct_profile_threshold_-6": profile,
              "edge_line_strength": today_edge},
    "old_edge": {"from_m": [round(float(cx_), 2), round(float(cz_), 1)], "to_wall_base_m": [round(float(wx_), 2), round(float(wz_), 1)],
                 "angle_to_road_deg": round(float(np.degrees(np.arctan(abs(slope)))), 1), "line_strength_today": old_edge_s,
                 "reading": "faint: the island's old far end, painted over"},
    "lanes_after_the_island": dict(LANES, note="after the island the right lane is marked to merge left (painted arrow); everyone then shares the left lane. "
                                       "Side-by-side needs are results/width_budget.json: vehicle + 0.5 m clearance + 0.75 m scooter, "
                                       "a sum I made, using the 0.5 m of 道路交通安全規則 §101; not a rule for lane width"),
    "island_opens_before_the_cone": dict(OPEN, method="cv2.HoughLinesP on the soft paint mask, outer edge zone X -7.5..-3.5 m, Z 2..21 m; length-weighted"),
    "triangle_tip_line_x_m": WALL_X, "wall_side_line_detected_x_m": WALL_DETECTED,
    "erased_triangle": {"vertices_m": [[round(float(x), 2), round(float(z), 1)] for x, z in tri], "along_wall_m": round(float(tip_z - stripes_end), 1),
                        "width_at_stripes_end_m": round(float(old_edge(stripes_end) - WALL_X), 2), "area_m2": round(float(area), 1)},
    "uncertainty": "the ruler's own spread is about +-10% (dash_ruler_P64.json subsets: 1.69-2.04 m per unit)",
    "who_did_what": {"opencv_5": "fitLine, getPerspectiveTransform, warpPerspective, cvtColor, adaptiveThreshold, HoughLinesP, "
                                 "connectedComponentsWithStats, erode, dilate, blur, contourArea, perspectiveTransform, fillPoly, polylines",
                     "a_person": "dash centres and the old edge's two ends (confirmed by the owner on the photograph); "
                                 "the line the triangle's tip touches (X = -4.3 m, owner confirmed); "
                                 "the reading that the faint diagonal is the old edge and the arrow is painted on erased stripes"},
}
text = json.dumps(out, indent=1, ensure_ascii=False, default=float) + "\n"
with open("results/erased_triangle_P64.json.tmp", "w") as fh:
    fh.write(text)
import os; os.replace("results/erased_triangle_P64.json.tmp", "results/erased_triangle_P64.json")
print(json.dumps({k: out[k] for k in ("ruler", "erased_triangle")}, ensure_ascii=False, default=float))
print("lanes", {k: v for k, v in LANES.items() if k != "rows_used"}); print("opens", OPEN); print("today", {k: v for k, v in out["today"].items() if not k.startswith("paint_pct")}, "old edge", out["old_edge"])
