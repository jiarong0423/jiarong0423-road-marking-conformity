#!/usr/bin/env python3
"""Second plate-redaction pass, 2026-10-13.

The 2026-09-21 pass covered five plates. A frame-by-frame review on
2026-10-13 found legible or near-legible plates on more vehicles in the
09-20 set and on two 09-23 wide shots (P62, P63). Each box below was
checked by eye on a crop before it was applied; the ones marked
`precaution` cover plates that were already illegible.

Same method as the first pass: solid fill (28, 28, 28) with a red outline,
no blur, because a blur can be partially inverted. The file is re-encoded
with the original quantisation tables and chroma subsampling
and the original EXIF segment, so the 35 mm focal length that every
measurement needs is carried over. The XMP block and the HDR gain map
are not: the gain map is a second image of the same scene and would keep
the plate. The pre-redaction files stay in the
git-ignored `data/` tree.

    python3 -B scripts/redact_plates.py            # dry run
    python3 -B scripts/redact_plates.py --apply
"""
import csv, hashlib, json, shutil, sys
from pathlib import Path
from PIL import Image, ImageDraw, JpegImagePlugin

ROOT = Path(__file__).resolve().parents[1]
D20, D23 = "evidence/field-2026-09-20/IMG_20260920_", "evidence/field-2026-09-23/IMG_20260923_"
BOXES = [
    (D20 + "155603", [1914, 1542, 61, 26]), (D20 + "155606", [2234, 1509, 94, 48]),
    (D20 + "155609", [1971, 1418, 28, 17]),
    (D20 + "155801", [1773, 1502, 47, 17]), (D20 + "155801", [1868, 1433, 48, 15]),
    (D20 + "155801", [1884, 1456, 26, 13]),
    (D20 + "155802", [1842, 1809, 37, 16]), (D20 + "155802", [1991, 1761, 33, 12]),
    (D20 + "155802", [1999, 1777, 24, 13], "precaution"),
    (D20 + "155803", [2367, 1696, 34, 14]),
    (D20 + "155845", [2607, 1484, 20, 14], "precaution"), (D20 + "155845", [2326, 1564, 44, 20], "precaution"),
    (D20 + "155847", [1742, 1317, 37, 21]),
    (D20 + "155927", [1766, 1464, 59, 37]),
    (D20 + "155928", [1913, 1315, 28, 12]), (D20 + "155928", [1971, 1419, 34, 22]),
    (D20 + "155928", [1695, 1372, 37, 21]),
    (D20 + "155929", [2148, 1380, 35, 21]), (D20 + "155929", [2411, 1420, 31, 22]),
    (D20 + "155930", [1912, 1366, 25, 16], "precaution"),
    (D20 + "155931", [680, 1714, 62, 35]), (D20 + "155931", [1662, 1482, 41, 22]),
    (D20 + "155957", [1678, 1664, 37, 19]),
    (D20 + "160018", [2545, 989, 40, 17]), (D20 + "160018", [2127, 1113, 59, 32]),
    (D20 + "160046", [2777, 1343, 52, 26]),
    (D20 + "160107", [662, 1704, 42, 21]),
    (D23 + "063345", [2532, 1837, 63, 38]), (D23 + "063347", [2605, 1875, 59, 37]),
    # added the same day after a second, independent frame-by-frame review: a registration
    # number painted on a rear window (155801-155804), a partly legible plate on 155927,
    # one scooter seen in three frames (155958, 155959, 160000), and the remaining small
    # plates in frames that were being re-encoded anyway
    (D20 + "155801", [2192, 1356, 46, 20]), (D20 + "155801", [2204, 1382, 26, 16]),
    (D20 + "155802", [2249, 1712, 40, 16]), (D20 + "155802", [2258, 1732, 24, 14]),
    (D20 + "155803", [2764, 1610, 40, 15]), (D20 + "155803", [2773, 1628, 22, 14]),
    (D20 + "155804", [2080, 1565, 38, 15]), (D20 + "155804", [2089, 1582, 20, 12]),
    (D20 + "155927", [1960, 1235, 55, 26]), (D20 + "155931", [2105, 1332, 36, 20]),
    (D20 + "160000", [1368, 1688, 30, 14]), (D20 + "160000", [1880, 1706, 28, 16]),
    (D20 + "155958", [1968, 2000, 38, 24]), (D20 + "155959", [2148, 1718, 30, 20]),
    (D20 + "155606", [3022, 1367, 32, 14], "precaution"), (D20 + "155609", [2092, 1386, 22, 10], "precaution"),
    (D20 + "155801", [2088, 1381, 28, 13], "precaution"), (D20 + "155801", [2283, 1386, 18, 14], "precaution"),
    (D20 + "155801", [2300, 1365, 18, 12], "precaution"), (D20 + "155802", [2150, 1720, 22, 13], "precaution"),
    (D20 + "155803", [2656, 1604, 24, 12], "precaution"), (D20 + "155804", [1798, 1626, 26, 16], "precaution"),
    (D20 + "155804", [1900, 1600, 20, 13], "precaution"), (D20 + "155804", [1990, 1544, 20, 12], "precaution"),
    (D20 + "155804", [2146, 1569, 20, 12], "precaution"), (D20 + "155847", [2148, 1208, 16, 14], "precaution"),
    (D20 + "155928", [2160, 1150, 25, 12], "precaution"), (D20 + "155929", [2325, 1328, 50, 22], "precaution"),
    (D20 + "155930", [2128, 1405, 32, 20], "precaution"), (D20 + "155930", [2030, 1318, 50, 22], "precaution"),
    (D20 + "155930", [2160, 1213, 20, 10], "precaution"), (D20 + "155931", [2290, 1400, 28, 16], "precaution"),
    (D20 + "155931", [2235, 1243, 18, 10], "precaution"), (D20 + "155957", [1880, 1415, 28, 14], "precaution"),
    (D20 + "155958", [1838, 1852, 40, 16], "precaution"), (D20 + "155959", [1836, 1628, 32, 16], "precaution"),
    (D20 + "160107", [140, 1650, 60, 30], "precaution"),
    # third review, same day: a borderline plate on 155844, and vehicles masked in one
    # frame but not in the next, so the frames cannot be combined
    (D20 + "155844", [2285, 1425, 30, 12]), (D20 + "155844", [2650, 1437, 20, 10], "precaution"),
    (D20 + "155613", [2770, 1466, 35, 15], "precaution"),
    (D20 + "155802", [2322, 1745, 20, 10], "precaution"), (D20 + "155802", [2340, 1733, 12, 7], "precaution"),
    (D20 + "155802", [2352, 1722, 20, 10], "precaution"),
    (D20 + "155803", [2820, 1640, 15, 8], "precaution"), (D20 + "155803", [2843, 1630, 12, 7], "precaution"),
    (D20 + "155803", [2850, 1615, 20, 10], "precaution"),
    (D20 + "155929", [2538, 1185, 20, 8], "precaution"), (D20 + "155931", [2175, 1300, 40, 25], "precaution"),
]
# Small, illegible plates left unmasked on purpose (illegible at 16x with contrast): in the measurement frames F17 (155843),
# F30-F32 (160015-160017) and F40 (160105), and in frames with nothing else to mask
# (155731, 155732, 155735, 155736, 155825, 155826, 155828, 155830, 160101-160103). A re-encode
# would perturb the published measurements for no privacy gain.
FILL, EDGE = (28, 28, 28), (255, 0, 0)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def redact(src, boxes, dst):
    im = Image.open(src)
    exif, icc = im.info.get("exif"), im.info.get("icc_profile")
    if not exif:
        sys.exit(f"ERROR {src}: no EXIF to carry over")
    out = im.copy(); dr = ImageDraw.Draw(out)
    for x, y, w, h in boxes:
        dr.rectangle((x, y, x + w - 1, y + h - 1), fill=FILL, outline=EDGE, width=3)
    kw = dict(qtables=im.quantization, subsampling=JpegImagePlugin.get_sampling(im), exif=exif)
    if icc:
        kw["icc_profile"] = icc
    tmp = Path(str(dst) + ".tmp")
    out.save(tmp, "JPEG", **kw)
    a = Image.open(tmp)
    if a.getexif().get_ifd(0x8769).get(41989) != im.getexif().get_ifd(0x8769).get(41989):
        tmp.unlink()
        sys.exit(f"ERROR {dst}: focal length tag 41989 not carried over")
    tmp.replace(dst)


