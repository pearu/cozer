# COZER GUI launcher for the bundled Windows installer.
#
# The conda env's native DLLs (glib/pango/cairo/gdk-pixbuf/fontconfig that
# WeasyPrint dlopens, plus Qt's) live in <prefix>\Library\bin, which is NOT on
# the search path when python starts directly (no `conda activate`).
#
# WeasyPrint dlopens by *bare name* (e.g. 'gobject-2.0-0'); cffi then resolves
# that via ctypes.util.find_library(), which searches **PATH** (see ctypes/util.py
# nt branch) -- NOT os.add_dll_directory and NOT WEASYPRINT_DLL_DIRECTORIES. So the
# DLL directory must be on PATH. (Qt loads differently, hence also add_dll_directory.)
import os
import sys

_libbin = os.path.join(sys.prefix, "Library", "bin")
_dll_handle = None
if os.path.isdir(_libbin):
    os.environ["PATH"] = _libbin + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        _dll_handle = os.add_dll_directory(_libbin)   # bound: don't let GC remove it

from cozer.__main__ import main  # noqa: E402  (must follow the DLL-path setup)

sys.exit(main())
