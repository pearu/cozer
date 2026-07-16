"""Startup splash — deliberately dependency-light (PySide6 only, no other cozer
imports) so ``__main__`` can show it *before* importing the rest of cozer, which
is the slow part of startup."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen


def make_splash():
    """A small COZER splash shown while the app sets up."""
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
    return splash


def center_splash(app, splash):
    """Center the splash on the primary screen. (No-op on Wayland, where the
    compositor, not the app, controls window placement.)"""
    screen = app.primaryScreen()
    if screen is not None:
        splash.move(screen.availableGeometry().center() - splash.rect().center())
