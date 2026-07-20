#!/usr/bin/env python
"""Build the sample event `sample_regatta_2026_legacy.cozj`.

A realistic two-class sample in the CURRENT ("legacy") phase convention — phases are
modelled with class-name suffixes (`/T` time-trial, `/Q` qualification), which is what
today's readers turn into phases (`race_kind`/`getclass`/`_catalog_phases`). The event
uses the new `.cozj` file format and the 2026 UIM rulesets; only the phase *encoding*
is legacy (a suffix-free new-convention sample waits on the new-format authoring — hence
the `_legacy` in the filename).

Classes (base names as in the 2026 ruleset catalogue — `GT15`, `F 500`):
  GT15   : time-trial (practice) -> finals (2 heats x 5 laps)
  F 500  : time-trial (solo runs) -> qualification -> finals (3 heats x 8 laps)

State: waiting for the first time-trial run — no heats recorded (`record == {}`).

Run:  /home/pearu/miniconda3/envs/cozer/bin/python samples/build_sample_legacy.py
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.store import read_legacy_coz, loads, dumps            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "sample_regatta_2026_legacy.cozj")
NAT = re.compile(r"^[A-Z]{3}$")            # clean 3-letter nationality codes only


def fix(s):
    """Recover UTF-8 from a latin-1-decoded legacy pickle string (e.g. 'Lääne')."""
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


# --- participants ---------------------------------------------------------------
def gt15_participants():
    """The 9 real GT-15 drivers from the 2025 Timecolors Cup, re-homed to base 'GT15'."""
    ed = read_legacy_coz(os.path.join(REPO, "legacy/events/Timecolors Cup 2025 EMV III 1.coz"))
    out = []
    for p in ed["participants"]:
        if len(p) > 5 and p[4] == "GT-15":
            out.append(["", fix(p[1]), fix(p[2]), p[3], "GT15", str(p[5])])
    return out


def f500_participants(n=18):
    """A realistic F 500 field for a qualification phase: n real drivers drawn from the
    whole legacy corpus (real names + clean nationality codes), given distinct numbers.
    (The corpus has only 3 actual F-500 entries — too few to qualify — so the field is
    seeded from real drivers across the corpus; this is a synthetic sample, not a record.)"""
    pool = {}
    for path in sorted(glob.glob(os.path.join(REPO, "legacy/events/*.coz"))):
        try:
            ed = read_legacy_coz(path)
        except Exception:
            continue
        for p in ed.get("participants", []):
            if len(p) > 5 and p[1] and NAT.match(str(p[3])):
                key = (fix(p[1]), fix(p[2]), p[3])
                pool.setdefault(key, key)
    drivers = sorted(pool)[:n]
    # distinct, realistic-looking hull numbers
    numbers = [1, 3, 4, 7, 9, 11, 14, 17, 21, 24, 27, 33, 41, 47, 55, 63, 70, 88, 91, 99]
    return [["", first, last, nat, "F 500", str(numbers[i])]
            for i, (first, last, nat) in enumerate(drivers)]


# --- rules: merge the 2026 general + circuit rulesets ---------------------------
def rules_2026():
    seen, merged = set(), []
    for rs in ("uim_general_2026", "uim_circuit_2026"):
        with open(os.path.join(REPO, "cozer/rulesets/%s.cozj" % rs), encoding="utf-8") as f:
            for r in loads(f.read()).get("rules", []):
                key = (r[1], str(r[2]).strip(), r[3])   # (code, rule-no, description)
                if key not in seen:
                    seen.add(key)
                    merged.append(list(r))
    return merged


def build():
    gt15 = gt15_participants()
    f500 = f500_participants()
    # classes: ['', name, pattern].  start-lap + N*lap = N+1 laps (see racepattern).
    classes = [
        ["", "GT15/T",  "1*(1100+25*1100):1"],                       # practice: best of many laps (305.04.02a)
        ["", "GT15",    "2*(1100+4*1100):2"],                        # finals: 2 heats x 5 laps
        ["", "F 500/T", "1*(1000+3*1500):1"],                        # solo runs: warm-up + 2 timed + safety = 4 laps (305.04.02b)
        ["", "F 500/Q", "3*(1000+4*1500):3!qualification[4,4,4]"],   # qheat1/qheat2 (top 4 each) + repechage (top 4); reduced 5-lap qheats
        ["", "F 500",   "3*(1000+7*1500):3"],                        # finals: 3 heats x 8 laps
    ]
    sheats = {"GT15/T": 1, "GT15": 2, "F 500/T": 1, "F 500/Q": 3, "F 500": 3}
    eventdata = {
        "title": "Sample Regatta 2026 (GT15 & F 500)",
        "venue": "Lake Harku, Tallinn, Estonia",
        "date": "2026-08-15",
        "officer": "Madis Kalder",
        "secretary": "Tiia Aasaru",
        "configure": {"language": "English", "id_but_size": 40, "id_but_textsize": 14},
        "scoringsystem": [400, 300, 225, 169, 127, 95, 71, 53, 40, 30, 22, 17, 13, 9, 7, 5, 4, 3, 2, 1, 0],
        "classes": classes,
        "sheats": sheats,
        "participants": gt15 + f500,
        "rules": rules_2026(),
        "record": {},        # waiting for the first time-trial run -- no heats yet
        "races": [],
        "prevorder": {},
        "savechecked": {},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(dumps(eventdata))
    print("wrote %s  (GT15=%d, F 500=%d participants, %d rules)"
          % (OUT, len(gt15), len(f500), len(eventdata["rules"])))
    return eventdata


if __name__ == "__main__":
    build()
