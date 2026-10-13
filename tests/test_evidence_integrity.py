"""The published photographs must still support what is said about them.

Standing rule 14. The plate redaction on 2026-09-21 wrote five of the 42
without carrying the EXIF over, so they shipped with no focal length
while `MANIFEST.csv` still recorded one. Nothing reported was wrong and
nothing was checking.

Slow by design - it reads 210 MB - and worth it: this is primary
evidence that cannot be re-obtained, and the failure it catches is
silent everywhere else.
"""
import csv
import hashlib
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "evidence" / "field-2026-09-20"
sys.path.insert(0, str(ROOT / "src"))

pytestmark = pytest.mark.skipif(not (EV / "MANIFEST.csv").exists(),
                                reason="evidence not present")
ROWS = list(csv.DictReader(open(EV / "MANIFEST.csv"))) if (EV / "MANIFEST.csv").exists() else []
F35_TAG = 41989          # FocalLengthIn35mmFilm, in the Exif IFD


def test_the_manifest_covers_every_photograph():
    on_disk = {p.name for p in EV.glob("*.jpg")}
    assert on_disk == {r["file"] for r in ROWS}
    assert len(ROWS) == 42


@pytest.mark.parametrize("row", ROWS, ids=[r["no"] for r in ROWS])
def test_the_focal_length_is_in_the_file_and_agrees_with_the_manifest(row):
    """The one camera parameter every measurement here needs.

    Read from the file, not from the manifest, because the manifest is
    what was being believed when five files stopped carrying it.
    """
    got = Image.open(EV / row["file"]).getexif().get_ifd(0x8769).get(F35_TAG)
    assert got is not None, (
        f"{row['no']} has no 35mm-equivalent focal length. The manifest says "
        f"{row['f35_mm']}, and nothing in the file supports that. If this "
        "file was edited, the edit dropped its EXIF.")
    assert int(got) == int(row["f35_mm"])


@pytest.mark.parametrize("row", ROWS, ids=[r["no"] for r in ROWS])
def test_the_bytes_are_the_bytes_the_manifest_names(row):
    b = (EV / row["file"]).read_bytes()
    assert hashlib.sha256(b).hexdigest() == row["sha256"]
    assert len(b) == int(row["bytes"])


def test_no_photograph_carries_a_real_gps_fix():
    """Degenerate 0/0 is what the camera wrote; a real one would be new."""
    bad = []
    for r in ROWS:
        g = Image.open(EV / r["file"]).getexif().get_ifd(0x8825)
        lat, lon = g.get(2), g.get(4)
        if lat and lon and not all(str(v) == "nan" for v in (*lat, *lon)):
            bad.append(r["no"])
    assert not bad, f"a real GPS fix appeared in {bad}"
