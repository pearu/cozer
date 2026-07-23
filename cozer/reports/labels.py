"""Localized report labels, extracted verbatim from the legacy
``data/English_cozer.tex`` / ``data/Estonian_cozer.tex`` macros.

Language is taken from ``eventdata['configure']['language']`` (as set by the
legacy File>Language menu), defaulting to English.
"""

LABELS = {
    "English": {
        "OfficeroftheDay": "Officer of the Day", "SecretaryoftheRace": "Secretary of the Race",
        "UIMCommissioner": "UIM Sports Commissioner", "PostedAt": "Posted at", "PrintedOn": "Printed on",
        "Page": "Page", "Registeredcompetitors": "Registered competitors",
        "IntermediateResults": "Intermediate Results", "FinalResults": "Final Results",
        "PracticeTimeTrial": "Practice / Time-trial",
        "NoTimeTrialData": "No time-trial results recorded for the selected classes.",
        "PenaltyNotes": "Notes",
        "DriversMeetingChecklist": "Drivers Meeting Checklist",
        "LapsCounterProtocol": "Laps Counter Protocol", "Inspection": "Inspection",
        "Meeting": "Meeting", "Class": "Class", "Name": "Name", "Country": "Country",
        "RaceNo": "Race No.", "Heat": "Heat", "Heats": "Heats", "Place": "Place",
        "From": "From", "No": "No.", "Res": "Res.", "LapTime": "Lap Time", "Qualify": "Q/DNQ",
        "Repechage": "Rep.", "Nationality": "Nat.",   # short header: the column holds a 3-char code
        "Results": "Results", "Pts": "Pts.", "Points": "Points", "Starttime": "Start time",
        "Summary": "Summary", "Lp": "L", "Lap": "Lap", "Start": "Start", "None": "None",
        "LapCountNote": "A lap count (e.g. /5L) is shown only for a boat short of the full distance; "
                        "a boat with no lap count completed all required laps",
        "TimeNote": "Result = total race time [M:SS.d]",
        "ResNote": "Result = AverSpeed / MaxLapSpeed [km/h]",
        "LapTimeNote": "Lap Time = best full lap [s]",   # time-trial footer (305.04.02)
        "QualifyNote": "Q = qualified, DNQ = did not qualify",   # qualification Q/DNQ key
        "TotalLapsTime": "Total Laps Time", "TotalLaps": "Total Laps",   # endurance
        "Lostalap": "Lost a lap", "LostTwoLaps": "Lost two laps", "Penaltylap": "Penalty lap",
        "FivePenaltylaps": "5 penalty laps", "EightPenaltylaps": "8 penalty laps",
        "TenPenaltylaps": "10 penalty laps", "ThreePenaltylaps": "3 penalty laps",
        "FourPenaltylaps": "4 penalty laps", "FifteenPenaltylaps": "15 penalty laps",
        "Didntstart": "Didn't start",
        "Interruption": "Interruption", "Disqualif": "Disqualif.", "YellowCard": "Yellow Card",
        "RedCard": "Red Card", "BlueCard": "Blue Card", "NotClassified": "Not classified",
        "LoseTwoPositions": "Lose two positions", "Note": "Note", "Qualified": "Qualified",
        "Notqualified": "Not qualified",
        "DidNotStart": "Did not start", "DidNotFinish": "Did not finish",
        "DidNotRestart": "Did not restart", "Disqualified": "Disqualified",
        "Accident": "Accident", "DidNotQualify": "Did not qualify",
        "PhaseTimeTrial": "Time Trial", "PhaseQualification": "Qualification",
        "PhaseFinal": "Final", "PhaseEndurance": "Endurance",
    },
    "Estonian": {
        "OfficeroftheDay": "Peakohtunik", "SecretaryoftheRace": "Võistluste sekretär",
        "UIMCommissioner": "UIM spordikomissar", "PostedAt": "Postitatud", "PrintedOn": "Prinditud",   # ET verified by owner
        "Page": "Leht", "Registeredcompetitors": "Registreeritud võistlejad",
        "IntermediateResults": "Vahetulemused", "FinalResults": "Tulemused",
        "PracticeTimeTrial": "Treening / ajasõit",
        "NoTimeTrialData": "Valitud klassidele pole ajasõidu tulemusi salvestatud.",
        "PenaltyNotes": "Märkused",
        "DriversMeetingChecklist": "Võistlejate koosoleku kontrolltabel",
        "LapsCounterProtocol": "Ringilugeja protokoll", "Inspection": "Ülevaatus",
        "Meeting": "Koosolek", "Class": "Klass", "Name": "Nimi", "Country": "Linn",
        "RaceNo": "Võistlus nr.", "Heat": "Sõit", "Heats": "Sõidud", "Place": "Koht",
        "From": "Klubi", "No": "Nr.", "Res": "Tul.", "LapTime": "Ringi aeg", "Qualify": "Q/DNQ",
        "Repechage": "Rep.", "Nationality": "Rahvus",   # ET verified by owner
        "Results": "Tulemus", "Pts": "Pnkt.", "Points": "Punktid", "Starttime": "Stardi aeg",
        "Summary": "Kokkuvõte", "Lp": "R", "Lap": "Ring", "Start": "Start", "None": "-",
        "LapCountNote": "Ringide arv (nt /5L) näidatakse ainult paadil, kes ei läbinud täisdistantsi; "
                        "ringide arvuta paat läbis kõik nõutud ringid",
        "TimeNote": "Tulemus = koguaeg [M:SS.d]",
        "ResNote": "Tulemus = (Keskmine kiirus) / (Parim ringi kiirus) [km/h]",
        "LapTimeNote": "Ringi aeg = kiireim täisring [s]",   # ET verified by owner
        "QualifyNote": "Q = kvalifitseerus, DNQ = ei kvalifitseerunud",   # ET verified by owner
        "TotalLapsTime": "Koguaeg", "TotalLaps": "Ringe kokku",   # ET verified by owner
        "Lostalap": "Kaotas ringi", "LostTwoLaps": "Kaotas kaks ringi",
        "Penaltylap": "Trahviring", "FivePenaltylaps": "5 trahviringi",
        "EightPenaltylaps": "8 trahviringi", "TenPenaltylaps": "10 trahviringi",
        "ThreePenaltylaps": "3 trahviringi", "FourPenaltylaps": "4 trahviringi",
        "FifteenPenaltylaps": "15 trahviringi",
        "Didntstart": "Ei startinud", "Interruption": "Katkestas", "Disqualif": "Diskvalif.",
        "YellowCard": "Kollane kaart", "RedCard": "Punane kaart",
        "BlueCard": "Sinine kaart", "NotClassified": "Klassifitseerimata",
        "LoseTwoPositions": "Kaotab kaks kohta", "Note": "Märkus",
        "Qualified": "Kvalifitseerus", "Notqualified": "Ei kvalifitseerunud",
        "DidNotStart": "Ei startinud", "DidNotFinish": "Ei lõpetanud",
        "DidNotRestart": "Ei taasstartinud", "Disqualified": "Diskvalifitseeritud",
        "Accident": "Õnnetus", "DidNotQualify": "Ei kvalifitseerunud",
        # NOTE: Estonian phase-kind names are best-effort -- owner to verify/correct.
        "PhaseTimeTrial": "Ajasõit", "PhaseQualification": "Kvalifikatsioon",
        "PhaseFinal": "Finaal", "PhaseEndurance": "Kestvussõit",
    },
}

