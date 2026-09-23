"""The gate behind an HTTP call.

One POST, and back comes the set of things wrong with the road in that
photograph - not a number. A taper three times too steep does not hurt
anybody on its own; what hurts is that it arrives beside a lane too narrow
to share, an edge that is not carriageway, a double white line, and a
surface in pieces. Each is arguable alone. Together they leave a rider with
no lawful place to be, and that is what the caller is told.

One POST, one verdict, in the older sense. The request carries the photograph and **the lens**,
and nothing else: the angle between two marking directions is invariant to
the camera's rotation, so the pitch does not enter, the road supplies its
own bearing from its own markings, and a rate needs no scale.

Until 2026-09-20 this asked for the pitch and the road's bearing as well.
Both turned out to be unavailable - the Street View pitch carries a degree
or two of the survey car's suspension, and the bearing measured
141.87 ± 8.32°, which is ±0.131 on a rate whose thresholds are 0.172 and
0.062. That version answered INDETERMINATE to everything, correctly, and
is gone.

The response always carries `basis`, so a reader can see which document the
verdict is measured against and that its applicability to this road class is
unsettled. A verdict without its basis is an assertion.
"""

import base64
import json
import sys

import cv2
import numpy as np

sys.path.insert(0, "/var/task/src")
from marking.situation import assess     # noqa: E402

# Lambda's synchronous request payload is capped at 6 MB and base64 adds a
# third, so anything over about 4.4 MB of encoded text never reaches this
# code - API Gateway returns its own 413 and the caller learns nothing about
# why. The cap here is below that so the refusal comes from the gate, with a
# reason, like every other refusal it makes.
MAX_BYTES = 3 * 1024 * 1024


