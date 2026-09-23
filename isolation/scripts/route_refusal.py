#!/usr/bin/env python3
"""Say what kind of refusal a refusal was, for one photograph or all 42.

Standing rule 7's open instance, closed. `src/marking/route.py` was 260
lines that nothing imported: a router built, tuned from 0.27 to 0.91
confidence by handing the model the nine-cell grid instead of an
aggregate, written up, and never connected. A capability nothing can
reach is not a capability.

**Why here and not inside `assess()`.** `route()` calls a typed-judgment
model. Putting it in the assessment would make the assessment
non-deterministic and network-dependent, and reproducibility is this
project's whole argument - the 42 photographs ship at native resolution
for exactly that reason. So the split is:

    assess()            pure, offline, same bytes in, same verdict out
    route_refusal.py    optional, afterwards, on the output

The gate decides what is measurable. This decides what to do when it
would not answer, which is a different question and the one place a
model earns its call. Nothing in the deployed path changes.

    python3 scripts/route_refusal.py --dry-run          # all 42, no model
    python3 scripts/route_refusal.py --photo F05        # one, asks
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]   # repo root: this file is isolation/scripts/
# isolation/src FIRST: these scripts serve the isolated modules, and
# isolation/src/marking/__init__.py extends the package path to the real
# src/marking so the shared parts still resolve. Moving these scripts
# into isolation/ on 2026-09-21 broke all three by leaving ROOT and this
# path pointing one directory too shallow; none was run afterwards.
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "isolation" / "src"))

from marking.pipeline import provenance           # noqa: E402
from marking.route import route_ensemble          # noqa: E402
from marking.situation import assess              # noqa: E402

INDEX = ROOT / "results" / "field_index_2026-09-20.csv"
EVID = ROOT / "evidence" / "field-2026-09-20"

# 116 縣道 (樹林中正路). docs/timeline-116.md: the limit was 50 when these
# markings were laid, and §171's taper length goes as V squared, so this
# is an input to the verdict and not a label.
POSTED_KMH = 50.0


def route_one(no: str, path: Path, *, dry_run: bool) -> dict:
    image = cv2.imread(str(path))
    if image is None:
        return {"no": no, "error": f"unreadable: {path}"}
    prov = provenance(image, path=str(path))
    if prov.focal_px is None:
        return {"no": no, "error": "no focal length in the file's EXIF"}
    fov = math.degrees(2 * math.atan(image.shape[1] / (2 * prov.focal_px)))
    result = assess(image, fov_deg=fov, posted_kmh=POSTED_KMH)
    taper = result.get("taper") or {}
    found = bool(result.get("carriageway_found",
                            "CARRIAGEWAY_OCCUPIED" in (result.get("findings") or [])))
    r = route_ensemble(taper, found, dry_run=dry_run)
    return {"no": no, "file": path.name,
            "fov_deg": round(fov, 2),
            "taper_state": taper.get("state"),
            "readings": taper.get("readings"),
            "action": r.action, "confidence": r.confidence,
            "asked": r.asked, "why": r.why}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--photo", help="one F-number, e.g. F05; default all 42")
    ap.add_argument("--dry-run", action="store_true",
                    help="settle by predicate only and never call the model")
    ap.add_argument("--out", type=Path, help="write JSON here")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(INDEX)))
    if a.photo:
        rows = [r for r in rows if r["no"] == a.photo]
        if not rows:
            print(f"no such photograph: {a.photo}", file=sys.stderr)
            return 2

    out = [route_one(r["no"], EVID / r["file"], dry_run=a.dry_run) for r in rows]
    # Three outcomes, not two. A dry run does not settle anything by
    # predicate - it declines to ask - and counting it as settled would
    # print an unanswered question as an answered one.
    asked = sum(bool(o.get("asked")) for o in out)
    deferred = sum(o.get("action") == "DRY_RUN" for o in out)
    settled = len(out) - asked - deferred
    print(f"{len(out)} photographs: {settled} settled by predicate, "
          f"{asked} reached the model, {deferred} would have been asked "
          f"and were not")
    for o in out:
        c = "" if o.get("confidence") is None else f" {o['confidence']:.2f}"
        print(f"  {o['no']}  {str(o.get('taper_state')):<24} -> "
              f"{o.get('action')}{c}  {o.get('why','')[:56]}")
    if a.out:
        a.out.write_text(json.dumps(
            {"dry_run": a.dry_run, "n": len(out), "asked": asked,
             "settled_by_predicate": settled, "would_have_been_asked": deferred,
             "note": "route_ensemble over the field set; assess() is unchanged "
                     "and stays deterministic - see this script's docstring",
             "routes": out}, indent=1, ensure_ascii=False))
        print(f"  -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
