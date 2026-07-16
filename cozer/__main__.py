"""Entry point for ``python -m cozer`` — launches the PySide6 GUI.

The splash is shown as early as possible: after Qt itself is imported (a Qt
splash cannot render before that) but *before* importing the rest of cozer,
which is the slow part of startup.
"""
import sys


def main(argv=None):
    print("Starting COZER…", file=sys.stderr)          # instant terminal feedback
    argv = sys.argv[1:] if argv is None else argv
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([sys.argv[0]] + list(argv))
    from cozer.app.splash import center_splash, make_splash
    splash = make_splash()
    center_splash(app, splash)
    splash.show()
    app.processEvents()
    from cozer.app.main import run                      # heavy imports happen here
    return run(argv, app=app, splash=splash)


if __name__ == "__main__":
    sys.exit(main())
