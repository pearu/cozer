"""Minimal fake ``wx`` so the LEGACY cozer core imports and runs headless under
stock Python 2.7 -- no wxPython 2.8 build required.

Install with::

    import wx_shim; sys.modules['wx'] = wx_shim

Only the symbols the *non-GUI* core (``legacy/cozer/prefs.py`` +
``analyzer.py``) touches at import/run time are provided. Deliberately does NOT
define ``USE_UNICODE`` so ``prefs`` falls back to 0 (no str<->unicode
re-encoding): the scoring results are unaffected by that choice, and strings are
carried through losslessly as raw bytes (see tools/golden_io.py).
"""


def Colour(*args):
    return ('Colour',) + tuple(args)


def Bell(*args, **kwargs):
    pass


def LogMessage(*args, **kwargs):
    pass


class Timer(object):
    def __init__(self, *args, **kwargs):
        pass

    def Start(self, *args, **kwargs):
        pass

    def Stop(self, *args, **kwargs):
        pass

    def Notify(self, *args, **kwargs):
        pass


GREEN = Colour(0, 255, 0)
WHITE = Colour(255, 255, 255)
BLACK = Colour(0, 0, 0)
RED = Colour(255, 0, 0)
