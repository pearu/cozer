"""Tests for the report pipeline: LaTeX-in-text decoding, result formatting,
report-model assembly against the proven scoring core, and PDF rendering
(orientation + page-fit)."""
import copy
import os
import sys

import fitz
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cozer.store import read_legacy_coz  # noqa: E402
from cozer.analyzer import analyze, sumanalyze, getsumresorder  # noqa: E402
from cozer.reports.latexish import latex_to_html  # noqa: E402
from cozer.reports.final import (  # noqa: E402
    build_full_final, full_final_html, _result_text, _sheats,
    build_short_final, short_final_html,
)
from cozer.reports import participants as P  # noqa: E402
from cozer.reports.common import participants_by_class  # noqa: E402
from cozer.reports.labels import get_labels  # noqa: E402
from cozer.reports.render import render_pdf_bytes  # noqa: E402


def _fits_portrait(pdf):
    doc = fitz.open(stream=pdf, filetype="pdf")
    for pg in doc:
        assert pg.rect.height > pg.rect.width
        maxx = max((ln["bbox"][2] for b in pg.get_text("dict")["blocks"]
                    for ln in b.get("lines", [])), default=0.0)
        assert maxx <= pg.rect.width - 5
    return "".join(pg.get_text() for pg in doc)

EVENT = os.path.join(REPO, "legacy", "events", "wc2000.coz")


def test_latex_to_html():
    assert latex_to_html(r"Ol\v{s}\'ak") == "Olšák"
    assert latex_to_html("313.04_4") == "313.04<sub>4</sub>"
    assert latex_to_html("406.05_{5.1}") == "406.05<sub>5.1</sub>"
    assert latex_to_html(r"A\\B") == "A<br>B"
    assert latex_to_html(r'J\"urgen') == "Jürgen"
    assert latex_to_html("a<b & c>d") == "a&lt;b &amp; c&gt;d"
    assert latex_to_html(r"x^{2}") == "x<sup>2</sup>"
    assert latex_to_html(r"\unknown y") == "y"        # control word gobbles the space
    assert latex_to_html("a--b---c") == "a–b—c"


def test_result_text_and_break_at_slash():
    r = {"points": 400, "place": 1, "avgspeed": 45.6, "maxlapspeed": 48.2,
         "lapinfo": (7, 0, 0), "notes": {}}
    assert _result_text(r, {}) == "45.6/&#8203;48.2"     # break only after the slash
    r2 = dict(r, lapinfo=(5, 0, 2))
    assert _result_text(r2, {}) == "45.6/&#8203;48.2/&#8203;5L"
    leg = {}
    r3 = {"points": -1, "place": -1, "avgspeed": 0, "maxlapspeed": 0,
          "lapinfo": (0, 0, 0), "notes": {"DQ": ["313.04_4"]}}
    out = _result_text(r3, leg)
    assert "DQ<sup>1</sup>" in out and leg               # note code + footnote registered


def test_report_output_paths():
    import os
    import tempfile
    from cozer.reports.output import report_stem, report_dir, report_output_paths
    assert report_stem("Full Final") == "full_final"
    ev = os.path.join("events", "demo", "sample.cozj")
    assert report_dir(ev) == os.path.abspath(os.path.join("events", "demo", "sample.reports"))
    latest, posting = report_output_paths(ev, "Intermediate", "0726-1432")
    d = report_dir(ev)
    assert latest == os.path.join(d, "intermediate.pdf")
    assert posting == os.path.join(d, "postings", "intermediate_0726-1432.pdf")
    # unsaved event -> a temp dir, so viewing works before the first save
    assert report_dir(None) == os.path.join(tempfile.gettempdir(), "cozer-reports")


def test_result_text_renders_209_codes():
    """A 2026 event stores §209 outcome codes directly; the report prints them in
    the result cell and the legend (backward-compatible: whatever is stored)."""
    from cozer.reports.final import _result_text, _legend_html
    from cozer.reports.labels import get_labels
    labels = get_labels({})
    for code, label in [("DSQ", "Disqualified"), ("DNS", "Did not start"),
                        ("DNF", "Did not finish"), ("ACC", "Accident")]:
        leg = {}
        r = {"points": -1, "place": -1, "avgspeed": 0, "maxlapspeed": 0,
             "lapinfo": (0, 0, 0), "notes": {code: ["311.01.4"]}}
        assert "%s<sup>1</sup>" % code in _result_text(r, leg)
        assert "%s = %s" % (code, label) in _legend_html(leg, labels)


