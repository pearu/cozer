#!/bin/bash
# Screenshot a legacy-cozer notebook page headlessly, as a GUI reference.
# Needs the env from build_legacy_env.sh plus a native Xvfb + xkbcomp on the host
# (e.g. `sudo apt install -y xvfb`) and imagemagick's `import` (in the env).
#
#   PAGE=Timer RACE=0 SHOT=/path/out.png bash legacy/screenshot_legacy.sh [event.coz]
#
# PAGE is a notebook tab name (Timer, "Edit Race Records", Reports, ...); for the
# Timer, RACE selects which race to show.
set -euo pipefail
ENV=${COZER_LEGACY_ENV:-cozer2}
BUILD=${COZER_WX_BUILD:-$HOME/build-wx2.8}
WXVER=2.8.12.1
HERE="$(cd "$(dirname "$0")" && pwd)"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="$BUILD/wxPython-src-$WXVER/wxPython:$HERE"
export PAGE=${PAGE:-Timer}
export RACE=${RACE:-0}
export SHOT=${SHOT:-/tmp/cozer_${PAGE// /_}.png}
cd "$HERE"
xvfb-run -a --server-args="-screen 0 1200x800x24" python screenshot_page.py "${1:-events/wc2000.coz}"
echo "saved: $SHOT"
