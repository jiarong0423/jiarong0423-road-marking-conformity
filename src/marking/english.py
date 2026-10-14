"""The response in English, first.

The judges read English, and until 2026-10-14 the endpoint answered in Traditional
Chinese: the summary, every finding and every next action. This module builds an
`en` block that the handler puts at the top of every response: what the photo
showed, what was measured and what was refused (with the reason), and what to do
next. It is built from the same structured result, never from the Chinese text,
so the numbers are the measured ones.

The Chinese fields stay as they are, after it: they quote the regulations and
documents word for word, and tests/test_basis_is_sourced.py checks those quotes
against docs/.
"""
from __future__ import annotations


def _n(v, fmt="{:.2f}"):
    return "?" if v is None else fmt.format(v)


def _finding(f: dict) -> str:
    code, m = f.get("code"), f.get("measured") or {}
    if code == "TAPER_TOO_STEEP":
        return (f"The lane-closing taper is at least {_n(m.get('times_required_at_least'), '{:.1f}')}x "
                f"steeper than the reference for the speed limit; its geometry suits at most "
                f"{_n(m.get('equivalent_kmh_at_most'), '{:.0f}')} km/h. This is the mildest of "
                f"{m.get('readings')} re-encoded readings, so no single value is given "
                "(reference: works traffic-control code, written for national freeways)")
    if code == "TAPER_BELOW_TABLE_4_2_7":
        return (f"The painted island opens at about {_n(m.get('ratio'), '{:.1f}')}:1 "
                f"(re-encoded readings spread {_n(m.get('spread'), '{:.1f}')}); design table "
                f"4.2.7 asks for {_n(m.get('need_ratio'), '{:.0f}')}:1 at "
                f"{_n(m.get('posted_kmh'), '{:.0f}')} km/h (used as a reference only)")
    if code == "TWO_RED_LINES":
        return (f"Two red lines: the intact new line and the worn old line beside it. The new "
                f"line's inner edge is {_n(m.get('gap_m'))} m from the old line's centre "
                f"(re-encoded readings {_n(m.get('min_m'))}-{_n(m.get('max_m'))} m). The ruler is "
                "the new line's own 10 cm width (§169)")
    if code == "EDGE_NOT_CARRIAGEWAY":
        return ("A red line runs along the right-hand edge. §169 allows it on a kerb, or on the "
                "road surface where there is no kerb; which one this is, and whether the drivable "
                "road ends here, this program cannot tell")
    if code == "NO_LANE_CHANGE":
        return ("A double white line: no lane changes here (§167), so a squeezed vehicle cannot "
                "move left")
    if code == "CENTRE_LINE_SOLID":
        return ("A double yellow line: the centre line, not to be crossed into oncoming traffic "
                "(§165; this project holds no text of §165, so only the colour is asserted)")
    if code == "CARRIAGEWAY_OCCUPIED":
        side = "left" if m.get("side") == "left" else "right"
        frac = m.get("width_frac")
        return (f"Works hoarding on the {side} takes "
                f"{'?' if frac is None else f'{frac * 100:.0f}'}% of the frame width at vehicle "
                "height; that side was drivable road, and traffic is squeezed into what is left")
    if code == "SURFACE_IN_PIECES":
        return (f"{m.get('surface_types')} different surfaces in the carriageway, so there are "
                "joins between old and new paving (the step at a join is not measured)")
    if code == "LANE_TOO_NARROW":
        return (f"Lane {_n(m.get('lane_width_m'))} m wide; a car and a scooter side by side need "
                f"{_n(m.get('need_car_m'))} m, a bus or truck and a scooter "
                f"{_n(m.get('need_heavy_m'))} m (0.5 m clearance, road traffic rules §101)")
    return f"{code}"


def _why(text):
    return None if text is None else str(text).replace("表 4.2.7", "design table 4.2.7")


def english(result: dict) -> dict:
    """The `en` block for one assess() result (and, when present, its burst)."""
    if result.get("state") == "NOT_A_ROAD_PHOTOGRAPH":
        return {"summary": "This is not a road photo: the road covers under 30% of the frame, "
                           "so nothing was measured. Retake it with the road in the lower half.",
                "next_actions": [a.get("en") for a in result.get("next_actions") or []]}
    findings = result.get("findings") or []
    rg = result.get("red_line_gap") or {}
    t427 = result.get("taper_table_4_2_7") or {}
    te = result.get("taper") or {}
    burst = result.get("red_line_gap_burst") or {}

    measured, refused = {}, {}
    if rg.get("state") == "MEASURED":
        measured["red_line_gap_m"] = {"value": rg.get("gap_m"), "range": [rg.get("min_m"), rg.get("max_m")],
                                      "how": "3 of 4 re-encodings of this photo agree within 5 cm"}
    else:
        refused["red_line_gap"] = _why(rg.get("why"))
    if burst.get("state") in ("MEASURED_ACROSS_BURST", "CONFIRMED_ACROSS_BURST"):
        measured["red_line_gap_across_photos_m"] = {
            "value": burst.get("gap_m"), "readings": burst.get("readings_m"),
            "how": burst.get("how")}
    elif burst.get("state"):
        refused["red_line_gap_across_photos"] = burst.get("why")
    if t427.get("ratio") is not None and t427.get("state") != "CANNOT_MEASURE":
        measured["island_taper_ratio"] = {"value": t427.get("ratio"), "state": t427.get("state"),
                                          "reference": t427.get("need_ratio"),
                                          "note": _why(t427.get("why"))}
    else:
        refused["island_taper_ratio"] = _why(t427.get("why"))
    if te.get("state") != "STEEPER_THAN_REFERENCE":
        refused["lane_closing_taper"] = f"{te.get('state')}: {_why(te.get('why'))}"
    refused["lane_width"] = "not checked: send lane_width_m; a photo has no scale of its own"
    refused["drain_grates"] = "not recognised online (detector removed 2026-09-21)"

    n = len(findings)
    summary = (f"{n} {'issue' if n == 1 else 'issues'} found in this photo"
               if n else "No issue this program can decide was found in this photo")
    if burst.get("state") == "MEASURED_ACROSS_BURST":
        summary += (f"; the red line's shift, refused on this photo alone, was measured across "
                    f"{len(burst.get('readings_m') or [])} photos taken seconds apart: "
                    f"{burst.get('gap_m')} m")
    elif burst.get("state") == "CONFIRMED_ACROSS_BURST":
        summary += (f"; the red line's shift ({rg.get('gap_m')} m) was confirmed on "
                    f"{len(burst.get('readings_m') or [])} photos taken seconds apart")
    return {"summary": summary + ".",
            "findings": [{"code": f.get("code"), "what": _finding(f)} for f in findings],
            "measured": measured,
            "not_measured_and_why": refused,
            "next_actions": [dict(a.get("en") or {}, action=a.get("action"))
                             for a in result.get("next_actions") or []],
            "language": "English summary first; the fields after this block keep the "
                        "regulations' own Traditional Chinese wording"}