def test_full_final_assembly_matches_core():
    ed = read_legacy_coz(EVENT)
    ss = ed.get("scoringsystem", [])
    rec = ed["record"]
    model = build_full_final(ed)
    assert model["orientation"] == "landscape" and model["tables"]
    for t in model["tables"]:
        cls = t["class"]          # wc2000 classes are unsuffixed, so getclass is identity
        heats = t["heats"]
        res = {h: analyze(h, copy.deepcopy(rec[cls][h]), ss) for h in heats}
        sumres = sumanalyze(heats, res, _sheats(ed, cls, len(heats)))
        order = getsumresorder(sumres)
        assert [row["id"] for row in t["rows"]] == [str(pid) for pid in order]
        for row in t["rows"]:
            pid = row["id"]
            # find the sumres entry by string id
            sr = next(sumres[k] for k in sumres if str(k) == pid)
            if sr["place"] > 0:
                assert row["place"] == str(sr["place"])
                assert row["sumpoints"] == str(sr["points"])


# --- UIM 209 DNQ tail (qualification -> finals report; §5.1 step 4) ---------------

def _qh(fast, slow):
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}
    return [info, {fast: [(1, 20.0)] * 3, slow: [(1, 25.0)] * 3}]


def _finals_heat(order):
    """A 3-lap circuit heat; boats finish in the given order (first = fastest)."""
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}
    return [info, {b: [(1, 20.0 + i)] * 3 for i, b in enumerate(order)}]


def _qual_finals_event(finals_heat):
    """C/Q qualification (10,30 primary; 20 repechage; 40 DNQ) feeding a C final."""
    classes = [["", "C/Q", "3*(1000):1!qualification[1,1,1]"], ["", "C", "2*(3*1000):1"]]
    parts = [["", "N%s" % b, "S%s" % b, "FIN", "C", str(b)] for b in (10, 20, 30, 40)]
    record = {"C/Q": {"1q": _qh("10", "20"), "2q": _qh("30", "40"), "3q": _qh("20", "40")},
              "C": {"1": finals_heat}}
    return {"kind": "event", "title": "Q", "classes": classes, "participants": parts,
            "record": record, "scoringsystem": [400, 300, 225], "rules": []}


def _finals_table(model):
    return next(t for t in model["tables"] if t["heats"] == ["1"])   # the C final (not the qheats)


def test_final_report_dnq_tail_lists_non_qualifiers():
    ed = _qual_finals_event(_finals_heat(["10", "30", "20"]))       # finalists race the final
    t = _finals_table(build_full_final(ed))
    ids = [r["id"] for r in t["rows"]]
    assert ids[:3] == ["10", "30", "20"]           # finalists classified, in finishing order
    assert ids[-1] == "40"                          # the sole non-qualifier, appended below
    dnq = t["rows"][-1]
    assert dnq["best"] == "DNQ" and dnq["sumpoints"] == "-" and dnq["place"] == ""


def test_final_report_dnq_boat_in_record_moves_to_tail_not_duplicated():
    # finals record materialized with ALL participants: boat 40 (DNQ) sits there as a DNS
    heat = _finals_heat(["10", "30", "20"])
    heat[1]["40"] = []                              # no crossings -> DNS placeholder
    t = _finals_table(build_full_final(_qual_finals_event(heat)))
    ids = [r["id"] for r in t["rows"]]
    assert ids.count("40") == 1                      # listed once...
    assert ids[-1] == "40" and t["rows"][-1]["best"] == "DNQ"   # ...in the tail, not the body
    assert set(ids[:-1]) == {"10", "30", "20"}       # body = finalists only (40 moved out)


def test_final_report_dnq_tail_in_short_report_too():
    t = _finals_table(build_short_final(_qual_finals_event(_finals_heat(["10", "30", "20"]))))
    assert t["rows"][-1]["id"] == "40" and t["rows"][-1]["best"] == "DNQ"


def test_final_report_subtitle_names_the_phase_kind():
    # an all-classes report over a qualification event spans two phases -> both named
    model = build_full_final(_qual_finals_event(_finals_heat(["10", "30", "20"])))
    assert model["subtitle"] == "Qualification · Final"
    assert '<div class="report-subtitle">Qualification · Final</div>' in full_final_html(model)
    # a per-phase report (select the final) names just that phase
    assert build_full_final(_qual_finals_event(_finals_heat(["10", "30", "20"])),
                            classes=["C"])["subtitle"] == "Final"


