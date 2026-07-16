#!/bin/sh
# Fast local dev-run for the sshfs workflow.
#
# Running `python -m cozer` directly off an sshfs mount is slow (~6s startup)
# because each cozer/*.pyc is a network round-trip. This mirrors the *current
# working tree* (including uncommitted edits) from the mount to a local dir with
# rsync (~50ms), then runs from there at local speed (~0.2s). So you still verify
# uncommitted changes before committing — no `git pull` needed.
#
# Usage (run from the repo root on the laptop, in the activated cozer env):
#     sh tools/devrun.sh [args...]
# SRC defaults to the current directory; override either location if needed:
#     COZER_SRC=/path/to/mount COZER_LOCAL=$HOME/.cache/cozer-local sh tools/devrun.sh
set -e
SRC="${COZER_SRC:-$PWD}"                          # repo root (defaults to cwd)
DST="${COZER_LOCAL:-$HOME/.cache/cozer-local}"    # local run dir
mkdir -p "$DST"
rsync -a --delete \
    --exclude '.git' --exclude 'legacy' --exclude 'review' \
    --exclude '__pycache__' --exclude '.pytest_cache' \
    "$SRC/" "$DST/"
cd "$DST"
exec python -m cozer "$@"
