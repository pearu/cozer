"""Reprimand notice (portrait, one page) — a blank fill-in form for a U.I.M. §406.04 reprimand.

A reprimand is a formal notice of disapproval of an unacceptable action (U.I.M. Circuit Rules 2026
§406.04): it must be recorded by the Race Secretariat and witnessed, it constitutes a warning that a
recurrence draws a heavier penalty, and it is valid 12 months. This report prints the notice as a
STATIC form the O.O.D. completes by hand for a specific incident — event header + the O.O.D./Secretary
signature lines are filled from the event; the competitor and the offence are write-in. English only
(U.I.M. official-form style; the article numbers are universal), matching the Inspection forms.
"""
from cozer.reports.common import esc, meta_of, document_html
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf

# The four §406.03 "unacceptable behaviour" grounds; a fifth "other breach" line covers a rules breach.
_GROUNDS = ("a deliberate act to gain unfair advantage",
            "a false act or statement suppressing facts required for the proper conduct of the race",
            "an attempt to bribe, or the taking of a bribe",
            "abusive or unsportsmanlike behaviour")

_CSS = """
.rn-note { margin:4px 0 10px; font-size:10.5px; color:#333; }
.rn-sec { font-weight:bold; margin:12px 0 4px; font-size:12px;
          border-bottom:2px solid #222; padding-bottom:2px; }
.rn-field { display:flex; align-items:flex-end; gap:6px; margin:6px 0; font-size:11px; }
.rn-lbl { white-space:nowrap; }
.rn-line { flex:1 1 auto; border-bottom:1px solid #555; min-height:1.15em; }
.rn-grid { display:flex; gap:14px; }
.rn-grid .rn-field { flex:1; }
.rn-box { display:inline-block; width:11px; height:11px; border:1.3px solid #333;
          margin-right:6px; vertical-align:-1px; }
.rn-check { font-size:11px; margin:3px 0; }
.rn-write { min-height:15.5em; border:1px solid #999; margin-top:3px; }
.rn-statement { border:2px solid #222; padding:9px 11px; margin:12px 0; font-size:11px;
                line-height:1.45; background:#f7f7f7; }
.rn-statement b { text-transform:uppercase; }
.rn-rights { font-size:9.5px; color:#444; margin:6px 0 2px; }
.rn-sig { display:flex; gap:24px; margin-top:6px; }
.rn-sig .rn-cell { flex:1; }
.rn-sig .rn-sigline { border-bottom:1px solid #333; height:1.9em; }
.rn-sig .rn-cap { font-size:9px; color:#444; margin-top:2px; }
.rn-name { font-size:11px; font-weight:bold; }
"""


def _field(label):
    return ('<div class="rn-field"><span class="rn-lbl">%s</span><span class="rn-line"></span></div>'
            % esc(label))


def _sig(name, caption):
    return ('<div class="rn-cell"><div class="rn-sigline"></div><div class="rn-cap">%s</div>%s</div>'
            % (esc(caption), ('<div class="rn-name">%s</div>' % esc(name)) if name else ""))


def _body(meta):
    ood = (meta.get("officer") or "").strip()
    sec = (meta.get("secretary") or "").strip()
    b = ['<style>%s</style>' % _CSS]
    b.append('<div class="rn-note">Issued under Article <b>406.04</b> of the U.I.M. Circuit Racing Rules '
             '2026. A reprimand is a formal notice of disapproval of an unacceptable action; it must be '
             'recorded by the Race Secretariat and witnessed, and it constitutes a warning that a '
             'recurrence will draw a heavier penalty (valid 12 months).</div>')

    b.append('<div class="rn-sec">Competitor</div>')
    b.append('<div class="rn-grid">%s%s</div>' % (_field("Driver / competitor"), _field("Boat No.")))
    b.append('<div class="rn-grid">%s%s%s</div>'
             % (_field("Class"), _field("Nationality"), _field("Licence No.")))

    b.append('<div class="rn-sec">The unacceptable action</div>')
    b.append('<div class="rn-grid">%s%s</div>' % (_field("Date and time of the incident"),
                                                  _field("Race / heat / session")))
    b.append('<div class="rn-field"><span class="rn-lbl">Description</span></div>')
    b.append('<div class="rn-write"></div>')
    b.append('<div class="rn-field" style="margin-top:8px"><span class="rn-lbl">Ground '
             '(&sect;406.03 &mdash; tick as applicable):</span></div>')
    for g in _GROUNDS:
        b.append('<div class="rn-check"><span class="rn-box"></span>%s</div>' % esc(g))
    b.append('<div class="rn-check"><span class="rn-box"></span>other breach of the applicable rules: '
             '<span class="rn-line" style="display:inline-block;width:60%;"></span></div>')

    b.append('<div class="rn-statement">You are hereby issued a <b>reprimand</b> &mdash; a formal notice '
             'of disapproval of the unacceptable action described above, under U.I.M. Circuit Rules '
             '&sect;406.04. This reprimand <b>automatically constitutes a warning</b>: should the offence '
             'recur, a heavier penalty will be imposed. It is <b>valid for twelve (12) months</b> from the '
             'date of issue below and is <b>recorded by the Race Secretariat</b>.</div>')
    b.append('<div class="rn-rights">The competitor may lodge a protest against this penalty as provided '
             'in &sect;403, and, if it is not upheld, may appeal under &sect;405.</div>')

    b.append('<div class="rn-sec">Issue, witness and record</div>')
    b.append('<div class="rn-grid">%s%s</div>' % (_field("Date issued"), _field("Time issued")))
    b.append('<div class="rn-sig">%s%s</div>'
             % (_sig(ood, "Officer of the Day / Race Director — signature (§406.04)"),
                _sig("", "Witness — name, role and signature (§406.04)")))
    b.append('<div class="rn-sig" style="margin-top:14px">%s%s</div>'
             % (_sig(sec, "Recorded by the Secretary of the Race — signature (§406.04)"),
                _sig("", "Received by the competitor — signature (refusal to sign is noted)")))
    return b


def build_reprimand(eventdata, classes=None):
    return {"meta": meta_of(eventdata), "labels": get_labels(eventdata), "orientation": "portrait",
            "heading": "Reprimand", "subtitle": "U.I.M. Circuit Rules §406.04"}


def reprimand_html(model):
    return document_html(model["orientation"], model["labels"], model["meta"], model["heading"],
                         _body(model["meta"]), subtitle=model["subtitle"], posting=False)


def render_reprimand(eventdata, out_path, classes=None):
    render_pdf(reprimand_html(build_reprimand(eventdata)), out_path)
