"""Is there room to react to the narrowing?

One question, three numbers: how long the taper is, how long the driver takes
to notice it, and which of the two runs out first. The taper rate is measured
(results/taper_rate.json); the reaction time and deceleration are the standard
design values, cited below; the lane width is an assumption, because the
maintenance office's route inventory has no width column (docs/official-records.md).
"""
import json

RATE = json.load(open("results/taper_rate.json"))["measured"]["taper_rate"]
LANE = 3.0      # m, assumed: not in any official record for this road
PIEV = 2.5      # s, perception-reaction, AASHTO Green Book / 公路路線設計規範
DECEL = 3.4     # m/s², comfortable deceleration, same sources

L = LANE / RATE
print(f"taper rate {RATE} (measured)  x lane {LANE} m (assumed)  ->  "
      f"taper length {L:.1f} m\n")

print(f"{'posted':>7} {'speed':>8} {'time in':>9} {'reaction':>10} "
      f"{'still in':>10}  verdict")
print(f"{'km/h':>7} {'m/s':>8} {'taper (s)':>9} {'needs (s)':>10} "
      f"{'taper?':>10}")
for v_kmh in (30, 40, 50):
    v = v_kmh / 3.6
    t_in = L / v
    print(f"{v_kmh:>7} {v:>8.2f} {t_in:>9.2f} {PIEV:>10.1f} "
          f"{'no':>10}  " if t_in >= PIEV else
          f"{v_kmh:>7} {v:>8.2f} {t_in:>9.2f} {PIEV:>10.1f} "
          f"{'YES':>10}  past the taper before reacting")

print(f"\nthe 50 -> 30 transition")
v1, v2 = 50/3.6, 30/3.6
d_react = v1 * PIEV
d_brake = (v1**2 - v2**2) / (2*DECEL)
print(f"  react at 50 km/h, {PIEV} s        {d_react:6.1f} m")
print(f"  then slow 50 -> 30 at {DECEL} m/s²  {d_brake:6.1f} m")
print(f"  total from seeing the sign        {d_react+d_brake:6.1f} m")
print(f"  the taper itself is               {L:6.1f} m  "
      f"({(d_react+d_brake)/L:.1f}x shorter than needed)")

req = {v: 155/v**2 for v in (30, 50)}
print(f"\nagainst the taper formula L = W·V²/155 (施工之交通管制守則 p.9)")
for v, r in req.items():
    print(f"  at {v} km/h the taper should be {LANE/r:5.1f} m; it is {L:.1f} m "
          f"-> {LANE/r/L:.1f}x too short")

json.dump({"taper_rate_measured": RATE, "lane_width_assumed_m": LANE,
           "taper_length_m": round(L,1), "piev_s": PIEV, "decel_m_s2": DECEL,
           "time_in_taper_s": {str(v): round(L/(v/3.6),2) for v in (30,40,50)},
           "transition_50_to_30": {"reaction_m": round(d_react,1),
                                   "braking_m": round(d_brake,1),
                                   "total_m": round(d_react+d_brake,1)},
           "required_taper_m": {str(v): round(LANE/r,1) for v,r in req.items()},
           "sources": ["施工之交通管制守則 p.9",
                       "AASHTO Green Book PIEV 2.5 s, decel 3.4 m/s²"]},
          open("results/reaction.json","w"), indent=2)
