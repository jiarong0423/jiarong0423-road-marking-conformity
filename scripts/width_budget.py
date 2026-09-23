"""Whether a car and a motorcycle fit in the lane at all.

The rider's account of this site is that traffic queues early, the right
side jams, there is one lane, and cars and motorcycles contest it - and that
on one occasion there was no room to get off the chevron in time. That is a
width question before it is a behaviour question, so it is worth adding up.

道路交通安全規則 §101 requires at least half a metre of lateral clearance
when overtaking. It is the only numeric side clearance in the rules, and it
is a legal minimum rather than a comfortable one.

Lane widths are not measured here. 養工處's route inventory has no width
column (docs/official-records.md) and the 0.1353 m/px orthophoto does not
resolve the lane lines at this location - the only strong peaks across the
section are building edges at +-21 m. So the widths below are the ordinary
design range, and the conclusion is stated for each.
"""
import json

CLEAR = 0.5        # m, 道路交通安全規則 §101
VEH = {"小客車 (typical sedan)": 1.78,
       "小客車 at the legal maximum": 2.5,
       "大型車 / bus at the legal maximum": 2.5}
MOTO = 0.75        # m, 普通重型機車 including mirrors
LANES = (3.0, 3.25, 3.5)

print(f"lateral clearance required when overtaking: {CLEAR} m "
      f"(道路交通安全規則 §101)\n")
print(f"{'alongside a':>36} {'needs':>7}  " +
      "  ".join(f"{l:.2f} m lane" for l in LANES))
rows = []
for name, wv in VEH.items():
    need = wv + CLEAR + MOTO
    cells = []
    for l in LANES:
        sp = l - need
        cells.append(f"{sp:+.2f} m" if sp < 0 else f"{sp:+.2f} m ok")
    print(f"{name:>36} {need:>7.2f}  " + "  ".join(f"{c:>13}" for c in cells))
    rows.append({"vehicle": name, "width_m": wv, "required_m": round(need, 2),
                 "spare_m": {str(l): round(l-need, 2) for l in LANES}})

print(f"\nwithout any clearance at all - the metal-to-metal fit")
for name, wv in VEH.items():
    need = wv + MOTO
    print(f"  {name:<36} {need:.2f} m, so it physically fits a "
          f"{LANES[0]:.2f} m lane with {LANES[0]-need:.2f} m to share")

print(f"\nwhat that means at this site")
print(f"  A sedan and a motorcycle physically fit a 3.0 m lane with 0.47 m")
print(f"  between them - which is why riders do it - but the rules ask for")
print(f"  0.50 m from the car alone, so the pair is already over budget by")
print(f"  {1.78+CLEAR+MOTO-3.0:.2f} m before anything goes wrong.")
print(f"  Against a bus or truck at the 2.5 m legal maximum the requirement is")
print(f"  {2.5+CLEAR+MOTO:.2f} m. No lane in the design range holds that, so a rider")
print(f"  beside a heavy vehicle has two options: drop back, or leave the lane.")
print(f"  At this site leaving the lane means the chevron, and the taper that")
print(f"  leads to it is 14.9 m - under 2 s at any speed the road carries")
print(f"  (results/control_group.json).")

json.dump({"clearance_m": CLEAR, "clearance_source": "道路交通安全規則 §101",
           "motorcycle_m": MOTO, "lane_widths_considered": list(LANES),
           "rows": rows,
           "lane_width_measured": False,
           "why_not": "養工處 route inventory has no width column; the 0.1353 "
                      "m/px orthophoto does not resolve lane lines here",
           "rider_account": ["queues form early", "the right side jams",
                             "one lane", "cars and motorcycles contest it",
                             "once had no room to get off the chevron in time"]},
          open("results/width_budget.json", "w"), indent=2, ensure_ascii=False)
