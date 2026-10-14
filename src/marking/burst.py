"""When the red-line gap is refused, go and get more evidence, and decide again.

Until 2026-10-14 a refusal ended the run: "this photo cannot answer it". A rider
does not take one photo, though; a phone takes a burst. So the refusal now
starts a second loop, and the image result decides each step of it:

  perceive  the red-line gap on the photo sent, under the 4-encoding gate
            (situation._red_line_gap). Did any encoding see the red-line pair?
  decide    worth more evidence only if the pair was seen at least once, or the
            gap was measured and can be confirmed. A photo with no red line gets
            no fetch: more photos of the same nothing would not help.
  act       find the photos taken within 3 s of this one (the evidence
            MANIFEST's capture times) or take the ones the caller attached,
            and fetch them
  perceive  register each to the first photo with OpenCV 5's
            cv2.findTransformECCMultiScale. A photo is used only if the
            correlation reaches 0.90: on the trial pairs
            (results/opencv5_matchers_trial.json) the same view a second apart
            gave 0.993-0.995 and a different view gave 0.70-0.73 while ECC
            still reported convergence, so convergence alone is not the gate.
            Then measure the gap on each, once, as received.
  decide    report the gap only if at least two photos measure it and they
            agree within 5 cm (the same tolerance as the encoding gate);
            otherwise ask for a retake, with the reason.

The I/O (fetching a URL) is the handler's; everything here takes images or
loader callables, so it runs the same in tests.
"""
from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from marking import phone

SAME_VIEW_MIN_CORRELATION = 0.90
AGREE_M = 0.05
MAX_GAP_S = 3
MAX_EXTRA = 2
REPO_RAW = "https://raw.githubusercontent.com/jiarong0423/jiarong0423-road-marking-conformity/main/evidence"


def load_index(roots) -> list[dict]:
    """Every evidence photo: set, file, capture time, sha256 (from the MANIFESTs)."""
    out = []
    for root in roots:
        for man in sorted(Path(root).glob("*/MANIFEST.csv")):
            for row in csv.DictReader(open(man, encoding="utf-8")):
                try:
                    t = datetime.strptime(row["captured"], "%Y:%m:%d %H:%M:%S")
                except (KeyError, ValueError):
                    continue
                out.append({"set": man.parent.name, "no": row.get("no"), "file": row["file"],
                            "captured": t, "sha256": row.get("sha256")})
    return out


def identify(index, *, sha256=None, filename=None):
    for e in index:
        if (sha256 and e["sha256"] == sha256) or (filename and e["file"] == filename):
            return e
    return None


def neighbours(index, entry, max_gap_s=MAX_GAP_S, k=MAX_EXTRA):
    """The photos of the same set taken within `max_gap_s` seconds, nearest first."""
    near = [(abs((e["captured"] - entry["captured"]).total_seconds()), e) for e in index
            if e["set"] == entry["set"] and e["file"] != entry["file"]]
    near = sorted(((d, e) for d, e in near if d <= max_gap_s), key=lambda de: (de[0], de[1]["file"]))
    return [dict(e, seconds_apart=d, url=f"{REPO_RAW}/{e['set']}/{e['file']}") for d, e in near[:k]]


def _grey_small(img, width=768):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    s = width / g.shape[1]
    return cv2.resize(g, (width, int(round(g.shape[0] * s))), interpolation=cv2.INTER_AREA)


def register(first, other) -> dict:
    """ECC (OpenCV 5, multi-scale) homography from `first` to `other`, on 768 px wide greys."""
    a, b = _grey_small(first), _grey_small(other)
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    p = cv2.ECCParameters()
    p.motionType = cv2.MOTION_HOMOGRAPHY
    try:
        cc, _ = cv2.findTransformECCMultiScale(a, b, np.eye(3, dtype=np.float32), p)
    except cv2.error as e:
        return {"converged": False, "same_view": False,
                "why": str(e).strip().splitlines()[-1][:160]}
    cc = round(float(cc), 3)
    return {"converged": True, "correlation": cc, "same_view": cc >= SAME_VIEW_MIN_CORRELATION,
            "why": None if cc >= SAME_VIEW_MIN_CORRELATION else
            f"ECC converged but the correlation {cc} is under {SAME_VIEW_MIN_CORRELATION}: "
            "not the same view"}


def worth_trying(rg: dict) -> tuple[bool, str]:
    if rg.get("state") == "MEASURED":
        return True, "measured on this photo; more photos can confirm it"
    seen = [r for r in (rg.get("probe") or {}).get("readings", []) if r.get("value") is not None]
    if seen:
        return True, (f"refused on this photo, but {len(seen)} of 4 encodings saw the red-line "
                      "pair; more photos of the same spot may settle it")
    return False, ("no encoding of this photo saw a red-line pair, so more photos of the "
                   "same spot would not help")


