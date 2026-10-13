"""Every clause this program quotes must exist in its own evidence.

Three fabrications in one day made this mechanical rather than a rule:

  E25  README cited 「§155 漸變段」. The only 155 in the code is the
       divisor of L = W·V²/155. A constant written as a clause number.
  E36  `_works_hoarding` cited 「新北市道路挖掘作業審查原則：佔用車道施工
       應維持必要車道數與寬度，並設置漸變段導引車流」. Checked against
       docs/source-ntpc-excavation-6.0.txt: 必要車道數 0 hits, 漸變段 0,
       導引車流 0, 佔用車道 0. Fabricated clause CONTENT, under a
       government document's name, in the delivery function.
  and  the §165 basis, written by the same agent an hour after recording
       E25, while fixing a bug about misattributing clauses. This
       project holds no text of §165 at all.

So: a substantive fragment of a `basis` string must appear in `docs/`,
or be marked as this program's own words. Nothing in between.
"""
import ast
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

MIN_FRAGMENT = 6

# A fragment inside one of these is the program speaking, not a quotation.
OWN_VOICE = ("本程式", "未查證", "未經查證", "本專案未持有")


def _normalise(text):
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("臺", "台")
    return "".join(c for c in text
                   if not unicodedata.category(c).startswith("P"))


def _corpus():
    out = []
    for path in sorted((ROOT / "docs").iterdir()):
        if path.suffix in (".md", ".txt"):
            out.append(path.read_text(errors="ignore"))
    # Han-only, to match `_windows`. They disagreed for one round: the
    # windows dropped the digit in 「以 3 米直規量取」 and the corpus kept
    # it, so a correctly sourced quote came back unsourced.
    return "".join(c for c in _normalise("\n".join(out))
                   if "\u4e00" <= c <= "\u9fff")


def _bases():
    tree = ast.parse((ROOT / "src" / "marking" / "situation.py").read_text())
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", "") == "Finding"
                and len(node.args) >= 4):
            try:
                found.append(ast.literal_eval(node.args[3]))
            except Exception:
                pass
    return found


# Two designs failed before this one, and both failures are the reason
# it is written the way it is.
#
#   whole sentences  cried wolf. The documents phrase and punctuate the
#     same clause differently, so five of seven bases failed on quotes
#     that ARE sourced. A check that fires on correct code gets switched
#     off, and is then worth less than nothing.
#   Han runs of 4+  matched nothing useful, because normalising strips
#     the punctuation and the whole basis becomes one run.
#
# So: strip punctuation from BOTH sides and slide a window. A real quote
# matches however it was punctuated; a fabricated one has nowhere to
# match. 必要車道數與寬度, 導引車流 and 分向限制線 all fail, which is
# what this exists for.
WINDOW = 6


def _windows(text):
    t = "".join(c for c in _normalise(text) if "\u4e00" <= c <= "\u9fff")
    return {t[k:k + WINDOW] for k in range(len(t) - WINDOW + 1)}


SPLIT = r"[:;.,\uff1a\uff1b\u3002\uff0c\u3001\uff08\uff09()]"


def _unsourced(basis, corpus):
    """Windows PER CLAUSE, never across the whole string.

    A basis is a label and then a quotation - 「設置規則 §169：以劃設於…」
    - and a window straddling that boundary cannot be in the corpus,
    because the boundary is this program's punctuation. The third
    version of this function failed the real-quote test for exactly
    that reason.
    """
    # A marker governs everything AFTER it, not just the clause it sits
    # in. 「本程式解讀:…」 is followed by a colon, and splitting on colons
    # separated the marker from the sentence it disclaims - so the fourth
    # version of this function still flagged text that was correctly
    # marked.
    missing, speaking = [], False
    for part in re.split(SPLIT, basis):
        if any(m in part for m in OWN_VOICE):
            speaking = True
        if speaking:
            continue
        for w in sorted(_windows(part)):
            if w not in corpus:
                missing.append(w)
    return missing

def test_the_findings_quote_clauses_this_project_holds():
    corpus, offenders = _corpus(), {}
    bases = _bases()
    assert len(bases) >= 6, f"only {len(bases)} basis strings found"
    for basis in bases:
        bad = _unsourced(basis, corpus)
        if bad:
            offenders[basis[:40]] = bad
    assert not offenders, (
        "a finding quotes text that is nowhere in docs/. Either add the "
        "source, or mark the sentence as this program's own words:\n" +
        "\n".join(f"  {k}…\n     {b}" for k, b in offenders.items()))


def test_the_check_would_catch_a_fabricated_quote():
    """The guard must fail on the actual sentence that was in the code."""
    corpus = _corpus()
    fabricated = ("新北市道路挖掘作業審查原則：佔用車道施工應維持必要"
                  "車道數與寬度，並設置漸變段導引車流")
    assert _unsourced(fabricated, corpus), (
        "the check passes the sentence it exists to catch")


def test_the_check_accepts_a_real_quote():
    corpus = _corpus()
    real = "設置規則 §169：以劃設於道路緣石正面或頂面為原則"
    assert not _unsourced(real, corpus), _unsourced(real, corpus)
