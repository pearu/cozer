"""cozer report generation: build report models from the proven scoring core
and render them to print-quality PDF via HTML/CSS (WeasyPrint, offline).

The same HTML templates are intended to feed the online/live view later
(Phase 7), so report content and live output share one source.
"""
from cozer.reports.final import build_full_final, full_final_html, render_full_final

__all__ = ["build_full_final", "full_final_html", "render_full_final"]
