"""Catch-all fake ``wx`` so the LEGACY cozer code -- including the GUI-importing
package -- imports and its *headless* logic runs under stock Python 2.7 with no
wxPython build.

Install once, before importing any legacy module::

    import wx_shim; wx_shim.install()

Every attribute access yields a permissive dummy class (subclassable, callable,
further attribute-accessible), enough to execute the legacy class definitions
without a real toolkit. ``USE_UNICODE`` and dunder names raise AttributeError so
that (a) legacy ``prefs`` falls back to ``USE_UNICODE = 0`` (matching the golden
string convention, see tools/golden_io.py) and (b) ``from wx import X`` fails
cleanly instead of treating the shim as a package (which would leak a bogus
``__path__``).
"""
import sys


class _Dummy(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _Dummy()

    def __getattr__(self, name):
        return _Dummy

    def __iter__(self):
        return iter(())


class _WxModule(object):
    def __init__(self, name):
        self.__name__ = name

    def __getattr__(self, name):
        if name == 'USE_UNICODE' or (name.startswith('__') and name.endswith('__')):
            raise AttributeError(name)
        return _Dummy


def install():
    """Register the wx / wx.grid shims in ``sys.modules`` (idempotent)."""
    if not isinstance(sys.modules.get('wx'), _WxModule):
        wx = _WxModule('wx')
        grid = _WxModule('wx.grid')
        wx.grid = grid
        sys.modules['wx'] = wx
        sys.modules['wx.grid'] = grid
    return sys.modules['wx']