def test_final_report_subtitle_localized_and_timetrial():
    # a synthetic time-trial-only event -> "Time Trial"
    info = {"course": [1000], "sheats": 1, "duration": None}
    tt = {"kind": "event", "title": "TT", "scoringsystem": [400, 300, 225], "rules": [],
          "classes": [["", "C/T", "1*(1000):1"]],
          "participants": [["", "N", "S", "FIN", "C", "10"]],
          "record": {"C/T": {"1t": [info, {"10": [(1, 20.0)]}]}}}
    assert build_full_final(tt)["subtitle"] == "Time Trial"
    # a real merged event names both phases present, joined with ' · '
    merged = read_legacy_coz(os.path.join(REPO, "legacy", "events", "WC 2024_Time_trials.coz"))
    assert build_full_final(merged)["subtitle"] == "Time Trial · Final"
    # localized (Estonian): a circuit final -> "Finaal"
    et = read_legacy_coz(EVENT); et.setdefault("configure", {})["language"] = "Estonian"
    assert build_short_final(et)["subtitle"] == "Finaal"


def test_legacy_final_report_is_byte_faithful_no_subtitle_no_dnq():
    from cozer.reports.final import build_full_final_legacy
    ed = _qual_finals_event(_finals_heat(["10", "30", "20"]))
    model = build_full_final_legacy(ed)
    assert model["subtitle"] == ""                             # legacy: no phase-kind subtitle
    t = _finals_table(model)
    assert "DNQ" not in [r["best"] for r in t["rows"]]         # legacy: no DNQ tail
    assert "40" not in [r["id"] for r in t["rows"]]            # DNQ boat not injected


def test_final_report_no_dnq_tail_without_qualification():
    # a plain circuit class (no /Q sibling) is unchanged -- no DNQ rows
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}
    ed = {"kind": "event", "title": "X", "scoringsystem": [400, 300, 225], "rules": [],
          "classes": [["", "C", "2*(3*1000):1"]],
          "participants": [["", "N", "S", "FIN", "C", str(b)] for b in (10, 20)],
          "record": {"C": {"1": [info, {"10": [(1, 20.0)] * 3, "20": [(1, 25.0)] * 3}]}}}
    t = next(t for t in build_full_final(ed)["tables"] if t["class"] == "C")
    assert [r["id"] for r in t["rows"]] == ["10", "20"]         # both scored, no DNQ tail
    assert all(r["best"] != "DNQ" for r in t["rows"])


def test_report_skips_unrecorded_heat_in_heat_map():
    """A heat_map naming a heat absent from the record -- a stale tree selection
    (heat checked, then its record cleared) or a programmatic caller -- must degrade
    gracefully: skip the missing heat instead of KeyError on record[cl][h]. Covers
    the four heat_map-driven builders (endurance shares the identical filter)."""
    from cozer.reports.intermediate import build_intermediate
    from cozer.reports.laps import build_laps_protocol
    ed = read_legacy_coz(EVENT)
    rec = ed["record"]
    cl = sorted(rec.keys())[0]
    real = sorted(rec[cl].keys())
    BOGUS = "__nope__"

    # a real heat mixed with a bogus unrecorded one -> builds, using only the real heat
    hm = {cl: [real[0], BOGUS]}
    ff = build_full_final(ed, classes=[cl], heat_map=hm)
    assert ff["tables"] and all(BOGUS not in t["heats"] for t in ff["tables"])
    assert build_short_final(ed, classes=[cl], heat_map=hm)["tables"]
    im = build_intermediate(ed, classes=[cl], heat_map=hm)
    assert im["tables"] and all(t["heat"] != BOGUS for t in im["tables"])
    lp = build_laps_protocol(ed, classes=[cl], heat_map=hm)
    assert lp["tables"] and all(t["heat"] != BOGUS for t in lp["tables"])

    # an all-unrecorded selection -> the class is skipped entirely, still no crash
    hm2 = {cl: [BOGUS]}
    for build in (build_full_final, build_short_final, build_intermediate, build_laps_protocol):
        assert build(ed, classes=[cl], heat_map=hm2)["tables"] == []


def test_full_final_renders_landscape_and_fits():
    ed = read_legacy_coz(EVENT)
    pdf = render_pdf_bytes(full_final_html(build_full_final(ed)))
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert doc.page_count >= 1
    for pg in doc:
        assert pg.rect.width > pg.rect.height           # landscape
        maxx = max((ln["bbox"][2] for b in pg.get_text("dict")["blocks"]
                    for ln in b.get("lines", [])), default=0.0)
        assert maxx <= pg.rect.width - 5                # nothing overflows the page
    assert "Final Results" in "".join(pg.get_text() for pg in doc)


