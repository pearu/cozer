# COZER GUI launcher for the bundled Windows installer.
#
# The conda env's native DLLs -- the glib/pango/cairo/gdk-pixbuf/fontconfig that
# WeasyPrint dlopens, plus Qt's -- live in <prefix>\Library\bin, which is NOT on
# the DLL search path when python is started directly (no `conda activate`).
# Add it explicitly (the modern, secure way, not via PATH), then start the GUI.
# Run windowless via pythonw.exe from the Start-menu shortcut.
import os
import sys

_dll = os.path.join(sys.prefix, "Library", "bin")
if hasattr(os, "add_dll_directory") and os.path.isdir(_dll):
    os.add_dll_directory(_dll)

from cozer.__main__ import main   # noqa: E402  (must follow the DLL-dir setup)

sys.exit(main())
