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
Both turned out to be too uncertain for the thresholds the rate is
compared against. That version answered INDETERMINATE to everything, correctly, and
is gone.

The response always carries `basis`, so a reader can see which document the
verdict is measured against and that its applicability to this road class is
unsettled. A verdict without its basis is an assertion.
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "/var/task/src")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))   # running from the repo
from marking import burst                 # noqa: E402
from marking.english import english       # noqa: E402
from marking.situation import assess      # noqa: E402

# The evidence MANIFESTs, so a photo of this project's own can be recognised and
# the photos taken seconds before and after it found. In the image they sit in
# evidence_index/ (aws/Dockerfile); in the repository, in evidence/.
INDEX = burst.load_index([p for p in (Path(__file__).resolve().parent / "evidence_index",
                                      Path(__file__).resolve().parent.parent / "evidence")
                          if p.is_dir()])

# Lambda's synchronous request payload is capped at 6 MB and base64 adds a
# third, so anything over about 4.4 MB of encoded text never reaches this
# code - API Gateway returns its own 413 and the caller learns nothing about
# why. The cap here is below that so the refusal comes from the gate, with a
# reason, like every other refusal it makes.
MAX_BYTES = 3 * 1024 * 1024

# A URL is fetched by this function, so it is not bound by the 6 MB request cap and
# an original full-size photo can be sent as it came off the phone. Only GitHub's
# raw file host, https, no redirects, a size cap and a timeout: the endpoint must
# not become a way to make AWS fetch arbitrary addresses.
URL_HOSTS = {"raw.githubusercontent.com"}
MAX_URL_BYTES = 15 * 1024 * 1024
URL_TIMEOUT_S = 20


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _fetch(url):
    """Bytes of an allowed URL, or ValueError with the reason."""
    u = urllib.parse.urlparse(url or "")
    if u.scheme != "https" or u.hostname not in URL_HOSTS:
        raise ValueError(f"only https URLs on {', '.join(sorted(URL_HOSTS))} are fetched")
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(urllib.request.Request(url, headers={"User-Agent": "road116-gate"}),
                     timeout=URL_TIMEOUT_S) as r:
        data = r.read(MAX_URL_BYTES + 1)
    if len(data) > MAX_URL_BYTES:
        raise ValueError(f"the file is over {MAX_URL_BYTES // 1024 // 1024} MB")
    return data


