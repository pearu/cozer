#!/bin/sh
# Script to build wx 2.8 under Ubuntu 16.04 with anaconda2.
#
# Author: Pearu Peterson
# Created: July 2016

#sudo apt-get install gv # for cozer PSView
PREFIX=/home/pearu/anaconda2

mkdir build-wx2.8
cd build-wx2.8
wget https://sourceforge.net/projects/wxpython/files/wxPython/2.8.12.1/wxPython-src-2.8.12.1.tar.bz2
tar xjf wxPython-src-2.8.12.1.tar.bz2
cd wxPython-src-2.8.12.1
export WXWIN=`pwd`
mkdir bld
cd bld

../configure --prefix=$PREFIX \
             --with-gtk \
             --enable-debug \
             --enable-debug_gdb \
             --enable-geometry \
             --enable-graphics_ctx \
             --enable-sound --with-sdl \
             --enable-mediactrl \
	     --without-opengl \
	     --enable-unicode \
#             --with-gnomeprint \
#             --enable-display \
#             --with-opengl \
	     #

make && make -C contrib/src/gizmos && make -C contrib/src/stc
make install && make -C contrib/src/gizmos install && make -C contrib/src/stc install

export WX_CONFIG=$PREFIX/bin/wx-config
cd ../wxPython
echo "Edit config.py: BUILD_GLCANVAS = 0; OR configure --with-opengl" 
pip install -U --egg .

cd $PREFIX/lib/python2.7/site-packages/
echo wx-2.8-gtk2-unicode/ > wx28.pth