def decide(rg: dict, readings: list[dict]) -> dict:
    """The decision after the burst. `readings`: one per extra photo, with `gap_m` or None."""
    vals = [r["gap_m"] for r in readings if r.get("gap_m") is not None]
    if rg.get("state") == "MEASURED":
        vals = [rg["gap_m"]] + vals
    if len(vals) < 2:
        return {"state": "NOT_ENOUGH",
                "why": f"only {len(vals)} photo(s) measured the gap; 2 that agree are needed",
                "readings_m": vals}
    spread = round(max(vals) - min(vals), 3)
    if spread > AGREE_M:
        return {"state": "DISAGREE", "readings_m": vals, "spread_m": spread,
                "why": f"the photos read {min(vals):.3f}-{max(vals):.3f} m, a spread of "
                       f"{spread:.3f} m, more than {AGREE_M} m"}
    state = "CONFIRMED_ACROSS_BURST" if rg.get("state") == "MEASURED" else "MEASURED_ACROSS_BURST"
    return {"state": state, "gap_m": round(float(np.median(vals)), 3), "readings_m": vals,
            "spread_m": spread,
            "how": f"{len(vals)} photos taken seconds apart, each registered to the first by "
                   f"ECC (correlation >= {SAME_VIEW_MIN_CORRELATION}), agree within {AGREE_M} m"}


def run(first, rg: dict, fov_deg: float, extras: list[dict], attached: bool = False) -> dict:
    """The second loop. `extras`: [{"label", "load": callable -> BGR image}], nearest first.

    `attached`: the caller sent these photos, which is a request to measure them;
    the worth-trying gate is for photos this function would go and fetch itself."""
    trace, t0 = [], time.time()
    go, reason = worth_trying(rg)
    if attached and extras and not go:
        go, reason = True, "the caller attached photos taken seconds apart, so they are measured"
    trace.append({"step": "decide", "what": "is more evidence worth fetching?", "result": go, "why": reason})
    if not go:
        return {"state": "NOT_TRIED", "why": reason, "trace": trace}
    if not extras:
        trace.append({"step": "decide", "what": "find photos taken within 3 s", "result": 0,
                      "why": "no neighbouring photo is known and none was attached"})
        return {"state": "NO_BURST", "why": "no photos taken seconds apart were found or attached",
                "trace": trace}
    readings = []
    for x in extras[:MAX_EXTRA]:
        rec = {"photo": x["label"]}
        t = time.time()
        try:
            img = x["load"]()
        except Exception as e:                       # a failed fetch is a reading, not a crash
            rec.update(gap_m=None, why=f"could not load: {type(e).__name__}: {e}")
            trace.append({"step": "act", "tool": "fetch", "photo": x["label"], "ok": False,
                          "why": rec["why"], "s": round(time.time() - t, 1)})
            readings.append(rec)
            continue
        trace.append({"step": "act", "tool": "fetch", "photo": x["label"], "ok": True,
                      "px": [int(img.shape[1]), int(img.shape[0])], "s": round(time.time() - t, 1)})
        t = time.time()
        reg = register(first, img)
        trace.append({"step": "perceive", "tool": "cv2.findTransformECCMultiScale", "photo": x["label"],
                      **reg, "s": round(time.time() - t, 1)})
        rec["registration"] = reg
        if not reg["same_view"]:
            rec.update(gap_m=None, why=reg["why"])
            readings.append(rec)
            continue
        t = time.time()
        h, w = img.shape[:2]
        o = phone.redline_gap(img, phone.K_from_fov(w, h, fov_deg))
        gap = (o.get("summary") or {}).get("median_m") if o.get("ok") else None
        rec.update(gap_m=gap, why=None if o.get("ok") else o.get("why"))
        trace.append({"step": "perceive", "tool": "red-line gap", "photo": x["label"],
                      "gap_m": gap, "why": rec["why"], "s": round(time.time() - t, 1)})
        readings.append(rec)
    out = decide(rg, readings)
    trace.append({"step": "decide", "what": "do the photos agree?", "result": out["state"],
                  "why": out.get("why") or out.get("how")})
    out.update(photos=readings, trace=trace, seconds=round(time.time() - t0, 1))
    return out


def actions(burst: dict) -> list[dict]:
    """What the burst's outcome asks the person to do next (same shape as actions.next_actions)."""
    from marking.actions import _act
    st = burst.get("state")
    if st in ("NO_BURST", "NOT_ENOUGH", "DISAGREE"):
        return [_act("RETAKE_BURST",
                     "在同一個位置連拍 2–3 張(間隔約 1 秒),連同這張一起送",
                     f"本程式的紅線位移需要至少兩張照片量到且相差 5 公分以內;"
                     f"這次的結果是 {st}",
                     basis="本程式的判準:兩張以上照片一致才報數字",
                     to="拍攝者",
                     en={"what": "Take 2-3 photos a second apart from the same spot and send "
                                 "them with this one (burst_base64 or burst_urls)",
                         "why": f"the red-line gap needs at least two photos that measure it "
                                f"and agree within 5 cm; this time: {st} ({burst.get('why')})",
                         "to": "the photographer"})]
    return []
