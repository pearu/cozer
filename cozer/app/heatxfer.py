"""Export/import a heat's measured records between two cozer instances of the same event.

A heat's record is addressed by **(class, phase, heat)** — ``record[base][kind][number][occurrence]`` —
independent of the Races-tab order, so the equivalent heat on another machine is found by that tuple
(if the schedules differ). This is app-layer I/O only: it reuses the existing record slot, the class
pattern, the participant list, and the journal ops (``heat`` + ``replace``). It changes **no** scoring
or seeding algorithm and **no** data structure.

Rules (owner):
  * a heat imports only if the target has the same **(class, phase)** and an **equivalent race pattern**
    — otherwise it is rejected with a message (never silently add a class or a different pattern);
  * every boat that carries marks must already be a **participant** of that class in the target — a
    missing boat rejects the heat (never invent participants);
  * if the equivalent record already holds **measured data**, overwriting is **confirmed** first;
  * a missing **Races-tab** entry for the heat is added (schedule metadata only).
"""
from cozer.classes import getclass
from cozer.native import record_heat
from cozer.phases import heat_number, heat_occurrence
from cozer.qualification import participant_boats
from cozer.racepattern import class_pattern, crack_race_pattern, get_classes, race_kind

KIND = "cozer-heat-records"


def _event_name(eventdata):
    return (eventdata.get("broadcast", {}) or {}).get("eventname") or eventdata.get("title", "") or ""


def export_heats(eventdata, selection):
    """The export payload for the ``(cl, heat_id)`` pairs in ``selection`` (the Reports-tab checked
    heats). Only heats that actually have a record slot are included; each carries its (class, phase,
    heat) address, the class pattern (for the importer's equivalence check), and the record
    ``[info, boats]``."""
    heats = []
    for cl, h in selection:
        rec = record_heat(eventdata, cl, h)
        if rec is None:
            continue                       # nothing recorded for this heat -> nothing to export
        heats.append({"class": cl, "phase": race_kind(eventdata, cl), "heat": h,
                      "pattern": class_pattern(eventdata, cl), "record": rec})
    return {"kind": KIND, "event": _event_name(eventdata), "heats": heats}


def _patterns_equivalent(p1, p2):
    """Two race patterns are equivalent if they crack to the same heat/lap structure (whitespace or
    formatting differences don't matter); fall back to string equality if either won't parse."""
    try:
        return crack_race_pattern(p1 or "") == crack_race_pattern(p2 or "")
    except Exception:
        return (p1 or "") == (p2 or "")


def validate_heat(eventdata, heat):
    """``None`` if ``heat`` can be imported into ``eventdata``, else a human message why not."""
    cl, h = heat.get("class"), heat.get("heat")
    if not cl or not h or not isinstance(heat.get("record"), (list, tuple)):
        return "malformed heat entry"
    if cl not in get_classes(eventdata):
        return "no class/phase '%s' in this event" % cl
    if not _patterns_equivalent(class_pattern(eventdata, cl), heat.get("pattern")):
        return "race pattern for '%s' differs from the source" % cl
    boats = (heat.get("record") or [None, {}])[1] or {}
    known = set(participant_boats(eventdata, cl))
    missing = sorted((str(b) for b, marks in boats.items() if marks and str(b) not in known),
                     key=lambda s: (len(s), s))
    if missing:
        return "boat(s) not in this event's '%s': %s" % (cl, ", ".join(missing))
    return None


def import_heats(eventdata, payload, record_op, confirm):
    """Validate + apply each heat in ``payload``.

    ``record_op(op)`` journals+applies one store op (pass ``store.record``). ``confirm(cl, h) -> bool``
    decides whether to overwrite existing **measured** data. Returns ``(imported, rejected)`` — lists of
    ``"<class> <heat>"`` (imported) and ``"<class> <heat>: <reason>"`` (rejected). Valid heats are
    applied even if others in the file are rejected (owner)."""
    imported, rejected = [], []
    if not isinstance(payload, dict) or payload.get("kind") != KIND:
        return imported, ["not a cozer heat-records file"]
    for heat in payload.get("heats", []) or []:
        cl, h = heat.get("class"), heat.get("heat")
        why = validate_heat(eventdata, heat)
        if why:
            rejected.append("%s %s: %s" % (cl, h, why))
            continue
        info, boats = heat["record"][0], heat["record"][1]
        existing = record_heat(eventdata, cl, h)
        if existing and any(existing[1].values()) and not confirm(cl, h):
            rejected.append("%s %s: kept existing measured data" % (cl, h))
            continue
        record_op({"op": "heat", "cl": cl, "h": h, "info": dict(info or {}), "ids": list(boats or {})})
        for bid, marks in (boats or {}).items():
            record_op({"op": "replace", "cl": cl, "h": h, "id": str(bid), "marks": list(marks)})
        _ensure_race_entry(eventdata, cl, h)
        imported.append("%s %s" % (cl, h))
    return imported, rejected


def _ensure_race_entry(eventdata, cl, h):
    """Add a one-heat race to the schedule if this ``(base, kind, number, occurrence)`` is not already
    scheduled (owner: add the missing Races-tab entry). Schedule metadata only — no record change."""
    base, kind = getclass(cl), race_kind(eventdata, cl)
    num, occ = heat_number(h), heat_occurrence(h)
    for race in eventdata.get("races", []) or []:
        for e in race:
            if (isinstance(e, dict) and e.get("name") == base and e.get("kind") == kind
                    and e.get("number") == num and e.get("occurrence", 0) == occ):
                return                     # already scheduled
    eventdata.setdefault("races", []).append(
        [{"name": base, "kind": kind, "number": num, "occurrence": occ}])
