#!/usr/bin/env bash
# Parallel test runner — no `make` dependency. Uses pytest-xdist to spread the suite
# across cores (the report/PDF-render + e2e tests dominate and parallelize well).
#
#   ./tools/test.sh              # full suite + coverage, parallel      (~9s vs ~37s serial)
#   ./tools/test.sh fast         # no coverage, parallel                (~6s)
#   ./tools/test.sh -k misclick  # any extra pytest args pass through
#   ./tools/test.sh fast tests/test_store.py       # combine
#   PYTEST_WORKERS=8 ./tools/test.sh               # override worker count
#
# Default workers = 12: <= the 18 physical cores, leaving headroom for the OS and a
# second session. HT cores (36) over-subscribe — don't raise it past ~16.
set -eu

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKERS="${PYTEST_WORKERS:-12}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"   # tests are headless

# The cozer env interpreter (override with COZER_PY on another machine / CI).
PY="${COZER_PY:-}"
if [ -z "$PY" ]; then
  if [ -x /home/pearu/miniconda3/envs/cozer/bin/python ]; then
    PY=/home/pearu/miniconda3/envs/cozer/bin/python
  else
    PY=python
  fi
fi

extra=()
if [ "${1:-}" = "fast" ]; then extra+=(--no-cov); shift; fi   # `fast` => skip coverage

cd "$REPO"
exec "$PY" -m pytest -n "$WORKERS" "${extra[@]}" "$@"
