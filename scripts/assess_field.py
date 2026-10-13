#!/usr/bin/env python3
"""Run `assess()` over all 42 field photographs and write down what it said.

E24, closed. `assess()` is the delivery function - `aws/handler.py` calls
it and nothing else does - and it had no driver. On 2026-09-22 a second
look found it is not quite true that it had no test either: two tests in
`tests/test_scenario_claims.py` reach it. But they replace
`road_region`, `_segments` and all four detectors with stubs and hand it
`np.zeros((800, 600, 3))`, so nothing that assess() actually computes is
exercised. No run of the current code over the 42 photographs had ever
been recorded, which by standing rule 1 makes every population-level
number this project quotes about `assess()` a hypothesis.

So this is that run.

**The field of view is read from the file, not supplied.** Every angle
downstream goes through K, 3 of the 42 photographs were taken at
f35 = 46 mm and the other 39 at 24 mm, and `aws/handler.py` has passed a
hand-supplied 60 every time (E15). The derivation is the one in
`isolation/scripts/route_refusal.py`:

    focal_px = f35 * hypot(w, h) / 43.267        # 35 mm frame diagonal
    fov_deg  = degrees(2 * atan(w / (2 * focal_px)))

and it is imported from `marking.pipeline.provenance` rather than copied,
because a copy is a second thing to be wrong about the same question.
That module lives under `isolation/src`; importing it here does not put
it on the delivery path - `aws/handler.py` still imports only
`marking.situation` - it means this script reads EXIF the same way the
measurement pipeline does.

Standing rule 14: the 35 mm equivalent in the file is compared against
`evidence/field-2026-09-20/MANIFEST.csv` on every frame, and a frame
whose EXIF has no focal length is recorded as an error rather than given
a default. That is the check that caught five photographs shipping with
their EXIF stripped by the plate redaction.

**It also checks that the answer is the same twice.** `route_refusal.py`
states as a design property that `assess()` is pure - "same bytes in,
same verdict out" - and the reproducibility argument rests on it. Running
this script twice over the same 42 files produced two different answers
on F18, 4 surfacings against 5. `--stability N` measures that instead of
asserting it either way: E43, and `totals.surface_types_stability` names
every photograph that gave more than one answer.

    /opt/anaconda3/bin/python3 scripts/assess_field.py \
        --out results/assess_2026-09-22.json --stability 5
    /opt/anaconda3/bin/python3 scripts/assess_field.py --photo F14 F09
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
import traceback
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "isolation" / "src"))

INDEX = ROOT / "results" / "field_index_2026-09-20.csv"
EVID = ROOT / "evidence" / "field-2026-09-20"
MANIFEST = EVID / "MANIFEST.csv"

# 116 縣道 (樹林中正路). docs/timeline-116.md: the posted limit was 50 when
# these markings were laid, and §171's taper length goes as V squared, so
# this is an input to the verdict and not a label. A works limit of 30 is
# painted on the carriageway at part of the site; that is a different
# number and `--posted-kmh 30` is how you ask for it. Whatever is used is
# written into the output.
POSTED_KMH = 50.0


def field_of_view(image, path):
    """Horizontal field of view from this file's own EXIF. No default."""
    from marking.pipeline import provenance

    prov = provenance(image, path=str(path))

    if prov.focal_px is None:
        return None, prov

    fov = math.degrees(2 * math.atan(image.shape[1] / (2 * prov.focal_px)))

    return fov, prov


