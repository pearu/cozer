"""cozer report generation: build report models from the proven scoring core
and render them to print-quality PDF via HTML/CSS (WeasyPrint, offline).

The same HTML templates are intended to feed the online/live view later
(Phase 7), so report content and live output share one source.
"""
from cozer.reports.final import (
    build_full_final, full_final_html, render_full_final,
    build_short_final, short_final_html, render_short_final,
    build_full_final_legacy, full_final_legacy_html, render_full_final_legacy,
    build_short_final_legacy, short_final_legacy_html, render_short_final_legacy,
)
from cozer.reports.participants import (
    build_participants, participants_html, render_participants,
    build_checklist, checklist_html, render_checklist,
)
from cozer.reports.intermediate import (
    build_intermediate, intermediate_html, render_intermediate,
)
from cozer.reports.qsummary import (
    build_qualification, qualification_html, render_qualification,
)
from cozer.reports.laps import (
    build_laps_protocol, laps_protocol_html, render_laps_protocol,
)
from cozer.reports.endurance import (
    build_endurance_final, endurance_final_html, render_endurance_final,
)
from cozer.reports.letters import (
    build_info_letter, info_letter_html, render_info_letter,
    build_registration_letter, registration_letter_html, render_registration_letter,
)
from cozer.reports.inspection import (
    build_inspection_cockpit, inspection_cockpit_html, render_inspection_cockpit,
    build_inspection_open, inspection_open_html, render_inspection_open,
)

__all__ = [
    "build_full_final", "full_final_html", "render_full_final",
    "build_short_final", "short_final_html", "render_short_final",
    "build_full_final_legacy", "full_final_legacy_html", "render_full_final_legacy",
    "build_short_final_legacy", "short_final_legacy_html", "render_short_final_legacy",
    "build_participants", "participants_html", "render_participants",
    "build_checklist", "checklist_html", "render_checklist",
    "build_intermediate", "intermediate_html", "render_intermediate",
    "build_qualification", "qualification_html", "render_qualification",
    "build_laps_protocol", "laps_protocol_html", "render_laps_protocol",
    "build_endurance_final", "endurance_final_html", "render_endurance_final",
    "build_info_letter", "info_letter_html", "render_info_letter",
    "build_registration_letter", "registration_letter_html", "render_registration_letter",
    "build_inspection_cockpit", "inspection_cockpit_html", "render_inspection_cockpit",
    "build_inspection_open", "inspection_open_html", "render_inspection_open",
]
