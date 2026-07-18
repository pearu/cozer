# COZER GUI launcher for the bundled Windows installer.
#
# The conda env's native DLLs (glib/pango/cairo/gdk-pixbuf/fontconfig that
# WeasyPrint dlopens, plus Qt's) live in <prefix>\Library\bin, which is NOT on
# the DLL search path when python starts directly (no `conda activate`). Point
# the loaders at it, then start the GUI (windowless via pythonw.exe).
import os
import sys

_libbin = os.path.join(sys.prefix, "Library", "bin")
_dll_handle = None
if os.path.isdir(_libbin):
    # WeasyPrint's supported hook: it splits this on ';' and add_dll_directory's
    # each entry, then dlopens with LOAD_LIBRARY_SEARCH_DEFAULT_DIRS.
    os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", _libbin)
    # For Qt / everything else: keep the handle alive for the process lifetime
    # (os.add_dll_directory REMOVES the dir when the returned object is GC'd).
    if hasattr(os, "add_dll_directory"):
        _dll_handle = os.add_dll_directory(_libbin)

from cozer.__main__ import main  # noqa: E402  (must follow the DLL-dir setup)

sys.exit(main())