def assess_one(job: dict) -> dict:
    """One photograph, in its own process. Pure: same bytes, same verdict."""
    import cv2

    from marking.situation import assess

    no, path = job["no"], Path(job["path"])
    row = {"no": no, "file": path.name,
           "captured": job.get("captured"),
           "manifest_f35_mm": job.get("manifest_f35_mm"),
           "manifest_sha256": job.get("manifest_sha256"),
           "redacted": job.get("redacted") or None}

    image = cv2.imread(str(path))

    if image is None:
        row["error"] = f"unreadable: {path}"
        return row

    row["size"] = f"{image.shape[1]}x{image.shape[0]}"

    fov, prov = field_of_view(image, path)
    row["exif_f35_mm"] = prov.f35_mm
    row["focal_px"] = None if prov.focal_px is None else round(prov.focal_px, 1)
    row["fov_deg"] = None if fov is None else round(fov, 3)
    row["provenance_notes"] = prov.notes
    row["sha256"] = prov.sha256

    # Rule 14: the manifest is an assertion about the file; the file is
    # the evidence. Disagreement is reported, never reconciled silently.
    want = job.get("manifest_f35_mm")
    if prov.f35_mm is None:
        row["error"] = ("no FocalLengthIn35mmFilm in this file's EXIF; the "
                        f"manifest asserts {want}. Not assessed: a field of "
                        "view was not supplied and will not be invented")
        return row
    if want is not None and abs(float(want) - prov.f35_mm) > 1e-6:
        row["f35_disagrees_with_manifest"] = True

    row["posted_kmh"] = job["posted_kmh"]
    row["lane_width_m"] = job["lane_width_m"]

    started = time.time()
    try:
        out = assess(image, fov_deg=fov, posted_kmh=job["posted_kmh"],
                     lane_width_m=job["lane_width_m"])
    except Exception:
        row["error"] = traceback.format_exc(limit=6)
        row["wall_s"] = round(time.time() - started, 1)
        return row
    row["wall_s"] = round(time.time() - started, 1)

    # `assess()` returns `roi_frac` only on the branch that refuses, so on
    # every frame that passed the gate the number the gate turns on is
    # absent from its own output - E34. G01's acceptance criteria are
    # written in terms of that number over all 42, so it is recomputed
    # here and named for what it is.
    roi = None
    if out.get("roi_frac") is None:
        from marking.extract import road_region

        roi = road_region(image)
        row["roi_frac_recomputed"] = (0.0 if roi is None
                                      else round(float((roi > 0).mean()), 4))

    # Is the same verdict returned for the same bytes? `route_refusal.py`
    # states as a design property that it is - "assess() pure, offline,
    # same bytes in, same verdict out" - and the whole reproducibility
    # argument rests on that sentence. Two full runs of this script over
    # the 42 disagreed on F18, 4 surfacings against 5, so the sentence is
    # not true. `_surface_types` seeds its own sampling with
    # `default_rng(0)` but leaves `cv2.kmeans(..., KMEANS_PP_CENTERS)` on
    # OpenCV's unseeded RNG, and on a frame near its own threshold the
    # answer moves. E43. This measures it instead of asserting either way.
    if job.get("stability") and roi is not None:
        from marking.situation import _surface_types

        repeats = [_surface_types(image, roi) for _ in range(job["stability"])]
        row["surface_types_repeats"] = repeats
        row["surface_types_stable"] = len(set(map(str, repeats))) == 1

    # Everything assess() returns, findings with their measured values and
    # both narration lists. Nothing is summarised away here: a driver that
    # keeps only the codes cannot be used to check a sentence.
    row.update({
        "state": out.get("state", "ASSESSED"),
        "summary": out.get("summary"),
        "roi_frac": out.get("roi_frac"),
        "carriageway_found": bool(out.get("carriageway_found")),
        "segments": out.get("segments"),
        "taper": out.get("taper"),
        "checked": out.get("checked", []),
        "not_checked": out.get("not_checked", []),
        "findings": out.get("findings", []),
        "codes": [f["code"] for f in out.get("findings", [])],
        "scenario": out.get("scenario", []),
        "site_description_not_measured":
            out.get("site_description_not_measured", []),
    })
    return row


