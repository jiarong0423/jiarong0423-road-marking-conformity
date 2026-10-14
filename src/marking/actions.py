"""What to do next, decided by what the photograph did and did not yield.

The competition's Agentic Vision criterion is explicit: the image result
must drive a subsequent plan, tool call, action or request for human
approval, and explaining a fixed result is not enough. The owner put the
same thing in his own words - 「系統要做的是提示,不是我跟你講你才做」.

They are the same requirement, and this module is the answer to it.

WHY IT IS NOT A LIST OF FINDINGS. Over 42 photographs of this road the
detectors report counts that do not survive being opened and looked at:
25 red lines of which 13 of 23 opened are something else, a hoarding box
that is 31.8 % hoarding by area, one §167 hit that is a false positive
while the line that does exist is missed. `docs/detectors.md` has
the table.

So the honest product is not "here is what is wrong with this road". It
is:

    這張照片能證明什麼
    不能證明什麼,以及為什麼
    你接下來該做什麼 —— 打開哪幾張看、去哪個機關要哪一份文件

A rider who photographs a road does not know that the excavation permit
for it is public, that it says 750 m by 3 m, that the hours in force
that day ended at 16:00, that his photograph is stamped 15:56, that the
traffic-management plan lives with 交通局 and not 養工處, or that the
line he is looking at might be §165 rather than §167 and that the two
mean different things to him. Telling him that is worth more than a
count he cannot rely on.

Each action carries `why` (what in this photograph caused it), `basis`
(the clause or record that makes it a real option) and `to` (who to ask,
where that applies). An action with no `why` tied to this frame is not
emitted.
"""
from __future__ import annotations

# Everything quoted here is in docs/ and checked by
# tests/test_basis_is_sourced.py's corpus. Nothing is invented; where
# this program is speaking for itself it says 本程式.

# 本程式未查證應依哪一條申請,只知道那是適用的法律。條號留白而不猜。
FOI = "政府資訊公開法(本程式未查證應依第幾條申請)"


FOI_EN = "Freedom of Government Information Act (which article applies is not checked by this program)"


def _act(kind, what, why, basis="", to="", evidence=None, en=None):
    """`en` is the same action in English: what, why and to. The judges read
    English, so every action carries both; the Chinese is what the cited
    documents say and stays the record (tests/test_basis_is_sourced.py)."""
    return {"action": kind, "what": what, "why": why,
            "basis": basis, "to": to, "evidence": evidence or {},
            "en": en or {}}


