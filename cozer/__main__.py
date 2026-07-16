"""Entry point for ``python -m cozer`` — launches the PySide6 GUI."""
import faulthandler
import os
import sys

# Dump a Python traceback if the process gets a fatal signal (segfault/abort),
# so native crashes are diagnosable instead of a bare "core dumped".
faulthandler.enable()


def _ensure_fontconfig():
    """Work around a recurring segfault in conda's libfontconfig
    (FcCharSetFindLeafForward): the env shares ~/.cache/fontconfig with the
    system's different-version fontconfig and crashes reading an incompatible
    cache. Point fontconfig at a private cache dir (keeping every font dir), so
    it only ever reads its own cache. Must run before Qt loads its font system.

    Linux + conda only; skipped if FONTCONFIG_FILE or COZER_NO_FONT_FIX is set.
    Best-effort: any failure leaves fontconfig untouched.
    """
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("FONTCONFIG_FILE") or os.environ.get("COZER_NO_FONT_FIX"):
        return
    prefix = os.environ.get("CONDA_PREFIX")
    if not prefix or not os.path.exists(os.path.join(prefix, "etc", "fonts", "fonts.conf")):
        return
    try:
        cachedir = os.path.join(prefix, "var", "cache", "cozer-fontconfig")
        os.makedirs(cachedir, exist_ok=True)
        dirs = "".join(
            "  <dir>%s</dir>\n" % d for d in
            ("/usr/share/fonts", os.path.join(prefix, "share", "fonts"),
             os.path.join(prefix, "fonts"), "~/.fonts"))
        conf = os.path.join(prefix, "etc", "cozer-fonts.conf")
        with open(conf, "w") as f:
            f.write('<?xml version="1.0"?>\n'
                    '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
                    '<fontconfig>\n%s'
                    '  <dir prefix="xdg">fonts</dir>\n'
                    '  <cachedir>%s</cachedir>\n'
                    '  <include ignore_missing="yes">%s</include>\n'
                    '</fontconfig>\n'
                    % (dirs, cachedir, os.path.join(prefix, "etc", "fonts", "conf.d")))
        os.environ["FONTCONFIG_FILE"] = conf
    except OSError:
        pass


def main(argv=None):
    print("Starting COZER…", file=sys.stderr)          # instant terminal feedback
    argv = sys.argv[1:] if argv is None else argv
    _ensure_fontconfig()                               # before Qt loads its font system
    from cozer.app.main import run
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
