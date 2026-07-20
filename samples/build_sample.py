#!/usr/bin/env python
"""Build the sample event `sample_regatta_2026.cozj` — a realistic two-class event in
the **suffix-free native schema (2)**: one class per base, phases as `{kind, pattern[,
qualifiers]}`, records keyed `record[base][kind][number]`. New `.cozj` format + 2026 UIM
rulesets; no legacy `/T`,`/Q` class or `t`/`q`/`r`/`R` heat suffixes anywhere.

Classes:
  GT15   : time-trial (practice) -> finals (2 heats x 5 laps)
  F 500  : time-trial (solo runs) -> qualification -> finals (3 heats x 8 laps)

State: waiting for the first time-trial run — no heats recorded (`record == {}`).

Run:  /home/pearu/miniconda3/envs/cozer/bin/python samples/build_sample.py
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.store import EventStore, dump_event                  # noqa: E402
from cozer.native import SCHEMA                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "sample_regatta_2026.cozj")
NAT = re.compile(r"^[A-Z]{3}$")            # clean 3-letter nationality codes only


def fix(s):
    """Recover UTF-8 from a latin-1-decoded legacy pickle string (e.g. 'Lääne')."""
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


def _read_legacy(path):
    from cozer.store import read_legacy_coz
    return read_legacy_coz(path)


# --- participants (real drivers from the legacy corpus; base class, no suffix) ------
def gt15_participants():
    """The 9 real GT-15 drivers from the 2025 Timecolors Cup, homed to base 'GT15'."""
    ed = _read_legacy(os.path.join(REPO, "legacy/events/Timecolors Cup 2025 EMV III 1.coz"))
    return [["", fix(p[1]), fix(p[2]), p[3], "GT15", str(p[5])]
            for p in ed["participants"] if len(p) > 5 and p[4] == "GT-15"]


def f500_participants(n=18):
    """A qualification-sized F 500 field: n real drivers from across the corpus (real
    names + clean nationality codes), given distinct numbers. (The corpus has only 3 real
    F-500 entries — too few to qualify — so it's seeded from real drivers; synthetic sample.)"""
    pool = {}
    for path in sorted(glob.glob(os.path.join(REPO, "legacy/events/*.coz"))):
        try:
            ed = _read_legacy(path)
        except Exception:
            continue
        for p in ed.get("participants", []):
            if len(p) > 5 and p[1] and NAT.match(str(p[3])):
                pool.setdefault((fix(p[1]), fix(p[2]), p[3]), None)
    drivers = sorted(pool)[:n]
    numbers = [1, 3, 4, 7, 9, 11, 14, 17, 21, 24, 27, 33, 41, 47, 55, 63, 70, 88, 91, 99]
    return [["", first, last, nat, "F 500", str(numbers[i])]
            for i, (first, last, nat) in enumerate(drivers)]


# --- rules: merge the 2026 general + circuit rulesets -------------------------------
def rules_2026():
    from cozer.store import loads
    seen, merged = set(), []
    for rs in ("uim_general_2026", "uim_circuit_2026"):
        with open(os.path.join(REPO, "cozer/rulesets/%s.cozj" % rs), encoding="utf-8") as f:
            for r in loads(f.read()).get("rules", []):
                key = (r[1], str(r[2]).strip(), r[3])
                if key not in seen:
                    seen.add(key)
                    merged.append(list(r))
    return merged


def build():
    # native classes: one per base, phases = {kind, pattern[, qualifiers]}.
    # start-lap + N*lap = N+1 laps (see racepattern).
    classes = [
        {"name": "GT15", "phases": [
            {"kind": "timetrial", "pattern": "1*(1100+25*1100):1"},   # practice, best of many laps (305.04.02a)
            {"kind": "circuit",   "pattern": "2*(1100+4*1100):2"},    # finals: 2 heats x 5 laps
        ]},
        {"name": "F 500", "phases": [
            {"kind": "timetrial",     "pattern": "1*(1000+3*1500):1"},                    # solo: warm-up+2 timed+safety = 4 laps (305.04.02b)
            {"kind": "qualification", "pattern": "3*(1000+4*1500):3", "qualifiers": [4, 4, 4]},  # qheat1/2 (top 4) + repechage (top 4); reduced 5-lap qheats
            {"kind": "circuit",       "pattern": "3*(1000+7*1500):3"},                    # finals: 3 heats x 8 laps
        ]},
    ]
    sheats = {"GT15": {"timetrial": 1, "circuit": 2},
              "F 500": {"timetrial": 1, "qualification": 3, "circuit": 3}}
    eventdata = {
        "schema": SCHEMA,
        "title": "Sample Regatta 2026 (GT15 & F 500)",
        "venue": "Lake Harku, Tallinn, Estonia",
        "date": "2026-08-15",
        "officer": "Madis Kalder",
        "secretary": "Tiia Aasaru",
        "configure": {"language": "English", "id_but_size": 40, "id_but_textsize": 14},
        "scoringsystem": [400, 300, 225, 169, 127, 95, 71, 53, 40, 30, 22, 17, 13, 9, 7, 5, 4, 3, 2, 1, 0],
        "classes": classes,
        "sheats": sheats,
        "participants": gt15_participants() + f500_participants(),
        "rules": rules_2026(),
        "record": {},        # waiting for the first time-trial run -- no heats yet
        "races": [],
        "prevorder": {},
        "savechecked": {},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(dump_event(eventdata))     # canonical native serialization (schema 2)
    # verify it reopens through the real store path
    reopened = EventStore.open(OUT).eventdata
    assert reopened.get("schema") == SCHEMA, reopened.get("schema")
    print("wrote %s  (schema %s, GT15=%d, F 500=%d participants, %d rules)"
          % (OUT, reopened.get("schema"), len(gt15_participants()),
             len(f500_participants()), len(eventdata["rules"])))
    return eventdata


if __name__ == "__main__":
    build()