def _plain(value):
    """numpy scalars and arrays, as the JSON types they stand for."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"{type(value).__name__} is not JSON-serialisable")


def _bad(message, code=400):
    """A refusal before the gate is reached.

    These used to return {"state": "CANNOT_MEASURE"} with no basis - the
    same wire shape as a measured refusal, from the file whose own docstring
    says a verdict without its basis is an assertion. They are now marked as
    what they are: the request never reached the measurement.
    """
    return {"statusCode": code,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"state": "BAD_REQUEST", "reason": message,
                                "measured": False,
                                "basis": "the request was rejected before the "
                                         "gate ran, so nothing was measured "
                                         "and no reference applies"},
                               ensure_ascii=False)}


def handler(event, context):
    if event.get("requestContext", {}).get("http", {}).get("method") == "GET":
        return {"statusCode": 200,
                "headers": {"content-type": "application/json"},
                "body": json.dumps({
                    "service": "road marking taper gate",
                    "opencv": cv2.__version__,
                    "post": {
                        "image_base64": "JPEG or PNG, <= 3 MB encoded. "
                                        "red_line_gap and taper_table_4_2_7 "
                                        "need the camera's original "
                                        "resolution: at 2000 px on the long "
                                        "side both refuse (checked "
                                        "2026-09-23 on F17/F30-32/F40), and "
                                        "originals are 5-10 MB, over this "
                                        "cap. Until the upload path changes "
                                        "they will usually say CANNOT_MEASURE",
                        "fov_deg": "horizontal field of view of the lens",
                        "posted_kmh": "speed limit in force",
                        "lane_width_m": "optional. Without it the width "
                                        "check is skipped and said to be "
                                        "skipped; a photograph has no scale",
                    },
                    "returns": {
                        "scenario": "what a road user meets here. Every "
                                    "clause either quotes a value measured "
                                    "in this frame or names inline the "
                                    "clause it is read under",
                        "site_description_not_measured": "things that are "
                                    "true of this place and that this "
                                    "program did not measure - the drain "
                                    "covers under the red line, the bridge "
                                    "430 m ahead. Kept apart from "
                                    "`scenario` so an unearned sentence "
                                    "has nowhere to sit",
                        "findings": "the same thing itemised, each with "
                                    "its measurement, basis and state",
                        "red_line_gap": "intact red line's inner edge to "
                                        "the worn line's centre, metres; the "
                                        "ruler is the line's own 10 cm "
                                        "width (§169). Reported only if "
                                        "four encodings of the bytes agree "
                                        "within 5 cm",
                        "taper_table_4_2_7": "chevron taper ratio against "
                                             "表 4.2.7 (50 km/h 16:1). Reported "
                                             "only if four encodings agree "
                                             "within 10%; one re-encode at "
                                             "quality 97 moved F40 from "
                                             "11.9:1 to 23.2:1",
                        "site_116_not_measured_from_this_photograph":
                            "the 116 縣道 site's published figures, attached "
                            "to every response, each with its results/ "
                            "source. Not measured from the photograph sent",
                        "state": "NOT_A_ROAD_PHOTOGRAPH when the road "
                                 "region is under 30% of the frame; then "
                                 "nothing was measured and every other key "
                                 "is empty except the site block, which is "
                                 "attached to every response",
                    },
                    "finding_codes": {
                        "TAPER_TOO_STEEP": "車道縮減漸變段過陡 (守則 p.9)",
                        "TAPER_BELOW_TABLE_4_2_7": "槽化線漸變率低於表 4.2.7 "
                                                   "該速率的比例",
                        "TWO_RED_LINES": "新舊兩條紅線,量到兩者距離 (§169 線寬當尺)",
                        "NO_LANE_CHANGE": "雙白實線，禁止變換車道 (§167)",
                        "EDGE_NOT_CARRIAGEWAY": "路緣紅線，可行駛路面至此為止 (§169)",
                        "SURFACE_IN_PIECES": "行車道內有新舊鋪面銜接處 (挖掘審查原則)",
                        "LANE_TOO_NARROW": "汽機車並行不足法定間隔 (§101)",
                        "CENTRE_LINE_SOLID": "雙黃實線，分向限制線 (§165)。"
                                             "與 §167 不同:它禁止的是跨越對向",
                    },
                    "not_needed": {
                        "pitch": "the angle measured is invariant to camera "
                                 "rotation",
                        "road_bearing": "the road's own markings give it",
                        "scale": "a taper rate is dimensionless",
                    },
                    "states": {
                        "WITHIN_REFERENCE": "clear of the reference by more "
                                            "than the measurement's doubt",
                        "STEEPER_THAN_REFERENCE": "past it by more than the "
                                                  "doubt",
                        "INDETERMINATE": "measured, but nearer the reference "
                                         "than this measurement can resolve",
                        "CANNOT_MEASURE": "the photograph does not show what "
                                          "is needed",
                    },
                }, ensure_ascii=False)}

    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception:
            return _bad("the request body is not text")
    try:
        req = json.loads(body)
    except Exception:
        return _bad("the request body is not JSON")

    raw = req.get("image_base64")
    if not raw:
        return _bad("no image_base64 in the request")
    try:
        blob = base64.b64decode(raw)
    except Exception:
        return _bad("image_base64 is not base64")
    if len(blob) > MAX_BYTES:
        return _bad(f"the image is {len(blob)//1024} kB and the limit is "
                    f"{MAX_BYTES//1024} kB - Lambda caps a synchronous "
                    f"request at 6 MB and base64 adds a third. Downscale it: "
                    f"the gate measures in the bird's eye plane and gains "
                    f"nothing above about 2000 px on the long side", 413)
    image = cv2.imdecode(np.frombuffer(blob, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return _bad("the bytes did not decode as an image")

    missing = [k for k in ("fov_deg", "posted_kmh") if req.get(k) is None]
    if missing:
        return _bad(f"missing: {', '.join(missing)}")

    try:
        out = assess(image, fov_deg=float(req["fov_deg"]),
                     posted_kmh=float(req["posted_kmh"]),
                     lane_width_m=(None if req.get("lane_width_m") is None
                                   else float(req["lane_width_m"])))
    except Exception as exc:                       # never a 500 with no reason
        return _bad(f"the pipeline raised {type(exc).__name__}: {exc}", 500)

    out["image_px"] = [int(image.shape[1]), int(image.shape[0])]
    out["opencv"] = cv2.__version__
    return {"statusCode": 200,
            "headers": {"content-type": "application/json"},
            # `default=` because a numpy scalar anywhere in the result
            # used to make this raise, and this line is outside the try
            # that wraps assess() - so one numpy.bool_ turned every real
            # photograph into a 500 with no body. Casting at the source
            # fixes the known one; this stops the next one from taking
            # the whole response with it. E40.
            "body": json.dumps(out, ensure_ascii=False, default=_plain)}
