#!/usr/bin/env python3
"""Measure the three §171 properties periodicity alone does not carry.

The architecture requires stage 5 to be evaluated against a recorded
false positive: `_grated_cover` tested periodicity, and over three
frames it returned the chevron hatching, a patched asphalt scar and the
ghost of an erased chevron - and no drain cover. Periodicity is a
property of many things on a road.

§171 states four. This measures the three that `results/chevron_periodic.json`
does not carry, all scale-free because stage 3 returns NONE:

  duty cycle  from the first two harmonics of the cross-stripe profile.
              For a square wave of duty D, |c2/c1| = |cos(pi*D)|, so
              D = arccos(|c2/c1|)/pi. Verified numerically elsewhere in
              this project against the analytic value at three duties.
              §171's 20 cm on a 50 cm pitch is 0.400.
  direction   the stripes' bearing, from the same transform.
  sign        whether the bright phase is brighter than the local
              background. Paint is. An imprint left by erasure is not,
              and that is the property the false positive lacks.

The sign is the load-bearing one and it is also the cheapest. That is
the finding, not the code.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]   # repo root: this file is isolation/scripts/
# isolation/src FIRST: these scripts serve the isolated modules, and
# isolation/src/marking/__init__.py extends the package path to the real
# src/marking so the shared parts still resolve. Moving these scripts
# into isolation/ on 2026-09-21 broke all three by leaving ROOT and this
# path pointing one directory too shallow; none was run afterwards.
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "isolation" / "src"))
from marking.pipeline import search_domain          # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util as _ilu                        # noqa: E402
_spec = _ilu.spec_from_file_location("_cp", ROOT / "scripts" / "chevron_periodic.py")
_cp = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_cp)
# The shared bank tops out at 28 px and every one of 45 frames came back
# at exactly 28, which is a ceiling and not a measurement. §171's pitch is
# 50 cm; at 1000 px wide that is about 7 px at 20 m and far more in the
# near field, so the range has to go up. Extended here rather than in
# chevron_periodic.py, whose published figures were computed with the
# bank as it stands.
_cp.BANK = _cp.gabor_bank(periods=(6, 9, 13, 19, 28, 40, 56, 80), n_theta=12)
periodic_field = _cp.periodic_field

WORK = 1000                  # as in chevron_periodic.py, so the two compare

# From the estimator's own calibration against synthetic profiles, one
# per condition, at 32 bins. This is a property of the estimator and not
# a claim about any road:
#
#   square wave, clean to moderate noise   0.004 - 0.045
#   sinusoid, with or without noise        0.101 - 0.178
#   square wave under heavy noise          0.157   <- overlaps the above
#   pure noise                             1.589
#
# So a residual at or below SQUARE_MAX is a square wave whose duty means
# something; above NOT_SQUARE_MIN it is not one; between them the answer
# is that this profile does not decide, which is a third outcome and not
# a rounding of the other two.
SQUARE_MAX, NOT_SQUARE_MIN = 0.06, 0.20


def _profile(gray, region, angle_deg, period):
    """Mean luminance across the stripes, inside ONE region.

    Over the whole search domain this returns a flat line: a chevron
    occupies a patch and averaging the lower 60 % of the frame washes it
    out. The first version of this script did exactly that and reported
    an amplitude of 2.23 grey levels, which is the sensor. The region is
    the point.
    """
    h, w = gray.shape
    th = np.radians(angle_deg)
    yy, xx = np.mgrid[0:h, 0:w]
    t = (xx * np.cos(th) + yy * np.sin(th)).astype(np.float32)
    m = region
    if m.sum() < 400:
        return None
    phase = np.mod(t[m], period) / period
    v = gray[m].astype(np.float32)
    # Bins have to be covered, not merely requested. A patch narrower
    # than one period fills part of the cycle and leaves the rest NaN,
    # and 32 bins over a period of 80 px left 15 filled on the first
    # frame tried. Fall back rather than fail, and say how many.
    for nb in (32, 24, 16, 12, 8):
        idx = np.clip((phase * nb).astype(int), 0, nb - 1)
        counts = np.bincount(idx, minlength=nb)
        if counts.min() >= 3:
            return np.array([v[idx == b].mean() for b in range(nb)])
    return None


def _duty_and_sign(prof):
    """Duty from |c2/c1|, sign from where the energy sits.

    |c2/c1| = |cos(pi*D)| holds for a SQUARE wave. Fed a sinusoid it
    returns c2/c1 = 0 and therefore D = 0.5, which is not a duty cycle -
    it is the estimator saying the input is not a square wave. The first
    run of this script reported a median of 0.4374 over 45 frames with
    that failure unguarded, which is a distribution of sinusoids and not
    a measurement of §171.

    So squareness is returned beside the duty and gates it. An ideal
    square wave of any duty puts a fixed share of its energy in the odd
    harmonics; a sinusoid puts all of it in the first.
    """
    p = prof - prof.mean()
    f = np.fft.rfft(p)
    c1, c2 = abs(f[1]), abs(f[2])
    if c1 < 1e-6:
        return None, None, None
    r = min(c2 / c1, 1.0)
    duty = float(np.arccos(r) / np.pi)

    # Is this actually a square wave? Two earlier gates failed here and
    # both failed the same way - they were dominated by the fundamental,
    # which a sinusoid and a square wave share.
    #
    #   energy above the fundamental: a noisy sinusoid scored 0.487,
    #     inside the 0.53-0.67 band square waves occupy, because noise
    #     is broadband
    #   cosine similarity of the harmonic series: a pure sinusoid scores
    #     0.932 STRUCTURALLY, since normalising a vector whose first
    #     entry dominates makes everything else nearly parallel
    #
    # The duty is estimated from c2/c1, so c2 agrees by construction and
    # tests nothing. Harmonics 3, 4 and 5 are not in the estimate, which
    # makes them a held-out prediction: a square wave of duty D must put
    # |c_n|/|c1| = |sin(n*pi*D)| / (n*|sin(pi*D)|) into each of them.
    # Same principle as the plane hold-out, one stage down.
    n = np.arange(3, 6)
    den = abs(np.sin(np.pi * duty)) * n
    pred = np.abs(np.sin(n * np.pi * duty)) / np.where(den > 1e-9, den, np.inf)
    meas = np.abs(f[3:6]) / c1 if len(f) > 5 else np.zeros(3)
    harmonic_residual = float(np.abs(meas - pred).mean())

    # Sign: the narrow phase is the marking. If duty < 0.5 the bright
    # bins are the narrow ones; ask whether they are above the median.
    k = max(1, int(round(duty * len(prof))))
    bright = np.sort(prof)[-k:].mean()
    dark = np.sort(prof)[:k].mean()
    med = float(np.median(prof))
    return duty, float(bright - med) > float(med - dark), {
        "harmonic_residual": round(harmonic_residual, 3),
        "bright_above_median": round(float(bright - med), 2),
        "dark_below_median": round(float(med - dark), 2),
        "amplitude": round(float(prof.max() - prof.min()), 2)}


def measure(path: Path) -> dict:
    """Locate the strongest periodic patch, then read §171's properties in it."""
    bgr = cv2.imread(str(path))
    if bgr is None:
        return {"error": "unreadable"}
    f = WORK / max(bgr.shape[:2])
    if f < 1:
        bgr = cv2.resize(bgr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    lab_l = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:, :, 0]
    dom = search_domain(bgr.shape) > 0

    resp, per, ang = periodic_field(lab_l)
    if not dom.any():
        return {"error": "empty domain"}
    thr = float(np.percentile(resp[dom], 97))
    strong = (dom & (resp >= thr)).astype(np.uint8)
    if strong.sum() < 200:
        return {"error": "no periodic structure above the 97th percentile"}

    # One patch, not the union of every strong pixel in the frame: a
    # profile taken across two patches at different bearings is a
    # profile of neither.
    strong = cv2.morphologyEx(strong, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(strong, 8)
    if n < 2:
        return {"error": "no component"}
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    region = lab == k
    if region.sum() < 400:
        return {"error": f"largest patch is {int(region.sum())} px"}

    angle = float(np.median(ang[region]))
    period = float(np.median(per[region]))
    bank_max = max(p for p, _, _ in _cp.BANK)
    prof = _profile(lab_l, region, angle, period)
    if prof is None:
        return {"error": "no profile in the patch"}
    duty, bright, detail = _duty_and_sign(prof)
    return {"angle_deg": round(angle, 1), "period_px": round(period, 1),
            "period_at_bank_ceiling": bool(period >= bank_max),
            "patch_px": int(region.sum()),
            "contrast": round(thr / max(float(np.median(resp[dom])), 1e-6), 2),
            "amplitude": round(float(prof.max() - prof.min()), 2),
            "duty": None if duty is None else round(duty, 4),
            "harmonic_residual": detail["harmonic_residual"],
            "paint_is_brighter": bright, "profile": detail}


def main() -> int:
    rows = [(r["no"], ROOT / "evidence" / "field-2026-09-20" / r["file"])
            for r in csv.DictReader(
                open(ROOT / "results" / "field_index_2026-09-20.csv"))]
    # The three epochs of one location. e3 is after the chevron was erased,
    # so its patch is the imprint - the recorded false positive itself, and
    # the only case here where the right answer is known in advance.
    for name in ("e1_2022-11", "e2_2024-09", "e3_2025-06"):
        q = ROOT / "output" / "epochs" / f"{name}.jpg"
        if q.exists():
            rows.append((name, q))
    out = []
    for no, path in rows:
        m = measure(path)
        m["no"] = no
        out.append(m)
        print(f"  {no}  角{str(m.get('angle_deg')):>5}  週期{str(m.get('period_px')):>5}  "
              f"duty {str(m.get('duty')):>6}  諧波殘差 {str(m.get('harmonic_residual')):>5}  "
              f"漆較亮 {str(m.get('paint_is_brighter')):>5}  振幅 {m.get('amplitude')}",
              flush=True)
    err = [o for o in out if o.get("duty") is None]
    ceil = [o for o in out if o.get("period_at_bank_ceiling")]
    print(f"\n  量不到 {len(err)}/{len(out)}: {[o['no'] for o in err]}")
    print(f"  週期頂到 bank 上限 {len(ceil)}/{len(out) - len(err)} "
          f"(上限本身從 28 拉到 80,它就回 80)")
    ok = [o for o in out if o.get("duty") is not None]
    sq = [o for o in ok if o["harmonic_residual"] <= SQUARE_MAX]
    no = [o for o in ok if o["harmonic_residual"] >= NOT_SQUARE_MIN]
    und = [o for o in ok if SQUARE_MAX < o["harmonic_residual"] < NOT_SQUARE_MIN]
    print(f"\n  量到 {len(ok)}/{len(out)}")
    print(f"  方波 {len(sq)}  非方波 {len(no)}  不決定 {len(und)}")
    if sq:
        d = np.array([o["duty"] for o in sq])
        br = sum(bool(o["paint_is_brighter"]) for o in sq)
        a = np.array([o["angle_deg"] for o in sq])
        print(f"  方波者 duty 中位 {np.median(d):.4f} 範圍 {d.min():.4f}-{d.max():.4f}"
              f"  (§171 是 0.400)")
        print(f"  方波者 角度 中位 {np.median(a):.1f} 範圍 {a.min():.0f}-{a.max():.0f}")
        print(f"  方波者 亮於周圍 {br}/{len(sq)}")
        print(f"  方波者: {[o['no'] for o in sq]}")
    if und:
        print(f"  不決定: {[o['no'] for o in und]}")
    (ROOT / "results" / "stage5_predicate.json").write_text(json.dumps(
        {"question": "the three §171 properties that periodicity does not carry",
         "method": __doc__.strip().splitlines()[0],
         "work_px": WORK, "n": len(out), "n_measured": len(ok),
         "duty_regulated": 0.400,
         "square_max": SQUARE_MAX, "not_square_min": NOT_SQUARE_MIN,
         "calibration": "synthetic, one profile per condition, 32 bins; a "
                        "property of the estimator, not of any road",
         "verdict": "THE LOCATOR FAILS. Unsupervised periodicity does not "
                    "find the chevron. The strongest Gabor response is the "
                    "coarsest kernel in the bank, which is shadow, kerb and "
                    "hoarding, not 20 cm stripes - and the period came back "
                    "at the bank's maximum on every frame at both 28 and 80, "
                    "so it is a ceiling and not a measurement. The two epoch "
                    "frames that DO contain a chevron return no profile at "
                    "all; the one where it was erased is the one that "
                    "measures. The §171 predicate in pipeline.py is sound "
                    "and has nothing to feed it.",
         "also": "results/chevron_periodic.json reports period_px_median "
                 "28.0 on 45 of 45 images, which is that bank's ceiling. "
                 "Its contrast figure stands; its period column does not. "
                 "Not in the figure registry, so nothing published moves.",
         "unmeasured": [o["no"] for o in err],
         "at_bank_ceiling": [o["no"] for o in ceil],
         "square": [o["no"] for o in sq], "not_square": [o["no"] for o in no],
         "undecided": [o["no"] for o in und],
         "duty_median_of_square": (None if not sq else
              round(float(np.median([o["duty"] for o in sq])), 4)),
         "per_image": out}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
