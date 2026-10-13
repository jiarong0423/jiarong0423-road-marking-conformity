#!/bin/sh
# Point git's hooks at the ones kept in scripts/, so they are version
# controlled rather than living only in one working copy.
#
# 2026-09-21: this used to be `ln -sf ../../scripts/check_stage.sh
# .git/hooks/pre-commit`. A symlink there is a hole: any tool that
# installs its own pre-commit hook by writing that path writes *through*
# the link and overwrites the project's check. That is exactly what
# happened - see the header of scripts/check_stage.sh.
#
# What goes in .git/hooks/pre-commit is now a regular file, four lines of
# wrapper that exec the real check. The wrapper is disposable; the check
# is not. Edits to scripts/check_stage.sh still take effect immediately,
# because the wrapper execs it by path rather than copying it.
set -e
cd "$(git rev-parse --show-toplevel)"
mkdir -p .git/hooks

if [ -L .git/hooks/pre-commit ]; then
  rm -f .git/hooks/pre-commit
fi

cat > .git/hooks/pre-commit <<'WRAPPER'
#!/bin/sh
# Installed by scripts/install_hooks.sh. Deliberately a regular file and
# not a symlink into scripts/: a tool that writes its own hook to this
# path then overwrites this wrapper, not the project's check.
exec "$(git rev-parse --show-toplevel)/scripts/check_stage.sh" "$@"
WRAPPER

chmod +x .git/hooks/pre-commit scripts/check_stage.sh
echo "pre-commit (regular file) -> scripts/check_stage.sh -> check_figures.py + workspace security gate"
