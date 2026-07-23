"""Modal dialogs that can't hide behind other windows — plus non-blocking notices.

cozer's message boxes and custom dialogs are **application-modal**: ``exec()`` grabs *all* input until
the dialog is dismissed. If cozer is not the frontmost window when one opens — the operator was in a
browser or the broadcast page, a fullscreen scoreboard or a second monitor is covering cozer — the
dialog can open *behind* that window while still blocking every click on cozer, so the app looks frozen
(an operator has hit exactly this). Everything here forces the dialog to the front (raise + activate +
flash the taskbar/dock) and drops a ``Waiting for input: …`` breadcrumb into the Log, so a hidden prompt
is both prevented and diagnosable after the fact.

Use ``question`` / ``warn`` / ``error`` for prompts that need a decision or report a failure the operator
must acknowledge, ``run_modal`` for a custom ``QDialog``/``QMessageBox`` the caller built, and
``notify`` for a *purely informational* message — that one does NOT block; it goes to the status bar and
the Log instead of interrupting with a modal.
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget


def _log(widget, msg):
    """Write to the MainWindow Log/status bar if one is reachable from ``widget`` (best-effort)."""
    if widget is None:
        win = None
    elif isinstance(widget, QWidget):
        # Call the real QWidget.window() explicitly: many cozer panels shadow `.window` with an instance
        # attribute (self.window = the MainWindow reference), so `widget.window()` would try to CALL that
        # attribute -> "'MainWindow' object is not callable" (issue #39). QWidget.window(widget) bypasses
        # the shadow and returns the top-level window regardless.
        win = QWidget.window(widget)
    else:
        wf = getattr(widget, "window", None)   # a duck-typed object with a window() method
        win = wf() if callable(wf) else None
    logfn = getattr(win, "log", None)
    if callable(logfn):
        logfn(msg)


def bring_to_front(dlg):
    """Pull a visible dialog above other windows, focus it, and flash the taskbar/dock. ``alert`` is the
    fallback for when the OS refuses to let a background app steal focus (Windows): the operator still
    gets a visible nudge and finds the dialog on top the moment they click cozer."""
    dlg.raise_()
    dlg.activateWindow()
    QApplication.alert(dlg)


def _arm(dlg, title, parent):
    """Log the breadcrumb and schedule ``bring_to_front`` for once the modal loop is running (the dialog
    is shown inside ``exec()``). A 0-ms timer fires as soon as that nested loop processes events, so it
    works for any QDialog/QMessageBox without subclassing."""
    _log(parent, "Waiting for input: %s" % (title or "cozer"))
    QTimer.singleShot(0, lambda: bring_to_front(dlg))


def run_modal(dlg, parent=None):
    """``exec()`` a caller-built ``QDialog``/``QMessageBox``, forced to the front. Returns exec()'s result."""
    _arm(dlg, dlg.windowTitle(), parent if parent is not None else dlg.parent())
    return dlg.exec()


def _box(parent, icon, title, text, buttons, default):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default is not None:
        box.setDefaultButton(default)
    _arm(box, title, parent)
    return box.exec()


def question(parent, title, text,
             buttons=QMessageBox.Yes | QMessageBox.No, default=QMessageBox.No):
    """A front-forced Yes/No (or custom-button) prompt. Returns the clicked StandardButton."""
    return _box(parent, QMessageBox.Question, title, text, buttons, default)


def info(parent, title, text, buttons=QMessageBox.Ok, default=None):
    """A front-forced informational modal the operator must *see and acknowledge* — actionable
    instructions (e.g. "update installed, reopen cozer"), not a passing status. For a passing status
    that need not block, use ``notify``."""
    return _box(parent, QMessageBox.Information, title, text, buttons, default)


def warn(parent, title, text, buttons=QMessageBox.Ok, default=None):
    """A front-forced warning the operator must see (validation failure, blocked action)."""
    return _box(parent, QMessageBox.Warning, title, text, buttons, default)


def error(parent, title, text, buttons=QMessageBox.Ok, default=None):
    """A front-forced error report (a user action failed)."""
    return _box(parent, QMessageBox.Critical, title, text, buttons, default)


def notify(widget, text):
    """A *non-blocking* replacement for a purely-informational popup: show it in the status bar + Log
    instead of interrupting with a modal. No blocking, no return value."""
    _log(widget, text)