def _seconds(stamp: str | None):
    """`2026:09:20 15:56:03` -> seconds past midnight. EXIF's own format."""
    if not stamp:
        return None
    try:
        hh, mm, ss = stamp.split(" ")[1].split(":")
    except (IndexError, ValueError):
        return None
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def totals(rows: list[dict]) -> dict:
    """Only counts that can be recomputed from `photographs` below."""
    ok = [r for r in rows if "error" not in r]
    errors = [r for r in rows if "error" in r]

    by_code = Counter(c for r in ok for c in r["codes"])
    sets = Counter(tuple(sorted(set(r["codes"]))) for r in ok)
    fovs = sorted({r["fov_deg"] for r in ok if r.get("fov_deg") is not None})
    fracs = sorted(r["roi_frac"] if r["roi_frac"] is not None
                   else r.get("roi_frac_recomputed") for r in ok)
    stamps = sorted((_seconds(r.get("captured")), r.get("captured"))
                    for r in rows if _seconds(r.get("captured")) is not None)

    return {
        "n": len(rows),
        "assessed": len(ok),
        "errors": len(errors),
        "photographs_with_at_least_one_finding":
            sum(1 for r in ok if r["codes"]),
        "photographs_with_no_finding": sum(1 for r in ok if not r["codes"]),
        "findings_total": sum(len(r["codes"]) for r in ok),
        "findings_by_code": dict(sorted(by_code.items())),
        "taper_states": dict(sorted(Counter(
            (r.get("taper") or {}).get("state") for r in ok).items())),
        "states": dict(sorted(Counter(r["state"] for r in ok).items())),
        "carriageway_found_true": sum(1 for r in ok if r["carriageway_found"]),
        "scenario_lines_total": sum(len(r["scenario"]) for r in ok),
        "unmeasured_lines_total":
            sum(len(r["site_description_not_measured"]) for r in ok),
        "photographs_with_unmeasured_lines":
            sum(1 for r in ok if r["site_description_not_measured"]),
        "fov_deg": {"distinct": fovs,
                    "min": fovs[0] if fovs else None,
                    "max": fovs[-1] if fovs else None},
        # The walk, in the order it happened. docs/field-index-2026-09-20.md
        # has quoted "15:56:03-16:01:07" since the day of the survey and no
        # script produced it, so it could not be registered. It can now.
        "captured": {
            "first": stamps[0][1] if stamps else None,
            "last": stamps[-1][1] if stamps else None,
            "span_s": (stamps[-1][0] - stamps[0][0]) if stamps else None,
            "distinct_timestamps": len({s for _, s in stamps}),
            "source": "evidence/field-2026-09-20/MANIFEST.csv, column "
                      "`captured`, which tests/test_evidence_integrity.py "
                      "checks against each file's own EXIF",
        },
        "surface_types_stability": {
            "measured": any("surface_types_repeats" in r for r in ok),
            "repeats_each": max((len(r.get("surface_types_repeats") or [])
                                 for r in ok), default=0),
            "unstable": sorted(r["no"] for r in ok
                               if r.get("surface_types_stable") is False),
            "note": "E43. `assess()` is documented as pure - same bytes in, "
                    "same verdict out. Any name listed here returned more "
                    "than one answer for the same file in one run",
        },
        "roi_frac": {"min": fracs[0] if fracs else None,
                     "max": fracs[-1] if fracs else None,
                     "note": "assess() reports this only when it refuses; "
                             "on an assessed frame it is recomputed here "
                             "from extract.road_region - E34"},
        "f35_mm_from_exif": dict(sorted(Counter(
            r.get("exif_f35_mm") for r in ok).items(),
            key=lambda kv: (kv[0] is None, kv[0]))),
        "f35_disagrees_with_manifest":
            [r["no"] for r in rows if r.get("f35_disagrees_with_manifest")],
        # The join the scenario document needs: how many distinct sets of
        # findings a road user actually meets, and which photographs each
        # one came from. Four, three or six is read off here, not decided.
        "distinct_finding_sets": [
            {"codes": list(codes), "photographs": n,
             "nos": [r["no"] for r in ok
                     if tuple(sorted(set(r["codes"]))) == codes]}
            for codes, n in sorted(sets.items(),
                                   key=lambda kv: (-kv[1], kv[0]))],
        "distinct_finding_sets_n": len(sets),
    }