# Phase kind (race_kind) -> label key, and canonical display order for a report subtitle.
PHASE_KIND_LABEL = {"timetrial": "PhaseTimeTrial", "qualification": "PhaseQualification",
                    "circuit": "PhaseFinal", "endurance": "PhaseEndurance"}
_PHASE_KIND_ORDER = ("timetrial", "qualification", "circuit", "endurance")


def phase_kinds_subtitle(labels, kinds):
    """A report subtitle naming the phase kind(s) present (§10-E), in canonical order and
    localized; distinct kinds are joined with ' · '. Empty when no known kind is present."""
    seen = set(kinds)
    names = [labels[PHASE_KIND_LABEL[k]] for k in _PHASE_KIND_ORDER if k in seen]
    return " · ".join(names)

# record code -> label key (for note legends)
RECCODE_LABEL = {
    "LL": "Lostalap", "LL2": "LostTwoLaps", "PL": "Penaltylap", "PL5": "FivePenaltylaps",
    "PL8": "EightPenaltylaps", "PL10": "TenPenaltylaps", "PL3": "ThreePenaltylaps",
    "PL4": "FourPenaltylaps", "PL15": "FifteenPenaltylaps", "DS": "Didntstart",
    "IR": "Interruption", "DQ": "Disqualif", "YC": "YellowCard", "RC": "RedCard",
    "BC": "BlueCard", "NC": "NotClassified", "LP2": "LoseTwoPositions",
    # 2026 UIM §209 result outcome codes
    "DNS": "DidNotStart", "DNF": "DidNotFinish", "DNR": "DidNotRestart",
    "DSQ": "Disqualified", "ACC": "Accident", "DNQ": "DidNotQualify",
    "NT": "Note", "Q": "Qualified", "NQ": "Notqualified",
}

def get_labels(eventdata):
    lang = "English"
    try:
        lang = eventdata.get("configure", {}).get("language", "English")
    except Exception:
        pass
    return LABELS.get(lang, LABELS["English"])
