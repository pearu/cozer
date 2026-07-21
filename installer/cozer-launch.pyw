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


def _report_startup_failure(exc):
    """The installer launches this with pythonw.exe (no console), so a startup crash would vanish
    with no window at all (exactly the report in issue #22 -- "clicking the icon does nothing").
    Make it visible instead: write the traceback to cozer-launch-error.log beside the install, and
    pop a native Windows dialog so the operator (and we) can see what went wrong."""
    import traceback
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logpath = os.path.join(sys.prefix, "cozer-launch-error.log")
    try:
        with open(logpath, "w", encoding="utf-8") as f:
            f.write(tb)
    except OSError:
        logpath = "(could not write log)"
    if sys.platform.startswith("win"):
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None,
            "COZER could not start.\n\n%s\n\nFull details saved to:\n%s"
            % (tb[-1200:], logpath),
            "COZER", 0x10)   # MB_ICONERROR


try:
    from cozer.__main__ import main  # noqa: E402  (must follow the DLL-path setup)
    sys.exit(main())
except Exception as exc:      # SystemExit (normal exit) is BaseException -> propagates untouched
    _report_startup_failure(exc)
    raise