def test_short_final_portrait_and_fits():
    ed = read_legacy_coz(EVENT)
    model = build_short_final(ed)
    assert model["orientation"] == "portrait" and model["full"] is False
    text = _fits_portrait(render_pdf_bytes(short_final_html(model)))
    assert "Final Results" in text


def test_participants_report():
    ed = read_legacy_coz(EVENT)
    model = P.build_participants(ed)
    by = participants_by_class(ed)
    assert model["tables"] and all(len(t["rows"]) == len(by[t["class"]]) for t in model["tables"])
    text = _fits_portrait(render_pdf_bytes(P.participants_html(model)))
    assert "Dubinin" in text and "Registered competitors" in text


def test_checklist_landscape():
    ed = read_legacy_coz(EVENT)
    model = P.build_checklist(ed)
    assert model["orientation"] == "landscape"
    doc = fitz.open(stream=render_pdf_bytes(P.checklist_html(model)), filetype="pdf")
    assert doc[0].rect.width > doc[0].rect.height
    assert "Meeting" in "".join(pg.get_text() for pg in doc)


def test_localization():
    assert get_labels({})["FinalResults"] == "Final Results"
    et = {"configure": {"language": "Estonian"}, "record": {}, "classes": [],
          "participants": [], "scoringsystem": []}
    assert get_labels(et)["FinalResults"] == "Tulemused"
    assert build_short_final(et)["heading"] == "Tulemused"


def test_intermediate_report():
    from cozer.reports.intermediate import build_intermediate, intermediate_html
    ed = read_legacy_coz(EVENT)
    model = build_intermediate(ed)
    assert model["tables"]
    text = _fits_portrait(render_pdf_bytes(intermediate_html(model)))
    assert "Intermediate Results" in text


def test_laps_protocol_report():
    from cozer.reports.laps import build_laps_protocol, laps_protocol_html
    ed = read_legacy_coz(EVENT)
    model = build_laps_protocol(ed)
    assert model["tables"]
    text = _fits_portrait(render_pdf_bytes(laps_protocol_html(model)))
    assert "Laps Counter Protocol" in text


def test_endurance_final_report():
    from cozer.reports.endurance import build_endurance_final, endurance_final_html, sec2time
    assert sec2time(3661) == "01:01:01" and sec2time(None) == "-"
    assert sec2time(-30.0).startswith("- ")
    ed = read_legacy_coz(os.path.join(REPO, "legacy", "events", "Endurance_EC1_Parnu_2013.coz"))
    model = build_endurance_final(ed)
    assert model["orientation"] == "landscape" and model["tables"]
    doc = fitz.open(stream=render_pdf_bytes(endurance_final_html(model)), filetype="pdf")
    for pg in doc:
        assert pg.rect.width > pg.rect.height
        maxx = max((ln["bbox"][2] for b in pg.get_text("dict")["blocks"]
                    for ln in b.get("lines", [])), default=0.0)
        assert maxx <= pg.rect.width - 5
    assert "Total Laps" in "".join(pg.get_text() for pg in doc)


# --- coverage sweep -------------------------------------------------------

@pytest.mark.parametrize("render_name,event", [
    ("render_full_final", "wc2000"), ("render_short_final", "wc2000"),
    ("render_participants", "wc2000"), ("render_checklist", "wc2000"),
    ("render_intermediate", "wc2000"), ("render_laps_protocol", "wc2000"),
    ("render_endurance_final", "Endurance_EC1_Parnu_2013"),
])
def test_render_wrappers_write_valid_pdf(tmp_path, render_name, event):
    import cozer.reports as R
    ed = read_legacy_coz(os.path.join(REPO, "legacy", "events", event + ".coz"))
    out = str(tmp_path / (render_name + ".pdf"))
    getattr(R, render_name)(ed, out)
    assert os.path.getsize(out) > 500
    fitz.open(out).close()


def test_latex_to_html_more():
    from cozer.reports.latexish import latex_to_html
    assert latex_to_html(r"\ss") == "ß"
    assert latex_to_html(r"\u{g}") == "ğ"
    assert latex_to_html(r"\H{o}") == "ő"
    assert latex_to_html(r"\r{u}") == "ů"
    assert latex_to_html(r"\c{c}") == "ç"
    assert latex_to_html(r"M \& M") == "M &amp; M"
    assert latex_to_html(r"a\,b") == "a b"
    assert latex_to_html("x^2") == "x<sup>2</sup>"
    assert latex_to_html(r"\v{q}") == "q"        # unmapped accent -> bare letter
    assert latex_to_html(r"\'{") == ""           # unclosed brace argument


