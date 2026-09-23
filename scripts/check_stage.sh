#!/bin/sh
# Refuse to stage what must not be published.
#
# Carried over from the previous entry, where a rule written in a
# document was broken in the next command by the same session with the
# document open. The check is mechanical for that reason.
#
# Installed as .git/hooks/pre-commit by scripts/install_hooks.sh.
#
# 2026-09-21: this file was itself destroyed by the mechanism it guards
# against. `.git/hooks/pre-commit` was a *symlink* to this path, and
# the workspace-level install_security_hooks.py writes its
# three-line shim to `.git/hooks/pre-commit`. The write followed the
# symlink and landed here, replacing the whole project check with an
# `exec` of the shared workspace security gate. The gate does not call
# check_figures, so the figure registry check, the data/ and output/
# staging refusal and the .mapskey credential check all stopped running,
# silently, one commit after the figure check was hardened.
#
# Two changes came out of that, and standing rule 3 is the reason:
#
#   * both checks now run from here - this file's own rules first, then
#     the workspace gate - and the commit is refused if either objects;
#   * scripts/install_hooks.sh installs a regular file at
#     .git/hooks/pre-commit that execs this script, not a symlink to it,
#     so the next tool that writes to that path overwrites a disposable
#     four-line wrapper instead of the project's check.
#
# tests/test_hook_chain.py fails if either half of the chain is missing.
set -e

staged=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$staged" ] && exit 0
fail=0

note() { printf '  %s\n    %s\n' "$1" "$2"; fail=1; }

for path in $staged; do
  case "$path" in
    .venv*/*|*/.venv*/*)
      note "$path" "a virtualenv: platform-specific binaries, useless elsewhere" ;;
    data/field-2026-09-20/*)
      # Named before the general data/ rule, because the general rule's
      # reason is an argument for overriding it and this one must not be
      # overridden. These 42 files are the PRE-REDACTION originals of
      # evidence/field-2026-09-20/: five of them carry a legible vehicle
      # registration plate. All five differ from the published copies by
      # SHA-256. Publishing them once is not undoable - it already cost
      # this project a deleted and rebuilt GitHub repository on
      # 2026-09-21, because a force-push leaves the blobs retrievable.
      note "$path" "a PRE-REDACTION original: five of these 42 carry a
    legible registration plate. There is no reason to stage this. Do not
    use --no-verify here." ;;
    data/*)
      note "$path" "the Seoul dataset: 4.6 GB, CC0 and re-obtainable with
    scripts/fetch_seoul.sh. Nothing from it belongs in git." ;;
    output/*)
      note "$path" "run output, not evidence until a script regenerates it" ;;
  esac

  # A key in a public repository is scraped within minutes, and .gitignore
  # alone does not stop `git add -f`. This is the check that survives that.
  case "$path" in
    *.mapskey|.mapskey|*.env|.env*|*.pem|*.key)
      note "$path" "credential-shaped filename" ;;
  esac

  if [ -f "$path" ] && [ "$(wc -c < "$path")" -lt 200000 ]; then
    if LC_ALL=C grep -qE "AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|ghp_[0-9A-Za-z]{36}|sk-[0-9A-Za-z]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----" "$path" 2>/dev/null; then
      note "$path" "contains something shaped like an API key or a private key"
    fi
  fi

  if [ -f "$path" ]; then
    size=$(wc -c < "$path" | tr -d " ")

    # The reason this asked for, given once.
    #
    # evidence/field-2026-09-20/ holds 42 photographs of 116 縣道 taken on
    # 2026-09-20, 3072x4096, about 5 MB each. They are the project's
    # primary evidence and cannot be re-obtained: the surface has been
    # worked on again since. They are published at full resolution
    # because reduction is not free - over the 42, reducing to 2000 px
    # changes 17 findings and 10 taper verdicts, and five photographs
    # gain a finding their originals refuse to make. A repository whose
    # argument is reproducibility cannot ship an article that measures
    # differently from the one measured.
    #
    # Five carry a masked registration plate; see the manifest's
    # `redacted` column and results/plate_redactions.json.
    #
    # evidence/field-2026-09-23/ holds 64 photographs taken 06:30-06:34 on
    # 2026-09-23: top, front and low side shots of the seven drain grates,
    # a card laid on the red line, and three wide shots. The recognition
    # results (red line over the grates, the card ruler) are measured on
    # the originals, for the same reason as above. Close-ups show pavement
    # only; in the three wide shots (P62-P64) no registration plate is
    # legible, checked by eye at full resolution on 2026-09-23.
    case "$path" in
      evidence/field-2026-09-20/*.jpg) continue ;;
      evidence/field-2026-09-23/*.jpg) continue ;;
    esac

    if [ "$size" -gt 2000000 ]; then
      note "$path" "$(( size / 1000000 )) MB. Large files need a reason; add one here."
    fi
  fi
done

# Published figures must still equal the files that produced them. Narrow on
# purpose: a check that cries wolf gets bypassed, and the bypass would take
# the rules above with it.
root=$(git rev-parse --show-toplevel)
if [ -f "$root/results/figure_registry.json" ]; then
  if python3 "$root/scripts/check_figures.py" > /tmp/marking_figures.$$ 2>&1; then
    # Say so on success too. A check that is silent when it passes looks
    # exactly like a check that is not running, and that is how this one
    # went missing for a day on 2026-09-21.
    sed 's/^/[check_figures] /' /tmp/marking_figures.$$
  else
    echo ""
    cat /tmp/marking_figures.$$
    fail=1
  fi
  rm -f /tmp/marking_figures.$$
fi

# The workspace security gate, chained rather than replacing the above.
# It runs second because it is the slow half - two python audits over the
# staged set - and because the project's own refusals should be the first
# thing on screen. It is run unconditionally, not short-circuited on a
# failure above, so one commit attempt shows every reason it was refused.
#
# A missing gate is a degradation, not a failure: this repository is meant
# to be clonable outside this workspace, and hard-failing every commit on
# a tool that lives outside it would be the "cries wolf" problem again. It
# says so on stderr, loudly, rather than passing in silence.
# The workspace-level gate lives outside this repository. Its path was
# hardcoded to one machine's home directory, which told a reader of a
# public repository the author's username and directory layout, and told
# a cloner nothing useful. It is an environment variable with that path
# as the default for the machine it was written on.
gate="${MARKING_SECURITY_GATE:-$HOME/Developer/tools/pre_commit_security_gate.sh}"
if [ -x "$gate" ]; then
  gate_status=0
  "$gate" "$@" || gate_status=$?

  if [ "$gate_status" -ne 0 ]; then
    echo "ERROR [check_stage] workspace security gate refused (exit $gate_status)" >&2
    fail=1
  fi
else
  echo "WARN [check_stage] workspace security gate absent at $gate;" >&2
  echo "WARN [check_stage] only this repository's own checks ran." >&2
fi

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "Refusing to stage the above. Override with --no-verify only if you can"
  echo "say out loud why it is safe to publish."
  exit 1
fi
