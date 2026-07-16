#!/bin/bash
# Build wxPython 2.8 + a runnable legacy-cozer conda env on a modern (2026)
# Linux toolchain. This is the July-2024 conda_install.sh approach, updated and
# made self-contained for GCC 14 / glibc 2.39 / today's conda-forge. Verified on
# Ubuntu 24.04 (conda-forge gcc 14.3, python 2.7.15, gtk2 2.24) with NO source
# patches -- only compiler flags and two conda-drift fixes.
#
#   Usage:   bash legacy/build_legacy_env.sh [env_name]      # default: cozer2
#   Run:     bash legacy/run_legacy.sh [event.coz]
#
# Needs a conda/mamba install (miniforge). Building needs no display; running
# the GUI does (your laptop screen, or an X server).
set -euo pipefail
ENV=${1:-cozer2}
WXVER=2.8.12.1
BUILD=${COZER_WX_BUILD:-$HOME/build-wx2.8}

echo "== 1/4  create env '$ENV' (python 2.7 + build tools + gtk2) =="
# xorg-xorgproto is the 2026 drift fix: gtk+-2.0.pc's X11 proto .pc chain is no
# longer pulled transitively, so pkg-config can't resolve gtk+-2.0 without it.
mamba create -n "$ENV" -y -c conda-forge \
    python=2.7 compilers make pkg-config gtk2 glib libxcrypt pip wget xorg-xorgproto

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV"
export PKG_CONFIG_PATH="$CONDA_PREFIX/lib/pkgconfig:$CONDA_PREFIX/share/pkgconfig"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
# GCC 14 vs 2011-era C/C++: old C++ standard + permissive + -fcommon avoids every
# breakage without touching a single source file.
export CFLAGS="${CFLAGS:-} -fcommon -Wno-implicit-int -Wno-implicit-function-declaration -Wno-narrowing"
export CXXFLAGS="${CXXFLAGS:-} -std=gnu++98 -fpermissive -fcommon -Wno-narrowing"

echo "== 2/4  download wxPython $WXVER source =="
mkdir -p "$BUILD"; cd "$BUILD"
[ -f "wxPython-src-$WXVER.tar.bz2" ] || \
    wget -q "https://downloads.sourceforge.net/project/wxpython/wxPython/$WXVER/wxPython-src-$WXVER.tar.bz2"
[ -d "wxPython-src-$WXVER" ] || tar xjf "wxPython-src-$WXVER.tar.bz2"
cd "wxPython-src-$WXVER"
export WXWIN="$(pwd)"

echo "== 3/4  build + install wxWidgets 2.8 (GTK2, unicode) =="
rm -rf bld; mkdir bld; cd bld
../configure --prefix="$CONDA_PREFIX" --with-gtk --enable-unicode --without-opengl --disable-mediactrl
make -j"$(nproc)"
make install
export WX_CONFIG="$CONDA_PREFIX/bin/wx-config"

echo "== 4/4  build wxPython 2.8 bindings (only the modules cozer uses) =="
cd "$WXWIN/wxPython"
sed -i 's/^BUILD_GLCANVAS = 1/BUILD_GLCANVAS = 0/; s/^BUILD_STC = 1/BUILD_STC = 0/; s/^BUILD_GIZMOS = 1/BUILD_GIZMOS = 0/' config.py
# py2.7's LDSHARED bakes "--sysroot=/", which points the linker at the host
# /lib64/libpthread.so.0 -- absent on merged-glibc (2.34+) systems. Repoint it at
# the conda sysroot, which still has it.
SYSROOT="$CONDA_PREFIX/x86_64-conda-linux-gnu/sysroot"
export LDSHARED="x86_64-conda-linux-gnu-gcc -pthread -shared -B $CONDA_PREFIX/compiler_compat -L$CONDA_PREFIX/lib -Wl,-rpath=$CONDA_PREFIX/lib -Wl,--no-as-needed -Wl,--sysroot=$SYSROOT"
python setup.py build_ext --inplace UNICODE=1 WXPORT=gtk2

echo ""
echo "== DONE =="
python -c "import wx; print('wxPython built:', wx.version())"
echo "Now run:   bash legacy/run_legacy.sh events/wc2000.coz"
