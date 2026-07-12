"""Phase 0 smoke tests.

These assert only packaging/environment invariants and keep CI meaningful
until the ported core lands (Phase 2), at which point golden/differential
tests replace them as the substance of the suite.
"""


def test_cozer_imports_and_has_version():
    import cozer

    assert isinstance(cozer.__version__, str)
    assert cozer.__version__


def test_report_toolchain_importable():
    # WeasyPrint = offline HTML/CSS -> PDF; PyMuPDF (fitz) = PDF text extraction
    # used by the report equivalence tests.
    import weasyprint  # noqa: F401
    import fitz  # PyMuPDF  # noqa: F401


def test_gui_toolkit_importable():
    # Importing PySide6 must not require a display (no QApplication created here).
    from PySide6 import QtCore

    assert QtCore.qVersion()
