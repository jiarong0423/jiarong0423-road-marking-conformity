"""The second loop (src/marking/burst.py) and the English block (src/marking/english.py).

The second loop must do what its docstring says: fetch more evidence only when the
first photo gives a reason to, accept another photo only if ECC registers it at
correlation >= 0.90 (ECC alone reports convergence on a different view), and report
a gap only when two or more photos agree within 5 cm. The English block must carry
no Chinese, because it exists for readers who do not read Chinese.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from marking import burst                      # noqa: E402
from marking.actions import next_actions       # noqa: E402
from marking.english import english            # noqa: E402

CJK = re.compile(r"[一-鿿]")
EV20 = ROOT / "evidence" / "field-2026-09-20"
EV23 = ROOT / "evidence" / "field-2026-09-23"
MEASURED = {"state": "MEASURED", "gap_m": 0.673, "min_m": 0.658, "max_m": 0.678}
SEEN_ONCE = {"state": "CANNOT_MEASURE", "why": "x",
             "probe": {"readings": [{"value": 0.66}, {"value": None}, {"value": None}, {"value": None}]}}
NEVER_SEEN = {"state": "CANNOT_MEASURE", "why": "x",
              "probe": {"readings": [{"value": None}] * 4}}


def test_decide_reports_only_when_two_photos_agree_within_5_cm():
    assert burst.decide(NEVER_SEEN, [{"gap_m": 0.68}, {"gap_m": 0.635}])["state"] == "MEASURED_ACROSS_BURST"
    assert burst.decide(NEVER_SEEN, [{"gap_m": 0.68}, {"gap_m": 0.62}])["state"] == "DISAGREE"
    assert burst.decide(NEVER_SEEN, [{"gap_m": 0.68}, {"gap_m": None}])["state"] == "NOT_ENOUGH"
    assert burst.decide(MEASURED, [{"gap_m": 0.68}])["state"] == "CONFIRMED_ACROSS_BURST"
    assert burst.decide(MEASURED, [{"gap_m": 0.60}])["state"] == "DISAGREE"


def test_more_evidence_is_fetched_only_when_the_first_photo_gives_a_reason():
    assert burst.worth_trying(MEASURED)[0]
    assert burst.worth_trying(SEEN_ONCE)[0]
    assert not burst.worth_trying(NEVER_SEEN)[0]
    out = burst.run(None, NEVER_SEEN, 56.8, [{"label": "x", "load": lambda: 1 / 0}])
    assert out["state"] == "NOT_TRIED"          # nothing was loaded
    out = burst.run(None, NEVER_SEEN, 56.8, [{"label": "x", "load": lambda: 1 / 0}], attached=True)
    assert out["state"] == "NOT_ENOUGH" and "could not load" in out["photos"][0]["why"]


def test_neighbours_are_found_by_capture_time():
    ix = burst.load_index([ROOT / "evidence"])
    me = burst.identify(ix, filename="IMG_20260920_160016.jpg")
    assert me["no"] == "F31"
    near = burst.neighbours(ix, me)
    assert [n["no"] for n in near] == ["F30", "F32"]
    assert all(n["url"].startswith("https://raw.githubusercontent.com/") for n in near)


@pytest.mark.skipif(not (EV20 / "IMG_20260920_160016.jpg").exists(), reason="evidence not present")
def test_ecc_accepts_the_same_view_and_refuses_a_different_one():
    f31 = cv2.imread(str(EV20 / "IMG_20260920_160016.jpg"))
    same = burst.register(f31, cv2.imread(str(EV20 / "IMG_20260920_160015.jpg")))
    other = burst.register(f31, cv2.imread(str(EV23 / "IMG_20260923_063437.jpg")))
    assert same["same_view"] and same["correlation"] >= burst.SAME_VIEW_MIN_CORRELATION
    assert not other["same_view"]                # whether or not ECC says it converged


def _all_findings_result():
    m = {"TAPER_TOO_STEEP": {"times_required_at_least": 2.1, "equivalent_kmh_at_most": 34, "readings": 9},
         "TAPER_BELOW_TABLE_4_2_7": {"ratio": 11.9, "spread": 0.4, "need_ratio": 16, "posted_kmh": 50},
         "TWO_RED_LINES": MEASURED, "EDGE_NOT_CARRIAGEWAY": {}, "NO_LANE_CHANGE": {},
         "CENTRE_LINE_SOLID": {}, "CARRIAGEWAY_OCCUPIED": {"side": "left", "width_frac": 0.68},
         "SURFACE_IN_PIECES": {"surface_types": 4},
         "LANE_TOO_NARROW": {"lane_width_m": 3.13, "need_car_m": 3.03, "need_heavy_m": 3.75}}
    r = {"findings": [{"code": c, "what": "中文", "measured": v} for c, v in m.items()],
         "red_line_gap": MEASURED,
         "taper": {"state": "CANNOT_MEASURE", "why": "readings scatter"},
         "taper_table_4_2_7": {"state": "STEEPER_THAN_REFERENCE", "ratio": 11.9, "need_ratio": 16,
                               "why": "表 4.2.7 has no row"},
         "red_line_gap_burst": {"state": "CONFIRMED_ACROSS_BURST", "gap_m": 0.673,
                                "readings_m": [0.673, 0.68, 0.635], "how": "3 photos agree"}}
    r["next_actions"] = next_actions(r)
    return r


def test_the_english_block_has_no_chinese_and_every_finding_and_action():
    r = _all_findings_result()
    en = english(r)
    text = json.dumps(en, ensure_ascii=False)
    assert not CJK.search(text), CJK.findall(text)[:10]
    assert [f["code"] for f in en["findings"]] == [f["code"] for f in r["findings"]]
    assert all(f["what"] != f["code"] for f in en["findings"])     # each code has its own sentence
    assert len(en["next_actions"]) == len(r["next_actions"])
    assert "confirmed on 3 photos" in en["summary"]


def test_every_action_carries_english_what_why_and_to():
    for a in _all_findings_result()["next_actions"] + burst.actions({"state": "DISAGREE", "why": "x"}):
        assert all(a["en"].get(k) for k in ("what", "why", "to")), a["action"]
        assert not CJK.search(json.dumps(a["en"], ensure_ascii=False)), a["action"]


def _handler():
    spec = importlib.util.spec_from_file_location("handler_t", ROOT / "aws" / "handler.py")
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    return h


@pytest.mark.parametrize("url", ["http://raw.githubusercontent.com/a.jpg", "https://example.com/a.jpg",
                                 "https://169.254.169.254/latest", "file:///etc/passwd", ""])
def test_only_https_github_raw_urls_are_fetched(url):
    with pytest.raises(ValueError):
        _handler()._fetch(url)


def test_the_response_starts_with_english_and_the_second_loop_can_be_skipped(monkeypatch):
    monkeypatch.delenv("ACCESS_TOKEN", raising=False)
    import base64
    img = np.full((900, 1200, 3), 128, np.uint8)
    b64 = base64.b64encode(cv2.imencode(".jpg", img)[1]).decode()
    h = _handler()
    for skip in (False, True):
        req = {"image_base64": b64, "fov_deg": 56.8, "posted_kmh": 50}
        if skip:
            req["burst"] = False
        r = h.handler({"requestContext": {"http": {"method": "POST"}}, "body": json.dumps(req)}, None)
        body = json.loads(r["body"])
        assert r["statusCode"] == 200 and next(iter(body)) == "en"
        assert ("red_line_gap_burst" in body) is (not skip and body.get("state") != "NOT_A_ROAD_PHOTOGRAPH")


# 2026-10-14, after the three-way review of v17


def test_a_measured_first_photo_is_not_told_to_retake_when_nothing_confirms_it():
    for extras in ([], [{"label": "x", "load": lambda: 1 / 0}]):
        b = burst.run(None, MEASURED, 56.8, extras)
        assert b["state"] in ("NO_BURST", "NOT_ENOUGH") and b["first_state"] == "MEASURED"
        assert burst.actions(b) == []
    refused = burst.run(None, SEEN_ONCE, 56.8, [])
    assert [a["action"] for a in burst.actions(refused)] == ["RETAKE_BURST"]
    disagree = dict(burst.decide(MEASURED, [{"gap_m": 0.55}]), first_state="MEASURED")
    assert [a["action"] for a in burst.actions(disagree)] == ["RETAKE_BURST"]


def test_no_extra_photo_is_started_without_time_left():
    import time
    loads = []
    b = burst.run(None, MEASURED, 56.8, [{"label": "x", "load": lambda: loads.append(1)}],
                  deadline=time.time() + 10)          # 10 s left: too little for a photo
    assert loads == [] and "time budget" in b["photos"][0]["why"]


def test_lane_width_is_called_unchecked_only_when_it_was_not_given():
    r = _all_findings_result()
    assert "lane_width" not in english(r)["not_measured_and_why"]
    r["not_checked"] = ["lane_width: 需提供車道寬,照片無比例尺"]
    assert "lane_width" in english(r)["not_measured_and_why"]


def test_the_english_block_never_prints_none():
    text = json.dumps(english({"findings": [], "next_actions": []}), ensure_ascii=False)
    assert "None" not in text and "null" not in text


def test_a_disagreeing_burst_is_said_in_the_summary():
    r = _all_findings_result()
    r["red_line_gap_burst"] = {"state": "DISAGREE", "why": "the photos read 0.55-0.68 m"}
    assert "disagree" in english(r)["summary"]


def test_only_this_repositorys_urls_are_recognised_by_file_name(monkeypatch):
    monkeypatch.delenv("ACCESS_TOKEN", raising=False)
    h = _handler()
    calls = []
    h._fetch = lambda u: calls.append(u) or cv2.imencode(".jpg", np.full((900, 1200, 3), 128, np.uint8))[1].tobytes()
    seen = []
    real = h.burst.identify
    h.burst.identify = lambda ix, sha256=None, filename=None: seen.append(filename) or real(ix, sha256=sha256, filename=filename)
    try:
        for url in ("https://raw.githubusercontent.com/someone/else/main/IMG_20260920_160016.jpg",
                    burst.REPO_RAW + "/field-2026-09-20/IMG_20260920_160016.jpg"):
            h.handler({"requestContext": {"http": {"method": "POST"}},
                       "body": json.dumps({"image_url": url, "fov_deg": 56.8, "posted_kmh": 50})}, None)
    finally:
        h.burst.identify = real
    assert seen == [None, "IMG_20260920_160016.jpg"]


def test_attached_photos_have_the_same_size_limit_and_a_pixel_cap():
    import base64
    h = _handler()
    with pytest.raises(ValueError):
        h._b64_photo(base64.b64encode(b"\0" * (h.MAX_BYTES + 1)).decode())
    big = cv2.imencode(".png", np.zeros((8000, 7000), np.uint8))[1].tobytes()   # 56 MP, small file
    with pytest.raises(ValueError):
        h._decode(big)
