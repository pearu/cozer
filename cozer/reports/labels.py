"""Localized report labels, extracted verbatim from the legacy
``data/English_cozer.tex`` / ``data/Estonian_cozer.tex`` macros.

Language is taken from ``eventdata['configure']['language']`` (as set by the
legacy File>Language menu), defaulting to English.
"""

LABELS = {
    "English": {
        "OfficeroftheDay": "Officer of the Day", "SecretaryoftheRace": "Secretary of the Race",
        "Page": "Page", "Registeredcompetitors": "Registered competitors",
        "IntermediateResults": "Intermediate Results", "FinalResults": "Final Results",
        "DriversMeetingChecklist": "Drivers Meeting Checklist",
        "LapsCounterProtocol": "Laps Counter Protocol", "Inspection": "Inspection",
        "Meeting": "Meeting", "Class": "Class", "Name": "Name", "Country": "Country",
        "RaceNo": "Race No.", "Heat": "Heat", "Heats": "Heats", "Place": "Place",
        "From": "From", "No": "No.", "Res": "Res.", "LapTime": "Lap Time",
        "Results": "Results", "Pts": "Pts.", "Points": "Points", "Starttime": "Start time",
        "Summary": "Summary", "Lp": "L", "Lap": "Lap", "Start": "Start", "None": "None",
        "ResNote": "Result = AverSpeed / MaxLapSpeed [km/h]",
        "Lostalap": "Lost a lap", "LostTwoLaps": "Lost two laps", "Penaltylap": "Penalty lap",
        "FivePenaltylaps": "5 penalty laps", "EightPenaltylaps": "8 penalty laps",
        "TenPenaltylaps": "10 penalty laps", "Didntstart": "Didn't start",
        "Interruption": "Interruption", "Disqualif": "Disqualif.", "YellowCard": "Yellow Card",
        "RedCard": "Red Card", "Note": "Note", "Qualified": "Qualified",
        "Notqualified": "Not qualified",
    },
    "Estonian": {
        "OfficeroftheDay": "Peakohtunik", "SecretaryoftheRace": "Võistluste sekretär",
        "Page": "Leht", "Registeredcompetitors": "Registreeritud võistlejad",
        "IntermediateResults": "Vahetulemused", "FinalResults": "Tulemused",
        "DriversMeetingChecklist": "Võistlejate koosoleku kontrolltabel",
        "LapsCounterProtocol": "Ringilugeja protokoll", "Inspection": "Ülevaatus",
        "Meeting": "Koosolek", "Class": "Klass", "Name": "Nimi", "Country": "Linn",
        "RaceNo": "Võistlus nr.", "Heat": "Sõit", "Heats": "Sõidud", "Place": "Koht",
        "From": "Klubi", "No": "Nr.", "Res": "Tul.", "LapTime": "Ringi aeg",
        "Results": "Tulemus", "Pts": "Pnkt.", "Points": "Punktid", "Starttime": "Stardi aeg",
        "Summary": "Kokkuvõte", "Lp": "R", "Lap": "Ring", "Start": "Start", "None": "-",
        "ResNote": "Tulemus = (Keskmine kiirus) / (Parim ringi kiirus) [km/h]",
        "Lostalap": "Kaotas ringi", "LostTwoLaps": "Kaotas kaks ringi",
        "Penaltylap": "Trahviring", "FivePenaltylaps": "5 trahviringi",
        "EightPenaltylaps": "8 trahviringi", "TenPenaltylaps": "10 trahviringi",
        "Didntstart": "Ei startinud", "Interruption": "Katkestas", "Disqualif": "Diskvalif.",
        "YellowCard": "Kollane kaart", "RedCard": "Punane kaart", "Note": "Märkus",
        "Qualified": "Kvalifitseerus", "Notqualified": "Ei kvalifitseerunud",
    },
}

# record code -> label key (for note legends)
RECCODE_LABEL = {
    "LL": "Lostalap", "LL2": "LostTwoLaps", "PL": "Penaltylap", "PL5": "FivePenaltylaps",
    "PL8": "EightPenaltylaps", "PL10": "TenPenaltylaps", "DS": "Didntstart",
    "IR": "Interruption", "DQ": "Disqualif", "YC": "YellowCard", "RC": "RedCard",
    "NT": "Note", "Q": "Qualified", "NQ": "Notqualified",
}


def get_labels(eventdata):
    lang = "English"
    try:
        lang = eventdata.get("configure", {}).get("language", "English")
    except Exception:
        pass
    return LABELS.get(lang, LABELS["English"])