def _decode(blob):
    image = cv2.imdecode(np.frombuffer(blob, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("the bytes did not decode as an image")
    return image


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


def _token_ok(event):
    """The access gate, added 2026-09-23.

    When the function's ACCESS_TOKEN environment variable is set, a POST
    must carry the same value in the `x-access-token` header; otherwise it
    is refused before any image is decoded, so an unauthorised caller costs
    milliseconds, not a measurement. The token is set by the owner on the
    function and given to judges with the submission; it is never in this
    repository. Unset, the endpoint stays open as before.
    """
    want = os.environ.get("ACCESS_TOKEN")
    if not want:
        return True
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    got = headers.get("x-access-token") or ""
    return hmac.compare_digest(got.encode(), want.encode())


def handler(event, context):
    if event.get("requestContext", {}).get("http", {}).get("method") == "GET":
        return {"statusCode": 200,
                "headers": {"content-type": "application/json"},
                "body": json.dumps({
                    "service": "road marking taper gate",
                    "access": ("POST needs the x-access-token header; the token "
                               "is given with the competition submission"
                               if os.environ.get("ACCESS_TOKEN") else
                               "open: no token required"),
                    "opencv": cv2.__version__,
                    "post": {
                        "image_base64": "JPEG or PNG, <= 3 MB encoded. "
                                        "red_line_gap and taper_table_4_2_7 "
                                        "need the camera's original "
                                        "resolution: at 2000 px on the long "
                                        "side both refuse (checked "
                                        "2026-09-23 on F17/F30-32/F40). "
                                        "Re-save the full-size photo at JPEG "
                                        "90 (about 2.2 MB, under this cap) "
                                        "and send it to the Function URL "
                                        "given with the submission: it has "
                                        "no 30 s limit and takes about 2.5 "
                                        "minutes. Through API Gateway (30 s) "
                                        "a full-size photo times out",
                        "image_url": "instead of image_base64: an https URL on "
                                     "raw.githubusercontent.com, fetched by the "
                                     "function (up to 15 MB, so an original photo "
                                     "can be sent as it is). For example any photo "
                                     "in the repository's evidence/ folder",
                        "burst_base64 / burst_urls": "optional, up to 2 more photos "
                                     "taken a second apart from the same spot. "
                                     "For the repository's own photos they are "
                                     "found by capture time without being sent",
                        "burst": "optional, false to skip the second loop",
                        "fov_deg": "horizontal field of view of the lens",
                        "posted_kmh": "speed limit in force",
                        "lane_width_m": "optional. Without it the width "
                                        "check is skipped and said to be "
                                        "skipped; a photograph has no scale",
                    },
                    "returns": {
                        "en": "first in every response: the summary, findings, what "
                              "was measured and what was refused with the reason, "
                              "and the next actions, in English. The fields after "
                              "it keep the regulations' Traditional Chinese wording",
                        "red_line_gap_burst": "the second loop: when the red-line "
                              "gap is refused (or can be confirmed), the photos taken "
                              "within 3 s are fetched, registered to the first with "
                              "cv2.findTransformECCMultiScale (correlation >= 0.90), "
                              "measured, and the gap is reported only if 2 or more "
                              "agree within 5 cm; `trace` lists every step",
                        "scenario": "what a road user meets here. Every "
                                    "clause either quotes a value measured "
                                    "in this frame or names inline the "
                                    "clause it is read under",
                        "site_description_not_measured": "things that are "
                                    "true of this place and that this "
                                    "program did not measure - the drain "
                                    "covers under the red line, the bridge "
                                    "ahead. Kept apart from "
                                    "`scenario` so an unearned sentence "
                                    "has nowhere to sit",
                        "findings": "the same thing itemised, each with "
                                    "its measurement, basis and state",
                        "red_line_gap": "intact red line's inner edge to "
                                        "the worn line's centre, metres; the "
                                        "ruler is the line's own 10 cm "
                                        "width (§169). Reported only if "
                                        "at least 3 of 4 encodings of the "
                                        "bytes agree within 5 cm",
                        "taper_table_4_2_7": "chevron taper ratio, set beside "
                                             "表 4.2.7 (50 km/h 16:1) as a "
                                             "reference only: that table is "
                                             "written for lane shifts at "
                                             "turning lanes. Reported only if "
                                             "at least 3 of 4 encodings agree "
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
                        "TAPER_TOO_STEEP": "the lane-closing taper is steeper than the "
                                           "works code's reference (code p.9)",
                        "TAPER_BELOW_TABLE_4_2_7": "the painted island's taper is below "
                                                   "design table 4.2.7's ratio for the speed "
                                                   "(table 4.2.7 used as a reference only)",
                        "TWO_RED_LINES": "new and old red lines, and the distance between "
                                         "them (the line's 10 cm width as the ruler, §169)",
                        "NO_LANE_CHANGE": "double white line: no lane changes (§167)",
                        "EDGE_NOT_CARRIAGEWAY": "kerbside red line: the drivable road may "
                                                "end here (§169)",
                        "SURFACE_IN_PIECES": "joins between old and new paving in the "
                                             "carriageway (excavation review rules)",
                        "LANE_TOO_NARROW": "a car and a scooter side by side lack the "
                                           "legal clearance (§101)",
                        "CENTRE_LINE_SOLID": "double yellow line: the centre line (§165); "
                                             "unlike §167, it forbids crossing into "
                                             "oncoming traffic",
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

    if not _token_ok(event):
        return {"statusCode": 401,
                "headers": {"content-type": "application/json"},
                "body": json.dumps({"state": "UNAUTHORISED",
                                    "reason": "missing or wrong x-access-token header",
                                    "measured": False,
                                    "basis": "the request was refused before the gate ran"})}

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

    raw, url = req.get("image_base64"), req.get("image_url")
    if not raw and not url:
        return _bad("send image_base64, or image_url (https, raw.githubusercontent.com)")
    if raw:
        try:
            blob = base64.b64decode(raw)
        except Exception:
            return _bad("image_base64 is not base64")
        if len(blob) > MAX_BYTES:
            return _bad(f"the image is {len(blob)//1024} kB and the limit is "
                        f"{MAX_BYTES//1024} kB - Lambda caps a synchronous "
                        f"request at 6 MB and base64 adds a third. Re-save the "
                        f"full-size photo at JPEG quality 90 (a 12 MP phone photo "
                        f"is then about 2.2 MB), or send image_url; do not downscale it, because "
                        f"red_line_gap and taper_table_4_2_7 refuse at 2000 px", 413)
    else:
        try:
            blob = _fetch(url)
        except Exception as exc:
            return _bad(f"image_url: {exc}")
    try:
        image = _decode(blob)
    except ValueError as exc:
        return _bad(str(exc))

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

    # The second loop (src/marking/burst.py): if the red-line gap was refused, or
    # can be confirmed, fetch the photos taken seconds apart and decide again.
    if out.get("state") != "NOT_A_ROAD_PHOTOGRAPH" and req.get("burst", True) is not False:
        source = None
        try:                                       # the first loop's answer stands whatever happens here
            extras = []
            for i, b64 in enumerate((req.get("burst_base64") or [])[:burst.MAX_EXTRA]):
                extras.append({"label": f"burst_base64[{i}]",
                               "load": lambda b64=b64: _decode(base64.b64decode(b64))})
                source = "attached by the caller"
            for u in (req.get("burst_urls") or [])[:burst.MAX_EXTRA - len(extras)]:
                extras.append({"label": str(u).rsplit("/", 1)[-1], "load": lambda u=u: _decode(_fetch(u))})
                source = "attached by the caller"
            if not extras:
                me = burst.identify(INDEX, sha256=hashlib.sha256(blob).hexdigest(),
                                    filename=(url or "").rsplit("/", 1)[-1] or None)
                if me:
                    for n in burst.neighbours(INDEX, me):
                        extras.append({"label": f"{n['no']} ({n['seconds_apart']:.0f} s apart)",
                                       "load": lambda u=n["url"]: _decode(_fetch(u))})
                    source = f"found by capture time: this photo is {me['no']} in evidence/{me['set']}"
            b = burst.run(image, out.get("red_line_gap") or {}, float(req["fov_deg"]), extras,
                          attached=source == "attached by the caller")
        except Exception as exc:
            b = {"state": "ERROR", "why": f"{type(exc).__name__}: {exc}"}
        b["extras_source"] = source
        out["red_line_gap_burst"] = b
        out["next_actions"] = (out.get("next_actions") or []) + burst.actions(b)

    out = {"en": english(out), **out}
    return {"statusCode": 200,
            "headers": {"content-type": "application/json"},
            # `default=` because a numpy scalar anywhere in the result
            # used to make this raise, and this line is outside the try
            # that wraps assess() - so one numpy.bool_ turned every real
            # photograph into a 500 with no body. Casting at the source
            # fixes the known one; this stops the next one from taking
            # the whole response with it. E40.
            "body": json.dumps(out, ensure_ascii=False, default=_plain)}
