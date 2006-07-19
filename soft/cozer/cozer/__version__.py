__version__ = '2.6'
try:
    from __svn_version__ import version
    __version__ += '_svn' + version
except ImportError:
    pass
