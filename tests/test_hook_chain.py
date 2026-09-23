"""Standing rule 3, made mechanical.

    `scripts/check_stage.sh` must reach `scripts/check_figures.py`. If a
    workspace-level hook replaces it, the project's check is chained
    behind it, not dropped.

Prose did not stop it. On 2026-09-21 a workspace installer wrote a
three-line shim over `scripts/check_stage.sh` - through the symlink that
`.git/hooks/pre-commit` used to be - and the figure registry check, the
data/ and output/ staging refusal and the .mapskey credential check all
stopped running without a word. The commit immediately before was a
hardening of the check that had just become unreachable, which is how
long it can go unnoticed.

These are static assertions on purpose. A test that actually staged a
file and ran `git commit` would need a scratch clone and would still not
be checking the hook this working copy has installed, which is the thing
that failed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".git" / "hooks" / "pre-commit"
CHECK_STAGE = ROOT / "scripts" / "check_stage.sh"
GATE = Path(os.environ.get(
    "MARKING_SECURITY_GATE",
    str(Path.home() / "Developer/tools/pre_commit_security_gate.sh")))


def test_check_stage_calls_check_figures():
    """The figure registry check is reachable from the staged-file check."""
    assert "scripts/check_figures.py" in CHECK_STAGE.read_text()


def test_check_stage_still_refuses_the_things_it_used_to():
    """The three refusals the shim silently dropped."""
    text = CHECK_STAGE.read_text()

    for marker in ("data/*", "output/*", ".mapskey"):
        assert marker in text, f"{marker} refusal is gone from check_stage.sh"


def test_check_stage_chains_the_workspace_gate():
    """Chained, not replaced - and not replacing it either.

    This asserted the gate's absolute path appeared in the script. That
    path was one machine's home directory, and publishing it told a
    reader of a public repository the author's username and layout, so
    the script takes MARKING_SECURITY_GATE instead. The assertion moves
    with it: the script must still resolve a gate and still run it.
    """
    text = CHECK_STAGE.read_text()
    assert "MARKING_SECURITY_GATE" in text, "the gate is no longer resolved"
    assert '"$gate"' in text, "the gate is resolved and never run"
    assert "gate_status" in text, "the gate runs and its status is ignored"


def test_check_stage_carries_no_home_directory():
    """A public repository should not name anyone's home directory."""
    import re
    text = CHECK_STAGE.read_text()
    assert not re.search(r"/Users/[a-z]", text), "an absolute home path is back"
    assert not re.search(r"/home/[a-z]", text)


@pytest.mark.skipif(not HOOK.exists(), reason="hooks not installed here")
def test_installed_hook_reaches_check_stage():
    """What git will actually run has to get to the project's check.

    A symlink passes this too, but test_hook_is_not_a_symlink is what
    stops the failure recurring; this one stops the hook being pointed
    somewhere else entirely.
    """
    if HOOK.is_symlink():
        target = os.path.realpath(HOOK)
        assert target == str(CHECK_STAGE.resolve())
    else:
        assert "scripts/check_stage.sh" in HOOK.read_text()


@pytest.mark.skipif(not HOOK.exists(), reason="hooks not installed here")
def test_hook_is_not_a_symlink_into_scripts():
    """The specific hole that lost the check.

    `.git/hooks/pre-commit` as a symlink into scripts/ means any
    installer that writes that path rewrites a version-controlled file in
    the working tree. Keep it a regular wrapper: the write then lands on
    something disposable.
    """
    assert not HOOK.is_symlink(), (
        ".git/hooks/pre-commit is a symlink again. Run "
        "scripts/install_hooks.sh - a write to this path would overwrite "
        "scripts/check_stage.sh, which is how the check was lost on "
        "2026-09-21.")