def tree_state() -> dict:
    """Which code this actually ran, commit *and* working tree.

    Recording only the commit is not enough when more than one agent is
    in the repository: on 2026-09-22 this script's first full run started
    at 04:18 with `src/` clean and `src/marking/situation.py` was edited
    at 04:25, while it was still going. The workers had already imported
    the module, so the run was of the commit - but nothing in the output
    said so, and a reader comparing the artifact against the files on
    disk would have found a difference with no way to date it.
    """
    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(ROOT), *args],
                                  capture_output=True, text=True,
                                  check=True).stdout.strip()
        except Exception:
            return None

    # `git diff --name-only HEAD` and not `status --porcelain`: the
    # porcelain line's path starts at a column that depends on the status
    # code, and slicing it fixed-width wrote `esults/figure_registry.json`
    # into the first artifact this function produced. A corrupted path in
    # the field that records what was run is worse than no field.
    changed = git("diff", "--name-only", "HEAD")
    tracked = [] if not changed else changed.splitlines()

    # The commit is not enough on its own. Three agents worked in this
    # repository on 2026-09-22 and HEAD moved twice during one run of
    # this script, so "which commit" and "which code ran" came apart. The
    # modules are hashed instead: that is pinned to the bytes Python
    # imported and cannot be raced by anybody else's commit.
    import hashlib

    modules = {
        path.relative_to(ROOT).as_posix():
            hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        for path in sorted((ROOT / "src" / "marking").glob("*.py"))
    }

    return {
        "commit": git("rev-parse", "HEAD") or "unknown",
        "modified_tracked_files_at_start": sorted(tracked),
        "src_clean_at_start": not any(f.startswith("src/") for f in tracked),
        "src_module_sha256_16": modules,
        "note": "captured before the first photograph is read. When "
                "`src_clean_at_start` is false the run measured the working "
                "tree and not the commit, and `src_module_sha256_16` is "
                "then the only unambiguous record of what ran",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path,
                    help="write the run here. Without it nothing is written")
    ap.add_argument("--photo", nargs="+", metavar="F##",
                    help="only these F-numbers; default all 42")
    ap.add_argument("--posted-kmh", type=float, default=POSTED_KMH,
                    help=f"speed the taper is judged against (default "
                         f"{POSTED_KMH:g}; see this file's POSTED_KMH note)")
    ap.add_argument("--lane-width-m", type=float, default=None,
                    help="the one number that cannot come from a photograph. "
                         "Omit it and LANE_TOO_NARROW is not checked")
    ap.add_argument("--stability", type=int, default=0, metavar="N",
                    help="also call `_surface_types` N extra times per "
                         "photograph and record every answer, so the "
                         "purity claim is measured and not asserted (E43)")
    ap.add_argument("--workers", type=int, default=4,
                    help="processes; assess() is pure so this changes "
                         "nothing but the wall clock")
    a = ap.parse_args()

    index = {r["no"]: r for r in csv.DictReader(INDEX.open())}
    manifest = {r["no"]: r for r in csv.DictReader(MANIFEST.open())}

    missing = sorted(set(index) ^ set(manifest))
    if missing:
        print(f"the index and the manifest disagree on {missing}",
              file=sys.stderr)
        return 2

    nos = sorted(index)
    if a.photo:
        unknown = [p for p in a.photo if p not in index]
        if unknown:
            print(f"no such photograph: {unknown}", file=sys.stderr)
            return 2
        nos = list(a.photo)

    jobs = [{"no": no, "path": str(EVID / index[no]["file"]),
             "captured": manifest[no]["captured"],
             "manifest_f35_mm": float(manifest[no]["f35_mm"])
                                if manifest[no]["f35_mm"] else None,
             "manifest_sha256": manifest[no]["sha256"],
             "redacted": manifest[no].get("redacted"),
             "posted_kmh": a.posted_kmh, "lane_width_m": a.lane_width_m,
             "stability": a.stability}
            for no in nos]

    tree = tree_state()

    started = time.time()
    if a.workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            rows = list(pool.map(assess_one, jobs))
    else:
        rows = [assess_one(j) for j in jobs]
    rows.sort(key=lambda r: r["no"])

    # Seconds from the first frame of the walk, so the scenarios can be
    # put in the order a road user meets them without re-parsing EXIF
    # timestamps downstream.
    clock = [_seconds(r.get("captured")) for r in rows]
    origin = min((c for c in clock if c is not None), default=None)
    for r, c in zip(rows, clock):
        r["seconds_from_first"] = None if (c is None or origin is None) \
            else c - origin

    t = totals(rows)
    document = {
        "note": "assess() over the field set, at native resolution, field "
                "of view from each file's EXIF. The first recorded "
                "full-population run of this function - E24. Every count "
                "in `totals` is recomputable from `photographs`.",
        "commit": tree["commit"],
        "tree_state": tree,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "regenerate": (f"/opt/anaconda3/bin/python3 scripts/assess_field.py "
                       f"--out results/assess_2026-09-22.json "
                       f"--posted-kmh {a.posted_kmh:g} "
                       f"--stability {a.stability}"),
        "posted_kmh": a.posted_kmh,
        "lane_width_m": a.lane_width_m,
        "wall_s": round(time.time() - started, 1),
        "totals": t,
        "photographs": rows,
    }

    print(f"{t['n']} photographs, {t['assessed']} assessed, "
          f"{t['errors']} errors: {t['findings_total']} findings over "
          f"{t['photographs_with_at_least_one_finding']} of them in "
          f"{t['distinct_finding_sets_n']} distinct sets; "
          f"taper {t['taper_states']}; posted {a.posted_kmh:g} km/h")
    for r in rows:
        if "error" in r:
            print(f"  {r['no']}  ERROR  "
                  f"{r['error'].strip().splitlines()[-1][:90]}")
            continue
        frac = r["roi_frac"] if r["roi_frac"] is not None \
            else r.get("roi_frac_recomputed")
        print(f"  {r['no']}  fov {r['fov_deg']:>5.2f}  roi "
              f"{frac:.3f}  {len(r['codes'])} findings  "
              f"{','.join(r['codes']) or '-':<62}  "
              f"scenario {len(r['scenario'])}  "
              f"unmeasured {len(r['site_description_not_measured'])}")
    print(f"  finding counts: {t['findings_by_code']}")
    st = t["surface_types_stability"]
    if st["measured"]:
        print(f"  surface_types over {st['repeats_each']} repeats: "
              f"{len(st['unstable'])} of {t['assessed']} photographs gave "
              f"more than one answer for the same bytes"
              + (f" - {','.join(st['unstable'])}" if st["unstable"] else ""))
    for s in t["distinct_finding_sets"]:
        print(f"  {s['photographs']:>2}x  {','.join(s['codes']) or '(none)'}")

    if a.out:
        a.out.write_text(json.dumps(document, indent=1, ensure_ascii=False)
                         + "\n")
        print(f"  -> {a.out}")
    else:
        print("  (no --out given, nothing written)")

    return 1 if t["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
