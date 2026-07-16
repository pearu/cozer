"""Entry point for ``python -m cozer`` — launches the PySide6 GUI.

The splash is built inline here with **only** PySide6, deliberately importing no
``cozer.app.*`` module until it is on screen: importing them first would read
each module over the filesystem (slow on a network mount) before the user sees
anything. So the order is: instant terminal line -> Qt -> splash -> the rest.
"""
import sys


def main(argv=None):
    print("Starting COZER…", file=sys.stderr)          # instant terminal feedback
    argv = sys.argv[1:] if argv is None else argv
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication, QSplashScreen
    app = QApplication.instance() or QApplication([sys.argv[0]] + list(argv))
    pm = QPixmap(440, 180)
    pm.fill(QColor("#2b3a67"))
    p = QPainter(pm)
    p.setPen(QColor("#f4f3ee"))
    p.setFont(QFont("DejaVu Sans", 30, QFont.Bold))
    p.drawText(pm.rect().adjusted(0, 34, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "COZER")
    p.setFont(QFont("DejaVu Sans", 11))
    p.drawText(pm.rect().adjusted(0, 96, 0, 0), Qt.AlignHCenter | Qt.AlignTop,
               "COmpetition organiZER")
    p.end()
    splash = QSplashScreen(pm)
    splash.showMessage("Starting up…", Qt.AlignBottom | Qt.AlignHCenter, QColor("#f4f3ee"))
    screen = app.primaryScreen()
    if screen is not None:
        splash.move(screen.availableGeometry().center() - splash.rect().center())
    splash.show()
    app.processEvents()
    from cozer.app.main import run                      # cozer.app.* read AFTER the splash
    return run(argv, app=app, splash=splash)


if __name__ == "__main__":
    sys.exit(main())
