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


def test_intermediate_timetrial_and_multidriver():
    from cozer.reports.intermediate import build_intermediate, intermediate_html
    ed = {
        "configure": {"language": "English"}, "scoringsystem": [10, 5, 3],
        "classes": [["x", "TT", "2*(2*1000):1"]],
        "participants": [["x", "A;B", "One;Two", "EST", "TT", "1"],
                         ["x", "C", "Three", "FIN", "TT", "2"]],
        "record": {"TT": {"1t": [{"course": [1000, 1000], "racetime": 1000.0},
                                 {"1": [(1, 20.0), (1, 21.0)], "2": [(1, 22.0)]}]}},
    }
    html = intermediate_html(build_intermediate(ed))
    assert "Lap Time" in html                      # time-trial column header
    assert "One" in html and "Two" in html         # multi-driver rows