def test_common_helpers():
    from cozer.reports.common import get_fullname, sheats_for, esc, display
    assert get_fullname("A;B", "X;Y") == "A X; B Y"
    assert get_fullname("John", "Doe") == "John Doe"
    get_fullname("A;B", "X")                       # exercises last-padding branch
    get_fullname("A", "X;Y")                       # exercises first-padding branch
    assert sheats_for({"classes": []}, "Z", 3) == 3
    assert esc("<&>") == "&lt;&amp;&gt;"
    assert display("313.04_4") == "313.04<sub>4</sub>"


def test_get_labels_bad_input():
    assert get_labels("not a dict")["Place"] == "Place"        # exception -> English
    assert get_labels({"configure": {"language": "Klingon"}})["Place"] == "Place"


def test_letters():
    from cozer.reports.letters import (
        build_info_letter, info_letter_html, registration_letter_html, build_registration_letter,
    )
    ed = read_legacy_coz(EVENT)
    # info letter (English)
    text = _fits_portrait(render_pdf_bytes(info_letter_html(build_info_letter(ed))))
    assert "Dear Competitor" in text and "Other Information" in text
    # info letter (Estonian)
    et = dict(ed, configure={"language": "Estonian"})
    et_html = info_letter_html(build_info_letter(et))
    assert "Lugupeetud" in et_html and "Muu informatsioon" in et_html
    # registration letter (bilingual entry form)
    reg = _fits_portrait(render_pdf_bytes(registration_letter_html(build_registration_letter(ed))))
    assert "ENTRY" in reg and "DRIVER" in reg and "Perekonnanimi" in reg


def test_intermediate_timetrial_and_multidriver():
    from cozer.reports.intermediate import build_intermediate, intermediate_html
    # A time-trial is a /T class (get_allowed_heats only permits a '1t' heat under a
    # /T class); intermediate now reads the kind from the phase (phase.kind ==
    # "timetrial"), so the class must carry the /T suffix, not just a 't' heat id.
    ed = {
        "configure": {"language": "English"}, "scoringsystem": [10, 5, 3],
        "classes": [["x", "TT/T", "2*(2*1000):1"]],
        "participants": [["x", "A;B", "One;Two", "EST", "TT", "1"],
                         ["x", "C", "Three", "FIN", "TT", "2"]],
        "record": {"TT/T": {"1t": [{"course": [1000, 1000], "racetime": 1000.0},
                                   {"1": [(1, 20.0), (1, 21.0)], "2": [(1, 22.0)]}]}},
    }
    html = intermediate_html(build_intermediate(ed))
    assert "Lap Time" in html                      # time-trial column header
    assert "One" in html and "Two" in html         # multi-driver rows
    # UIM 305.04.02 best-lap TIME: boat 1's fastest lap is 20s (not the last, 21s);
    # boat 2 ran a single lap (22s) -> it now shows a time (used to render "-", laptime=0).
    assert "20.000" in html and "22.000" in html
    assert "21.000" not in html                    # the slower lap is not the reported time


def test_intermediate_qualification_shows_qdnq():
    # A qualification qheat: the Intermediate report (printed after each qheat) marks the top-N
    # finishers Q and the rest DNQ (the per-qheat advancement, UIM §4.1 / 209).
    from cozer.reports.intermediate import build_intermediate, intermediate_html
    from cozer.native import to_native
    ed = to_native({
        "configure": {"language": "English"}, "scoringsystem": [400, 300, 225], "rules": [], "races": [],
        "participants": [["", "A", "x", "EST", "F 500", "1"], ["", "B", "y", "FIN", "F 500", "2"],
                         ["", "C", "z", "SWE", "F 500", "3"]],
        "classes": [["", "F 500/Q", "1*(3*1000):1!qualification[2]"], ["", "F 500", "4*(1400):3"]],
        "record": {"F 500/Q": {"1q": [{"course": [1000, 1000, 1000], "racetime": 1000.0}, {
            "1": [(1, 20.0), (1, 20.0), (1, 20.0)], "2": [(1, 21.0), (1, 21.0), (1, 21.0)],
            "3": [(1, 22.0), (1, 22.0), (1, 22.0)]}]}},
    })
    m = build_intermediate(ed)
    t = next(x for x in m["tables"] if x.get("isqual"))
    assert t["qcount"] == 2                                 # top 2 of the qheat qualify
    assert {r["id"]: r["status"] for r in t["rows"]} == {"1": "Q", "2": "Q", "3": "DNQ"}
    html = intermediate_html(m)
    assert "Q/DNQ" in html and "DNQ" in html               # the status column renders
