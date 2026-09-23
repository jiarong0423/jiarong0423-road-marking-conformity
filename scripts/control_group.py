"""The control: what has to happen in the taper, against what the taper allows.

The taper is a fixed length. Everything else - how fast the driver is going,
how quickly they react, whether it is dark, and how much of the chevron is
still painted - changes what has to fit inside it. Setting those against each
other is the comparison; each row is a condition and the last column is
whether the manoeuvre finishes before the road runs out.

Reaction times are not the single design figure. Olson and Sivak measured
unalerted drivers meeting an obstacle while cresting a hill - which is this
site, because 樹林陸橋 starts 430 m away - and found 1.1 s at the median and
1.6 s at the 95th percentile. Those are the fastest a driver manages under
optimised conditions, not a typical case; the 2.5 s in the design standards
carries the margin the measured values do not.

Steering is not instant either. Summala's lane changes begin moving laterally
at 1.5 s, are half done at 2.5 s and finish near 4 s. A driver who has only
reacted has not yet moved.

At night a marking must first be seen. Zwahlen and Schnell put the minimum
preview at 3.65 s under low beam, and that is before any of the above.
"""
import json

TAPER = 14.9          # m, from the measured rate 0.202 on a 3.0 m lane
ERASED = 0.64         # measured, results/erasure_ratio.json

PRT = {"median driver (Olson & Sivak 50th)": 1.1,
       "95th percentile (Olson & Sivak)": 1.6,
       "design standard (AASHTO PIEV)": 2.5}
STEER = {"first lateral movement (Summala)": 1.5,
         "half way across (Summala)": 2.5,
         "lane change complete (Summala)": 4.0}
NIGHT_PREVIEW = 3.65  # s, Zwahlen & Schnell 1997, low beam

print(f"taper {TAPER} m; chevron {int((1-ERASED)*100)}% of its original width "
      f"after {int(ERASED*100)}% was ground off\n")

print("time the taper allows")
for v in (30, 40, 50):
    print(f"  {v:>2} km/h   {TAPER/(v/3.6):5.2f} s")

print("\ntime the manoeuvre needs, day, reacting and then steering clear")
print(f"{'reaction':>38} {'+ half a lane change':>21} "
      f"{'@30':>7} {'@40':>7} {'@50':>7}")
rows = []
for name, prt in PRT.items():
    need = prt + STEER["half way across (Summala)"]
    cells = []
    for v in (30, 40, 50):
        have = TAPER/(v/3.6)
        cells.append("ok" if have >= need else f"-{need-have:.1f}s")
    print(f"{name:>38} {need:>19.1f} s {cells[0]:>7} {cells[1]:>7} {cells[2]:>7}")
    rows.append({"condition": name, "needed_s": round(need, 2),
                 "shortfall_s": {str(v): round(need - TAPER/(v/3.6), 2)
                                 for v in (30, 40, 50)}})

print(f"\nsame, at night: the marking has to be seen first "
      f"({NIGHT_PREVIEW} s minimum preview)")
print(f"{'reaction':>38} {'+ preview + half change':>21} "
      f"{'@30':>7} {'@40':>7} {'@50':>7}")
for name, prt in PRT.items():
    need = NIGHT_PREVIEW + prt + STEER["half way across (Summala)"]
    cells = [f"-{need-TAPER/(v/3.6):.1f}s" for v in (30, 40, 50)]
    print(f"{name:>38} {need:>19.1f} s {cells[0]:>7} {cells[1]:>7} {cells[2]:>7}")

print(f"\nhow much road each condition actually needs")
for v in (30, 50):
    for name, prt in PRT.items():
        d_day = (prt + STEER["half way across (Summala)"]) * v/3.6
        d_ngt = (NIGHT_PREVIEW + prt + STEER["half way across (Summala)"]) * v/3.6
        print(f"  {v} km/h  {name:<38} day {d_day:5.1f} m   night {d_ngt:5.1f} m "
              f"  (taper is {TAPER} m)")

print(f"\nthe chevron at night")
print(f"  the ground-off {int(ERASED*100)}% carries no retroreflective paint at")
print(f"  all, so the driver is shown {int((1-ERASED)*100)}% of the original")
print(f"  width. Marking width drives night detection distance directly, most")
print(f"  strongly where retroreflectivity is already low (Ohme & Schnell 2001),")
print(f"  and the imprint that makes the erasure visible by day returns nothing")
print(f"  to a headlamp. No detection distance is claimed here: this site has")
print(f"  not been photographed at night, and the field set is 15:56-16:01.")

json.dump({"taper_m": TAPER, "erased_share": ERASED,
           "night_preview_s": NIGHT_PREVIEW, "prt_s": PRT, "steer_s": STEER,
           "time_available_s": {str(v): round(TAPER/(v/3.6), 2) for v in (30, 40, 50)},
           "day": rows,
           "sight_line": {"structure": "樹林陸橋2B-2(A)", "near_end_m": 430,
                          "length_m": 355.6, "grade": "市道",
                          "source": "新北市轄內橋梁基本資料"},
           "sources": ["Olson & Sivak 1986, Human Factors 28(1)",
                       "Summala, lane change lateral displacement",
                       "Zwahlen & Schnell 1997, low-beam preview time",
                       "Ohme & Schnell 2001, marking width and older drivers",
                       "AASHTO Green Book, PIEV 2.5 s"],
           "not_measured": ["night detection distance at this site",
                            "the taper rate after the 2026-05 re-marking; 0.202 "
                            "is from 2025-06 Street View, which is before it"]},
          open("results/control_group.json", "w"), indent=2, ensure_ascii=False)
