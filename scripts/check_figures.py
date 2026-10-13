"""Fail when a published figure no longer equals the file that produced it.

Prose did not work. On 2026-09-17 the claim rule was written into AGENTS.md;
on 2026-09-18 the same session quoted a figure from a heredoc that was never
saved, corrected a document and left the sentences that depended on the old
number, and added the sentence "source for every figure here is
results/..." to a paragraph where three of six figures were not. The
mechanical check that did work, all day, was scripts/check_stage.sh.

So this is the mechanical equivalent, deliberately narrow. Three rules, all pure parse-and-compare:

    every entry in results/figure_registry.json must equal the value at its
    JSON pointer in the results file it names;

    every assertion in its optional `expect` block must hold at the same
    time;

    and no entry may cite a source file that carries a `withdrawn` marker.

The third rule was added on 2026-09-21, when two of nine entries were found
citing `results/taper_rate.json` after that file had been withdrawn. The
values still matched, so the check passed: it compared the number to its
source without asking whether the source still stood. Withdrawing a
measurement and leaving the figures that quote it is the same failure this
file exists to prevent, one level up.

The second rule exists because the first one has a hole that this project
has already fallen into by hand. Three registry entries point into
`splits/3`, a positional index into an array. Reorder that array and the
pointer still resolves, still has the right type, still holds a plausible
number - and the citation has quietly moved from testB to testA.
`hard_threshold_wrong_pct` is 9.0 in both testB rows, so comparing values
cannot tell them apart either. `expect` pins the neighbours: the split's own
`label`, its decision count, the garment count at the root. A mis-aimed
pointer then fails loudly instead of passing.

That is pure parse-and-compare. It has no heuristics and cannot produce a
false positive, which matters more than coverage: a check that cries wolf
gets bypassed with --no-verify, and the bypass takes the licensing check
down with it.

What it deliberately does not do: scan prose for loose numbers, guess which
number is a measurement, or police version numbers, years, code constants,
pixel sizes or percentages of frame height. Those belong to a person.

    python3 scripts/check_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "results" / "figure_registry.json"


def resolve(document, pointer: str):
    """RFC 6901, the subset used here."""
    node = document

    for token in pointer.lstrip("#/").split("/"):
        if token == "":
            continue

        token = token.replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]

    return node


def expectation(document, pointer: str, key: str):
    """`$root/x` is absolute; `$parent/x` is relative to the pointer's owner."""
    if key.startswith("$root/"):
        return resolve(document, key[len("$root/"):])

    if key.startswith("$parent/"):
        parent = pointer.rsplit("/", 1)[0]

        return resolve(document, f"{parent}/{key[len('$parent/'):]}")

    raise ValueError(f"an expectation must start with $root/ or $parent/, "
                     f"not {key!r}")


def main() -> int:
    if not REGISTRY.exists():
        print(f"{REGISTRY} is missing")
        return 1

    entries = json.load(REGISTRY.open())["figures"]
    cache, failures = {}, []

    for entry in entries:
        path, _, pointer = entry["source"].partition("#")
        target = ROOT / path

        if not target.exists():
            failures.append(f"{entry['id']}: {path} does not exist")
            continue

        if path not in cache:
            cache[path] = json.load(target.open())

        source = cache[path]

        if isinstance(source, dict) and "withdrawn" in source:
            failures.append(
                f"{entry['id']}: {path} is withdrawn, and this figure still "
                f"quotes it.\n      {str(source['withdrawn'])[:160]}\n"
                f"      Remove the entry and every citation of it, or "
                f"un-withdraw the source.")
            continue

        try:
            found = resolve(cache[path], pointer)
        except (KeyError, IndexError, ValueError) as error:
            failures.append(f"{entry['id']}: {pointer} does not resolve in "
                            f"{path} ({error})")
            continue

        if found != entry["value"]:
            failures.append(
                f"{entry['id']}: registry says {entry['value']}, "
                f"{path}{pointer} says {found}")
            continue

        for key, want in entry.get("expect", {}).items():
            try:
                got = expectation(cache[path], pointer, key)
            except (KeyError, IndexError, ValueError) as error:
                failures.append(f"{entry['id']}: expectation {key} does not "
                                f"resolve ({error})")
                continue

            if got != want:
                failures.append(
                    f"{entry['id']}: expects {key} to be {want!r}, "
                    f"{path} has {got!r} - the pointer is aimed at the wrong "
                    f"place, or the source moved under it")

    for line in failures:
        print(f"  {line}")

    if failures:
        print(f"\n{len(failures)} of {len(entries)} published figures no "
              f"longer stand.\nEither the measurement changed and the "
              f"registry and every citation must follow, or the\nregistry "
              f"is wrong, or the source has been withdrawn and what quotes "
              f"it must go too.\nDo not silence this by editing the "
              f"registry to match.")
        return 1

    archival = [e["id"] for e in entries if e.get("archival_only")]
    print(f"{len(entries)} published figures match their sources")

    if archival:
        print(f"  {len(archival)} are archive-only - their source has no "
              f"producing script and cannot be re-derived:")

        for one in archival:
            print(f"    {one}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
