"""The second loop, run through the real handler on three cases, with its trace.

    python3 -B isolation/agentic/burst_demo.py      (writes results/agentic_burst_2026-10-14.json)

The handler fetches photos from the public repository by URL; here `_fetch` is
pointed at the same files in evidence/, so the run needs no network and reads
the bytes the MANIFEST's sha256 pins. Everything else is the code that runs on
Lambda.

  1. F31 sent whole: the gap is measured, F30 and F32 are found by capture time,
     fetched, registered by ECC and measured: confirmed or not
  2. F31 shrunk to 2000 px, F30 and F32 attached: the photo alone is refused,
     and the burst decides
  3. F31 shrunk, P64 (another place, another day) and F30 attached: ECC must
     refuse P64 although it reports convergence, leaving one photo, too few
"""
import base64
import importlib.util
import json
import os
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("handler", ROOT / "aws" / "handler.py")
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
RAW = "https://raw.githubusercontent.com/jiarong0423/jiarong0423-road-marking-conformity/main/evidence/"


def local_fetch(url):
    if not url.startswith(RAW):
        raise ValueError("not this repository's evidence")
    return (ROOT / "evidence" / url[len(RAW):]).read_bytes()


h._fetch = local_fetch
F30, F31, F32 = (RAW + f"field-2026-09-20/IMG_20260920_16001{i}.jpg" for i in (5, 6, 7))
P64 = RAW + "field-2026-09-23/IMG_20260923_063437.jpg"
full = cv2.imread(str(ROOT / "evidence/field-2026-09-20/IMG_20260920_160016.jpg"))
small = base64.b64encode(cv2.imencode(".jpg", cv2.resize(full, (1500, 2000), interpolation=cv2.INTER_AREA),
                                      [cv2.IMWRITE_JPEG_QUALITY, 90])[1]).decode()
CASES = [("F31 sent whole; neighbours found by capture time", {"image_url": F31}),
         ("F31 at 2000 px; F30 and F32 attached", {"image_base64": small, "burst_urls": [F30, F32]}),
         ("F31 at 2000 px; P64 (another place) and F30 attached", {"image_base64": small, "burst_urls": [P64, F30]})]

runs = []
for name, req in CASES:
    t = time.time()
    r = h.handler({"requestContext": {"http": {"method": "POST"}},
                   "body": json.dumps(dict(req, fov_deg=56.812, posted_kmh=50))}, None)
    b = json.loads(r["body"])
    bb = b.get("red_line_gap_burst") or {}
    runs.append({"case": name, "status": r["statusCode"], "seconds": round(time.time() - t, 1),
                 "first_photo_red_line_gap": {k: (b.get("red_line_gap") or {}).get(k) for k in ("state", "gap_m", "why")},
                 "burst": {k: bb.get(k) for k in ("state", "gap_m", "readings_m", "spread_m", "why", "how",
                                                  "extras_source", "trace")},
                 "en_summary": b["en"]["summary"],
                 "next_actions": [a.get("action") for a in b.get("next_actions") or []]})
    print(name, "->", bb.get("state"), bb.get("gap_m"), runs[-1]["seconds"], "s")

out = {"date": "2026-10-14", "opencv": cv2.__version__,
       "note": "aws/handler.py run locally; URLs read from evidence/ instead of the network",
       "thresholds": {"ecc_same_view_min_correlation": h.burst.SAME_VIEW_MIN_CORRELATION,
                      "agree_m": h.burst.AGREE_M, "max_seconds_apart": h.burst.MAX_GAP_S},
       "runs": runs}
p = ROOT / "results" / "agentic_burst_2026-10-14.json"
p.with_suffix(".json.tmp").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
os.replace(p.with_suffix(".json.tmp"), p)