def main(apply):
    by_file = {}
    for item in BOXES:
        by_file.setdefault(item[0] + ".jpg", []).append(item)
    rec_path = ROOT / "results/plate_redactions.json"
    rec = json.loads(rec_path.read_text())
    second = {}
    for rel, items in by_file.items():
        src = ROOT / rel
        backup = ROOT / "data" / (Path(rel).parent.name + "-pre-2026-10-13") / src.name
        # every run rebuilds from the pre-pass bytes, so a file is re-encoded once however many runs
        known = rec.get("second_pass_2026-10-13", {}).get("files", {}).get(src.name, {}).get("sha256_before")
        if backup.exists():
            before = sha(backup)
            if known and known != before:
                sys.exit(f"ERROR backup of {rel} is not the file recorded as pre-redaction")
        else:
            before = sha(src)
        if apply:
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                shutil.copy2(src, backup)
                if sha(backup) != before:
                    sys.exit(f"ERROR backup of {rel} differs from the file it backs up")
            redact(backup, [i[1] for i in items], src)
        second[src.name] = {
            "boxes_xywh": [i[1] for i in items],
            "precaution": [i[1] for i in items if len(i) > 2],
            "sha256_before": before,
            "sha256_after": sha(src) if apply else None,
        }
        print(f"{rel}: {len(items)} box(es){' applied' if apply else ''}")
    if not apply:
        print("dry run; pass --apply to write")
        return 0
    old = rec.get("second_pass_2026-10-13", {})
    rec["second_pass_2026-10-13"] = {
        "note": ("Three frame-by-frame reviews found more legible plates than the first pass covered. "
                 f"{len(BOXES)} boxes on {len(by_file)} files, every box on a vehicle body. Same method: "
                 "solid fill with a red outline, no blur. Re-encoded with the original quantisation tables, "
                 "subsampling and EXIF. Results computed before this date read the pre-redaction bytes; "
                 "sha256_before records them. Produced by scripts/redact_plates.py."
                 " The re-encode does not carry over the XMP block or the HDR gain map appended after the main image; the first pass dropped them too. The gain map is a second, smaller image of the same scene and would have kept the plates."),
        "files": second,
    }
    if "assess_rerun" in old:
        rec["second_pass_2026-10-13"]["assess_rerun"] = old["assess_rerun"]
    rec_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    for man in ("evidence/field-2026-09-20/MANIFEST.csv", "evidence/field-2026-09-23/MANIFEST.csv"):
        p = ROOT / man
        rows = list(csv.DictReader(p.open(newline="", encoding="utf-8")))
        fields = list(rows[0].keys())
        for r in rows:
            if r["file"] in second:
                f = ROOT / Path(man).parent / r["file"]
                r["sha256"], r["bytes"] = sha(f), str(f.stat().st_size)
                if "redacted" in r:
                    r["redacted"] = "plate"
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n"); w.writeheader(); w.writerows(rows)
    print("manifests and results/plate_redactions.json updated")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv[1:]))
