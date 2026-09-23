# 116 縣道現場照，2026-09-20

42 photographs of 116 縣道 (樹林中正路), taken between 15:56 and 16:01 on
2026-09-20. They are the project's primary evidence and cannot be
re-obtained: the surface has been worked on again since.

## These are the originals, and that is not a luxury

3072x4096, 210 MB for the set (201 MiB), exactly as the camera wrote
them. The largest single file is 7.9 MB (7.5 MiB).

They were going to be published at 2000 px, on the argument that
`taper_ensemble` works at 1000, 1400 and 1800 px and resamples anything
larger before it looks at it, so nothing here has ever seen more than
1800 px. Checked on two photographs that held, and it was taken for the
set.

Over all 42 it does not hold. Seventeen give different findings from
their reduced copies and ten differ in the taper verdict, and not only by
losing things: F01, F03, F18, F20 and F21 gain TAPER_TOO_STEEP, asserting
from the reduced copy a taper their originals refuse to measure. Reducing
them produces a different article, and a repository whose argument is
reproducibility cannot ship one.

`MANIFEST.csv` carries, per photograph, its F-number, capture time,
pixel size, the EXIF 35 mm-equivalent focal length that sets the field of
view a measurement needs, its byte count and its SHA-256. Its columns are
exactly `no, file, captured, size, f35_mm, bytes, sha256`.

```sh
cd evidence/field-2026-09-20
python3 - <<'EOF'
import csv, hashlib
bad = 0
for r in csv.DictReader(open("MANIFEST.csv")):
    if hashlib.sha256(open(r["file"], "rb").read()).hexdigest() != r["sha256"]:
        print("differs:", r["file"]); bad += 1
print(f"{bad} of 42 differ")
EOF
```

An earlier version of this file carried a second snippet that read a
`published_sha256` column. That column existed when these were published
reduced and does not exist now that they are the originals, so anyone
following the instruction got a KeyError. One snippet, and it is the one
that runs.

## Five registration plates are masked

Five of the 42 carry a legible vehicle registration plate, and each is
covered by a solid dark rectangle with a red outline. Three vehicles:
F24 and F25 are the same car one second apart, and F34 and F35 carry
plates that motion blur had already made illegible - masked anyway,
because doing so costs nothing and being wrong costs a stranger.

Solid fill, not blur: a blur can be partially inverted.

**Every box lies on a vehicle body. No road-surface pixel was touched,
and no measurement reads from those regions** - checked by re-running
`assess()` on all five before and after, which returns the same findings.

`results/plate_redactions.json` gives each box, its frame and the
resulting SHA-256. `MANIFEST.csv` has a `redacted` column, and its
hashes are of the files as published.

**Where the pre-redaction originals are.** An earlier version of this
paragraph said they were held offline and were not in this repository.
That was wrong, and it was wrong about the five files that carry a
legible registration plate. They are on disk at
`data/field-2026-09-20/`, inside the working tree. All five differ from
the published copies by SHA-256, which is how they were found on
2026-09-22.

Nothing is leaking: `data/` is in `.gitignore`, `git ls-files data/`
returns nothing, and `scripts/check_stage.sh` refuses to stage anything
under it. But a sentence saying they are not here would let someone
archive this folder, or use a tool that does not read `.gitignore`, and
publish them. So it says where they are instead.

## What was looked at and deliberately left

A privacy review went through all 42 at full resolution before this
repository was made readable by anyone.

The line it was held to is Street View's, because these photographs are
of the same streets and are published for the same reason: the subject
is the road surface. Street View blurs faces and registration plates and
does not blur shop signage, and that is exactly the line drawn here,
arrived at independently and then recognised. What follows is what the
review found and what the owner decided.

**Five registration plates — masked.** Above.

**No identifiable faces.** The largest face in the set is about 8 px;
every rider is helmeted, visored or facing away. Checked at
magnification, not from thumbnails.

**Shop signage carrying business names and telephone numbers — left as
photographed.** About ten frames show frontages along the road: vehicle
repair shops, a stainless-steel fabricator, a CNC shop, a restaurant, a
dealership. The signs are in public view on a public road, they are part
of what the street looks like, and Street View publishes the same
frontages on the same road unblurred. The subject here is the pavement.
The owner's decision, recorded so that it is not re-opened by someone
assuming it was an oversight.

**EXIF — nothing to remove, and on five of them nothing was left.**

No GPS: every one of the 42 stores latitude, longitude, altitude, speed
and time as degenerate 0/0 rationals, one identical pattern across the
set. No serial number, no owner, no copyright field, no artist, no
software tag. The camera model and the capture time are there and both
are wanted.

That audit named what it looked for and did not name the **MakerNote**,
which 37 of the 42 carry. Checked 2026-09-21 rather than assumed: at
most 88 bytes each, and the only readable string in any of them is
`Xiaomi`, which is already the `Make` field. Nothing identifying.

**The redaction pass destroyed the EXIF on the five it touched.** They
shipped with zero tags. `MANIFEST.csv` still recorded their 35 mm
equivalent focal length, so the number was an assertion a reader could
no longer check against the file — and that number is the one camera
parameter every measurement here needs. Nothing reported was wrong, but
five photographs had stopped being able to support what was said about
them.

It surfaced by accident, and that is the part worth keeping: the new
pipeline was run over all 42 and returned no focal length on exactly
five. Nobody looked for this. A run over the whole set found it because
it was a run over the whole set.

Repaired by copying the original APP1 segment back in. That leaves the
compressed image data untouched, so the masked pixels are bit-identical
to the files the privacy review passed — asserted in code before the
hashes were rewritten, not inspected afterwards. The reinstated EXIF was
then audited on its own terms, with the result above. See
`results/plate_redactions.json`.

## The filenames are the camera's

`IMG_20260920_155603.jpg` is what the camera wrote. They are not renamed,
because the name carries the capture time and renaming primary evidence
weakens what it is evidence of. `MANIFEST.csv` carries the F-number that
`results/field_index_2026-09-20.csv` and the documents use.

38 of the 42 filenames agree with the EXIF capture time to the second.
Four - F04, F06, F34, F37 - are one second earlier than their EXIF, which
is the gap between the shutter and the file being written.
