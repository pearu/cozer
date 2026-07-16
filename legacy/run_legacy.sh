#!/bin/bash
# Run the legacy (Python 2 / wxPython 2.8) cozer GUI built by
# build_legacy_env.sh. Needs a display (your laptop screen).
#
#   bash legacy/run_legacy.sh [event.coz]
#
# Overridable:  COZER_LEGACY_ENV (default cozer2), COZER_WX_BUILD (default ~/build-wx2.8)
set -euo pipefail
ENV=${COZER_LEGACY_ENV:-cozer2}
BUILD=${COZER_WX_BUILD:-$HOME/build-wx2.8}
WXVER=2.8.12.1
HERE="$(cd "$(dirname "$0")" && pwd)"          # the legacy/ dir

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
# in-place wxPython build + the legacy cozer package
export PYTHONPATH="$BUILD/wxPython-src-$WXVER/wxPython:$HERE"
cd "$HERE"
exec python cozer.py "${1:-events/wc2000.coz}"
