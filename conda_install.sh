#!/bin/sh
# Script to build wx 2.8 under Ubuntu 22.04 with conda.
#
# Author: Pearu Peterson
# Created: July 2024

#sudo apt-get install gv # for cozer PSView

# Prerequisites:
#   mamba install python=2 compilers make pkg-config gtk2 glib libxcrypt

PREFIX=$CONDA_PREFIX
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
export CXXFLAGS="$CXXFLAGS -Wno-narrowing"
mkdir -p build-wx2.8
cd build-wx2.8
#wget https://sourceforge.net/projects/wxpython/files/wxPython/2.8.12.1/wxPython-src-2.8.12.1.tar.bz2
#tar xjf wxPython-src-2.8.12.1.tar.bz2
cd wxPython-src-2.8.12.1
export WXWIN=`pwd`
#rm -rf bld
mkdir -p bld
cd bld

../configure --prefix=$PREFIX \
             --with-gtk \
             --enable-geometry \
             --enable-graphics_ctx \
             --enable-sound --with-sdl \
             --enable-mediactrl \
	     --without-opengl \
	     --enable-unicode \
#              --enable-debug_gdb \
#             --enable-debug \
#             --with-gnomeprint \
#             --enable-display \
#             --with-opengl \
	     #

make && make -C contrib/src/gizmos && make -C contrib/src/stc

make install && make -C contrib/src/gizmos install && make -C contrib/src/stc install

export WX_CONFIG=$PREFIX/bin/wx-config
cd ../wxPython
echo "Edit config.py: BUILD_GLCANVAS = 0; OR configure --with-opengl"

export PYTHONPATH=$CONDA_PREFIX/lib/python2.7/site-packages/wx-2.8-gtk2-unicode
cd $PREFIX/lib/python2.7/site-packages/
echo wx-2.8-gtk2-unicode/ > wx28.pth
cd -
pip install -e  .
