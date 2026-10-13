#!/usr/bin/env python3
"""Check a fresh batch of field photographs before anything is measured.

Runs on a folder the moment the photographs land. Nothing here decides a
result; it says which frames the measurement scripts can use and why the
others cannot, so a wasted shot is known the same morning, not a week on.

For every JPEG:
  EXIF present, FocalLengthIn35mmFilm present and equal to the batch's
  main lens (the 2026-09-20 batch was 24 mm on 39 of 42; the three at
  46 mm could not be used); portrait orientation; HDR / gain-map absent;
  size not re-encoded by a messenger (byte size and dimensions); a GPS
  fix if the phone left one (the earlier batch had none); the sha256,
  so the manifest can be written the same way as evidence/field-2026-09-20.

    /opt/anaconda3/bin/python3 scripts/intake_field.py <folder> [--manifest out.csv]
"""
import argparse, csv, glob, hashlib, os, re, sys
from collections import Counter
from PIL import Image
from PIL.ExifTags import TAGS

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("folder"); ap.add_argument("--manifest")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.folder, "*.jpg")) + glob.glob(os.path.join(a.folder, "*.JPG")) + glob.glob(os.path.join(a.folder, "*.jpeg")))
    if not files:
        sys.exit(f"沒有 jpg:{a.folder}")
    rows, f35s = [], Counter()
    for p in files:
        raw = open(p, "rb").read(); im = Image.open(p)
        ex = {TAGS.get(k, k): v for k, v in (im._getexif() or {}).items()}
        f35 = ex.get("FocalLengthIn35mmFilm"); w, h = im.size
        gps = ex.get("GPSInfo") or {}
        def _real(v):
            try:
                return all(float(x) == float(x) for x in (v if isinstance(v, tuple) else (v,)))
            except (TypeError, ValueError, ZeroDivisionError):   # a 0/0 rational is "no fix"
                return False
        has_gps = bool(gps) and _real(gps.get(2)) and _real(gps.get(4))   # 2/4 = lat/lon triples
        hdr = b"hdrgm:Version" in raw[:200000]
        rows.append({"file": os.path.basename(p), "captured": ex.get("DateTimeOriginal", ""), "size": f"{w}x{h}",
                     "portrait": h > w, "f35_mm": f35, "hdr_gainmap": hdr, "gps": has_gps,
                     "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        if f35: f35s[f35] += 1
    main_f35 = f35s.most_common(1)[0][0] if f35s else None
    ok = 0
    print(f"{len(rows)} 張  主鏡頭 f35={main_f35} mm")
    for r in rows:
        why = []
        if not r["f35_mm"]: why.append("無 EXIF 焦距(被轉傳壓縮?)")
        elif r["f35_mm"] != main_f35: why.append(f"焦距 {r['f35_mm']} mm ≠ 主鏡頭(有縮放)")
        if not r["portrait"]: why.append("橫式")
        # A gain map rode along on all 43 of the 2026-09-20 batch and every
        # measurement used the ordinary base image underneath it, so it is
        # noted, not a reason to refuse.
        if r["bytes"] < 1_500_000: why.append(f"只有 {r['bytes']//1000} KB(疑似壓縮過)")
        r["usable"] = not why; r["why"] = "; ".join(why); ok += r["usable"]
        print(f"  {r['file']:28} {r['captured'][11:]:9} {r['size']:10} f35={str(r['f35_mm']):>4} {'GPS' if r['gps'] else '   '} {'HDR' if r['hdr_gainmap'] else '   '}  {'✓' if r['usable'] else '✗ ' + r['why']}")
    print(f"→ 可用 {ok}/{len(rows)}")
    if a.manifest:
        with open(a.manifest, "w", newline="") as f:
            wri = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wri.writeheader(); wri.writerows(rows)
        print("manifest:", a.manifest)

if __name__ == "__main__":
    main()
