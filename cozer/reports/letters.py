"""Info Letter (spectator-bio collection form) and Registration Letter
(bilingual entry form). Static forms ported from the legacy
``\\cozerinfoletter`` / ``\\cozerregistrationletter`` macros. The Info Letter is
localized; the Registration Letter is inherently bilingual (English/Estonian).
"""
from cozer.reports.common import esc, display, meta_of, document_html
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf

# Info-letter content per language. Field entries are (label, blank-space "ex").
_INFO = {
    "English": {
        "greeting": "Dear Competitor,",
        "intro": ("We kindly ask you to provide us with the following information, so that we "
                  "can introduce you to spectators during the competition. If you have some "
                  "interesting facts of your life, please describe them under "
                  "“Other Information”."),
        "fields": [("First Name", 1), ("Surname", 1), ("Date and Place of Birth", 1),
                   ("Marital Status", 1), ("Children", 1), ("Occupation", 1),
                   ("Team, Club, Country", 2), ("Best Results", 8), ("Hobbies", 7),
                   ("Other Information", 10)],
        "closing": ["Thank you for your help and we wish you pleasant starts!",
                    "Organizers of the event"],
    },
    "Estonian": {
        "greeting": "Lugupeetud võistleja,",
        "intro": ("Palume Teil edastada meile järgmine teave, et saaksime Teid võistluse ajal "
                  "pealtvaatajatele tutvustada. Kui Teie elus on huvitavaid fakte, kirjeldage "
                  "neid palun lahtris „Muu informatsioon“."),
        "fields": [("Eesnimi", 1), ("Perekonnanimi", 1), ("Sünnipäev ja sünnikoht", 1),
                   ("Perekonnaseis", 1), ("Lapsed", 1), ("Amet", 1),
                   ("Võistkond, Klubi, Riik", 2), ("Parimad tulemused", 8), ("Hobid", 7),
                   ("Muu informatsioon", 10)],
        "closing": ["Täname abi eest ja soovime meeldivaid starte!",
                    "Võistluse korraldajad"],
    },
}

_LETTER_CSS = (
    "<style>.letter{font-size:11pt;margin:.25cm 0} "
    ".ffield{margin:.15cm 0} .flabel{font-weight:bold;font-size:11pt} "
    ".fbox{border-bottom:1px solid #888;margin-top:3px} "
    ".regform{border-collapse:collapse;width:100%;table-layout:fixed;margin:.15cm 0} "
    ".regform td{border:1px solid #333;padding:5px;font-size:10pt;vertical-align:top} "
    ".regform td.blank{height:.7cm} .regform td.rg{vertical-align:middle;background:#eee;font-weight:bold} "
    ".decl{border:1px solid #333;padding:6px;font-size:9pt;margin-top:.2cm} "
    ".sig{margin-top:.35cm;font-weight:bold} .sigline{border-bottom:1px solid #333;height:1cm} "
    ".na{margin-top:.35cm;font-weight:bold}</style>"
)


def _lang(eventdata):
    try:
        return eventdata.get("configure", {}).get("language", "English")
    except Exception:
        return "English"


def build_info_letter(eventdata):
    content = _INFO.get(_lang(eventdata), _INFO["English"])
    return {"meta": meta_of(eventdata), "labels": get_labels(eventdata),
            "orientation": "portrait", "content": content}


def info_letter_html(model):
    c = model["content"]
    body = ['<p class="letter">%s</p>' % display(c["greeting"]),
            '<p class="letter">%s</p>' % display(c["intro"])]
    for label, ex in c["fields"]:
        body.append('<div class="ffield"><span class="flabel">%s:</span>'
                    '<div class="fbox" style="height:%.2fcm"></div></div>'
                    % (display(label), max(0.6, ex * 0.35)))
    for line in c["closing"]:
        body.append('<p class="letter">%s</p>' % display(line))
    return _LETTER_CSS + document_html(model["orientation"], model["labels"], model["meta"], "", body)


# Registration form rows: (group | None-continuation, English term, Estonian term)
_REG_ROWS = [
    ("ENTRY", "Starting no", "Võistleja nr."),
    (None, "Class", "Klass"),
    (None, "Country", "Riik"),
    ("DRIVER", "Surname", "Perekonnanimi"),
    (None, "First name", "Eesnimi"),
    (None, "Date of birth", "Sünniaeg"),
    (None, "Address", "Aadress"),
    (None, "Club", "Klubi"),
    (None, "Blood group", "Veregrupp"),
    ("BOAT", "Manufacture", "Valmistaja"),
    (None, "In year", "Valmistamise aasta"),
    ("MOTOR", "Manufacture", "Valmistaja"),
    ("LICENSE", "No:", "Litsents"),
    ("CERTIFICATE OF MEASURE", "No:", "Mõõdukiri"),
    ("INSURANCE POLICY", "No:", "Kindlustuspoliis"),
]
_DECL_EN = ("I declare that the above is right. I declare that I will follow the rules of "
            "U.I.M. and the regulations of this competition and the arrangements of the "
            "organizers. I take part in the competition at my own responsibility and risk.")
_DECL_ET = ("Kinnitan, et minu antud informatsioon on õige ja luban juhinduda U.I.M.-i "
            "määrustest, selle võistluse juhendist ja organisaatorite korraldustest. "
            "Ma võtan võistlustest osa omal vastutusel ja riskil.")


def build_registration_letter(eventdata):
    return {"meta": meta_of(eventdata), "labels": get_labels(eventdata), "orientation": "portrait"}


def registration_letter_html(model):
    trs = []
    idx = 0
    while idx < len(_REG_ROWS):
        span, j = 1, idx + 1
        while j < len(_REG_ROWS) and _REG_ROWS[j][0] is None:
            span += 1
            j += 1
        for k in range(idx, j):
            g, en, et = _REG_ROWS[k]
            gcell = '<td class="rg" rowspan="%d">%s</td>' % (span, esc(g)) if k == idx else ""
            trs.append('<tr>%s<td>%s</td><td class="blank"></td><td>%s</td></tr>'
                       % (gcell, esc(en), display(et)))
        idx = j
    table = ('<table class="regform"><colgroup><col style="width:20%"><col style="width:22%">'
             '<col style="width:36%"><col style="width:22%"></colgroup>'
             + "".join(trs) + "</table>")
    decl = '<div class="decl">%s</div><div class="decl">%s</div>' % (esc(_DECL_EN), display(_DECL_ET))
    sig = '<div class="sig">Signature / Allkiri</div><div class="sigline"></div>'
    na = ('<div class="na">Approved by driver\'s National Authority:</div>'
          '<table class="regform"><colgroup><col style="width:30%"><col style="width:70%"></colgroup>'
          '<tr><td>NA:</td><td class="blank"></td></tr>'
          '<tr><td>Signed by:</td><td class="blank"></td></tr>'
          '<tr><td>Signature:</td><td class="blank"></td></tr></table>')
    return _LETTER_CSS + document_html(model["orientation"], model["labels"], model["meta"],
                                       "", [table, decl, sig, na])


def render_info_letter(eventdata, out_path):
    model = build_info_letter(eventdata)
    html = info_letter_html(model)
    render_pdf(html, out_path)
    return model, html


def render_registration_letter(eventdata, out_path):
    model = build_registration_letter(eventdata)
    html = registration_letter_html(model)
    render_pdf(html, out_path)
    return model, html