def next_actions(result: dict, *, photo: str | None = None) -> list[dict]:
    """The ranked things to do about THIS photograph.

    `result` is `situation.assess()`'s output. Ordered by what settles
    the most: a document that decides a question outright comes before
    an eyeball check, which comes before anything needing a site visit.
    """
    out = []
    findings = {f["code"]: f for f in (result.get("findings") or [])}
    taper = result.get("taper") or {}

    if result.get("state") == "NOT_A_ROAD_PHOTOGRAPH":
        return [_act("RETAKE",
                     "重拍:讓路面佔畫面下半部",
                     f"道路區域只佔畫面 {result.get('roi_frac', 0)*100:.1f}%,"
                     "低於 30%,本程式因此沒有量測任何東西",
                     to="拍攝者",
                     en={"what": "Retake: let the road fill the lower half of the frame",
                         "why": f"the road region covers only {result.get('roi_frac', 0)*100:.1f}% "
                                "of the frame, under 30%, so nothing was measured",
                         "to": "the photographer"})]

    # 1. Documents settle questions outright, so they come first.
    if "CARRIAGEWAY_OCCUPIED" in findings or "SURFACE_IN_PIECES" in findings:
        out.append(_act(
            "REQUEST_DOCUMENT",
            "向交通局申請該路段的交通維持計畫",
            "本張偵測到施工佔用或多層鋪面,而佔用的核准範圍、期間與"
            "漸變段設計只寫在交維計畫裡,照片上量不到",
            basis=f"{FOI};養工處管路面,交通局管交通管制",
            to="新北市政府交通局",
            en={"what": "Request the traffic management plan for this stretch from the "
                        "Traffic Department",
                "why": "this photo shows works occupying the road or a patched surface; "
                       "what was approved (extent, period, taper design) is written only in "
                       "the traffic management plan and cannot be measured in a photo",
                "to": "New Taipei City Traffic Department"}))
        out.append(_act(
            "CHECK_PUBLIC_RECORD",
            "查該路段的道路挖掘許可",
            "挖掘許可是公開資料,會寫出核准的長寬、期間與施工時段",
            basis="data.gov.tw 122989 新北市政府道路挖掘資訊",
            to="民眾可自行查詢",
            evidence={"已查到的案件":
                      "新北捷五所字第1140874494號,柏油長750公尺寬3公尺,"
                      "2025-05-06 至 2026-09-30,拍照當日適用日間09-16時"},
            en={"what": "Look up the road excavation permit for this stretch",
                "why": "excavation permits are public data and state the approved length, "
                       "width, period and working hours",
                "to": "anyone (open data, data.gov.tw 122989)"}))

    # 1b. The three documents the story ends on (docs/story-116.md), each
    #     emitted only when this frame measured the thing it would settle.
    rg = result.get("red_line_gap") or {}
    t427 = result.get("taper_table_4_2_7") or {}
    if "TWO_RED_LINES" in findings or "NO_LANE_CHANGE" in findings:
        why, why_en = [], []
        if "TWO_RED_LINES" in findings:
            why.append(f"本張量到新舊兩條紅線相距約 {rg.get('gap_m')} m,哪一條是現行要看核定函")
            why_en.append(f"this photo measured the new and old red lines about {rg.get('gap_m')} m "
                          "apart; which one is in force is in the approval letter")
        if "NO_LANE_CHANGE" in findings:
            why.append("本張偵測到雙白實線,它從哪裡開始畫、為何這樣畫,只寫在劃設圖說裡")
            why_en.append("this photo shows a double white line; where it starts and why is "
                          "written only in the marking plans")
        out.append(_act(
            "REQUEST_DOCUMENT",
            "向交通局申請該路段標線改繪核定函及劃設圖說",
            ";".join(why),
            basis=FOI,
            to="新北市政府交通局",
            en={"what": "Request the approval letter and marking plans for the repainting "
                        "from the Traffic Department",
                "why": "; ".join(why_en),
                "to": "New Taipei City Traffic Department"}))
    if t427.get("state") in ("STEEPER_THAN_REFERENCE", "WITHIN_REFERENCE", "INDETERMINATE"):
        out.append(_act(
            "REQUEST_DOCUMENT",
            "申請挖掘許可 1140874494 的交通維持計畫與施工圖說",
            f"本張量到槽化線漸變率約 {t427.get('ratio')}:1;"
            "要比 16:1(50 km/h)還是 5:1(施工期 30 km/h),取決於核定的設計速率",
            basis=f"{FOI};表 4.2.7(docs/evidence.md L19)",
            to="新北市政府(捷運工程局/工務局)",
            en={"what": "Request the traffic management plan and works drawings for "
                        "excavation permit 1140874494",
                "why": f"this photo measured the painted island's taper at about "
                       f"{t427.get('ratio')}:1; whether to compare it with 16:1 (50 km/h) "
                       "or 5:1 (30 km/h during the works) depends on the approved design speed",
                "to": "New Taipei City Government (Metro construction office / Public Works)"}))
    if "TWO_RED_LINES" in findings:
        out.append(_act(
            "REQUEST_DOCUMENT",
            "向區公所申請側溝工程竣工圖說與蓋板檢驗報告",
            "紅線外移後,側溝帶與溝蓋落在紅線內側;溝蓋與路面的落差、蓋板規格只在竣工資料裡",
            basis=FOI,
            to="樹林區公所工務課",
            en={"what": "Request the drain works' as-built drawings and the grate "
                        "inspection reports from the district office",
                "why": "with the red line moved out, the drain strip and its grates lie on "
                       "the road side of it; the step between grate and road and the grate "
                       "specification are only in the as-built records",
                "to": "Shulin District Office, Public Works Section"}))

    # 2. Things a person can settle by opening this frame and looking.
    for code, label, label_en in (("EDGE_NOT_CARRIAGEWAY", "§169 路緣紅線", "§169 kerbside red line"),
                                  ("NO_LANE_CHANGE", "§167 雙白實線", "§167 double white line"),
                                  ("CENTRE_LINE_SOLID", "§165 雙黃實線", "§165 double yellow line")):
        if code in findings:
            out.append(_act(
                "HUMAN_LOOK",
                f"打開這張的原解析度,確認{label}的框裡真的是那個東西",
                "本程式的這一類判定經逐張人眼檢查後,有相當比例不成立",
                basis="docs/detectors.md 的對照表",
                to="判讀者",
                evidence={"框": (findings[code].get("measured") or {}).get("px")},
                en={"what": f"Open this photo at full size and check that the box really "
                            f"holds a {label_en}",
                    "why": "when a person opened this program's detections of this kind photo "
                           "by photo, a large share were something else (docs/detectors.md)",
                    "to": "a person reviewing the photo"}))

    # 3. What this photograph structurally cannot answer.
    if taper.get("state") != "STEEPER_THAN_REFERENCE":
        out.append(_act(
            "CANNOT_FROM_PHOTO",
            "漸變段長度:這張照片答不了",
            f"擾動集成的狀態是 {taper.get('state')},"
            f"{taper.get('why', '各編碼版本不一致')}",
            basis="本程式在各編碼版本不一致時拒答,不給單一數值",
            to="需現場量測或交維計畫",
            en={"what": "Length of the lane-closing taper: this photo cannot answer it",
                "why": f"the re-encoding check came out {taper.get('state')}: "
                       f"{taper.get('why') or 'the encodings disagree'}",
                "to": "the traffic management plan"}))
    if rg.get("state") == "MEASURED":
        out.append(_act(
            "CANNOT_FROM_PHOTO",
            "紅線外移以外的公分數:這張照片答不了",
            "本張唯一的尺是新紅線的線寬(§169 一○公分),只用在同一條線旁的距離;"
            "溝蓋落差、車道寬沒有同一深度的尺",
            basis="scale_source = RED_LINE_WIDTH (only for red_line_gap)",
            to="現場拉尺",
            en={"what": "Any distance other than the red line's shift: this photo cannot answer it",
                "why": "the only ruler in this photo is the new red line's width (10 cm by "
                       "§169), and it holds only beside that line; the grate step and the "
                       "lane width have no ruler at their depth",
                "to": "the as-built records"}))
    else:
        out.append(_act(
            "CANNOT_FROM_PHOTO",
            "任何公分數:這張照片答不了",
            "沒有比例尺。相機高度未記錄;"
            + (f"紅線線寬這把尺這張也用不上({rg.get('why')})" if rg.get("why")
               else "而標線寬度不能拿來校正它自己要檢查的標線"),
            basis="scale_source = NONE",
            to="現場拉尺,或拍攝時記下相機高度",
            en={"what": "Any distance in centimetres: this photo cannot answer it",
                "why": "there is no ruler: the camera height is not recorded; "
                       + (f"the red line's width cannot be used as the ruler here either "
                          f"({rg.get('why')})" if rg.get("why")
                          else "and a marking's width cannot calibrate the marking it checks"),
                "to": "a burst of photos of a red line (see red_line_gap_burst), or the records"}))
    out.append(_act(
        "NOT_DETECTED",
        "水溝蓋:本程式辨識不到",
        "偵測器在三個畫面裡找到三個週期結構,沒有一個是溝蓋,已於 2026-09-21 移除",
        basis="現場紀錄與照片可見,本程式未能辨識",
        to="人眼",
        en={"what": "Drain grates: this program cannot recognise them online",
            "why": "the grate detector found three periodic structures in three frames and "
                   "none was a grate, so it was removed on 2026-09-21; the grate evidence "
                   "comes from a separate offline script checked photo by photo",
            "to": "a person looking at the photo"}))
    return out
