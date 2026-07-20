"""Suffix-free phase-native event schema — the target model for the suffix refactor.

Stage 1: a converter between the legacy **suffixed** shape (class names carry
``/T``/``/Q``; heat ids carry ``t``/``q`` sub-kind or ``r``/``R`` restart) and a
**suffix-free** shape where

- ``classes`` is a list of ``{name: base, phases: [{kind, pattern, qualifiers?}, ...]}``
  (kind is explicit, so no ``/T``/``/Q`` on the name; the ``!qualification[...]`` count
  moves to a ``qualifiers`` list);
- ``record`` is ``record[base][kind][number] = [ [info, boats], ... ]`` — a **restart is
  an extra list entry** under the number, so no ``1r``/``1q`` heat ids;
- ``races`` reference a heat by ``{name, kind, number, occurrence}`` (occurrence = restart
  rank), again suffix-free.

Everything else in ``eventdata`` (participants, scoringsystem, rules, qheat1, …) passes
through untouched — participants/qheat1 are already base-keyed. The record ``[info, boats]``
objects are carried through by reference.

``to_native`` / ``from_native`` are inverses on canonically-suffixed input **for the record
and races**; ``classes`` are **content-preserving but order-canonicalized** — nesting phases
under a base means the round-trip regroups a legacy flat ``[all bases, then all /T]`` layout
to **base-grouped** (each base followed by its ``/T``/``/Q``), matching the native model (and
the base-grouped Classes tab). Base order and each class's col0/pattern are kept; only the
interleaving of a base's phases is canonicalized. Verified on the whole bundled corpus (only
``/T`` and heat suffixes ``''``/``r``/``t``, no non-canonical spellings). Legacy provenance is
intentionally NOT preserved: a legacy `.coz`
is read once (import) and never written back (``legacy/cozer`` remains for legacy files —
owner), so the round-trip canonicalizes, which is a no-op on the canonical corpus.
"""
import re

from cozer.classes import getclass
from cozer.phases import synth_heat_id
from cozer.qualification import qualification_counts
from cozer.racepattern import class_pattern, race_kind

# On-disk schema version, carried in the native dict so a loader dispatches unambiguously
# instead of sniffing the shape: absent/1 = legacy suffixed (old .cozj); 2 = native
# suffix-free (this module); a value ABOVE the loader's known max must fail fast ("saved by
# a newer cozer") rather than silently mangle a future format.
SCHEMA = 2


def schema_of(data):
    """The storage-format version of a loaded dict — 2+ for native, 1 for legacy/unversioned."""
    return (data or {}).get("schema", 1)


def is_native(data):
    """True if ``data`` is in the suffix-free native shape (schema >= 2)."""
    return schema_of(data) >= 2


_HEAT_RE = re.compile(r"^(\d+)([a-zA-Z]?)$")
_RESTART_RANK = {"": 0, "r": 1, "R": 2}      # circuit heat-id restart suffix -> occurrence
_QUAL_TOKEN = re.compile(r"\s*!qualification\[[\d,\s]*\]", re.I)


def _parse_heat(hid):
    """``(number, occurrence)`` for a legacy heat id: ``'1'``→(1,0), ``'2r'``→(2,1),
    ``'1t'``/``'1q'``→(1,0) (the sub-kind letter carries no restart rank)."""
    m = _HEAT_RE.match(str(hid))
    if not m:
        raise ValueError("unrecognized heat id %r" % (hid,))
    return int(m.group(1)), _RESTART_RANK.get(m.group(2), 0)


def _class_name(base, kind):
    """Canonical legacy class name for a base + kind (``F-4`` + timetrial → ``F-4/T``)."""
    return base + "/T" if kind == "timetrial" else base + "/Q" if kind == "qualification" else base


def _strip_qual(pattern):
    return _QUAL_TOKEN.sub("", pattern or "").strip()


# Top-level ``{class_name: value}`` caches that are keyed by a (suffixed) class name and so
# also carry suffixes — converted to ``{base: {kind: value}}`` like the record.
_CLASS_KEYED = ("sheats", "savechecked")


def _classkeyed_to_native(eventdata, field):
    """``{suffixed_class: value}`` → ``{base: {kind: value}}``."""
    out = {}
    for cl, val in (field or {}).items():
        out.setdefault(getclass(cl), {})[race_kind(eventdata, cl)] = val
    return out


def _classkeyed_from_native(field):
    """``{base: {kind: value}}`` → ``{suffixed_class: value}``."""
    out = {}
    for base, kinds in (field or {}).items():
        for kind, val in (kinds or {}).items():
            out[_class_name(base, kind)] = val
    return out


def _phase_of(eventdata, name):
    """The native phase dict for a legacy class ``name`` — kind, pattern (qualification
    count split out into ``qualifiers``)."""
    pat = class_pattern(eventdata, name) or ""
    ph = {"kind": race_kind(eventdata, name), "pattern": _strip_qual(pat)}
    counts = qualification_counts(pat)
    if counts:
        ph["qualifiers"] = list(counts)
    return ph


def _native_addr(eventdata, cl, h):
    """A legacy ``(class, heat_id)`` → the native address ``(base, kind, number, occurrence)``."""
    return getclass(cl), race_kind(eventdata, cl), _parse_heat(h)


def record_heat(eventdata, cl, h):
    """The ``[info, boats]`` record for legacy ``(class, heat_id)``, or ``None`` — works on
    both shapes (native ``record[base][kind][number][occurrence]`` and legacy ``record[cl][h]``),
    so a direct-record consumer addresses heats by the legacy id regardless of the storage."""
    rec = eventdata.get("record", {}) or {}
    if eventdata.get("schema", 1) >= SCHEMA:
        base, kind, (num, occ) = _native_addr(eventdata, cl, h)
        lst = (rec.get(base, {}) or {}).get(kind, {}).get(str(num))
        return lst[occ] if lst and occ < len(lst) else None
    return rec.get(cl, {}).get(h)


def ensure_heat(eventdata, cl, h, slot):
    """Place ``slot`` (``[info, boats]``) at legacy ``(class, heat_id)``, creating the path.
    Native: ``record[base][kind][number]`` is a list indexed by restart occurrence."""
    rec = eventdata.setdefault("record", {})
    if eventdata.get("schema", 1) >= SCHEMA:
        base, kind, (num, occ) = _native_addr(eventdata, cl, h)
        lst = rec.setdefault(base, {}).setdefault(kind, {}).setdefault(str(num), [])
        while len(lst) <= occ:
            lst.append([{}, {}])
        lst[occ] = slot
    else:
        rec.setdefault(cl, {})[h] = slot


def legacy_races_to_native(eventdata, races):
    """Race schedule → suffix-free heat refs. The in-memory model is native now, so this is
    mainly the legacy ``.coz`` import path (``to_native``): legacy ``[_, class, heat]`` rows →
    ``{name, kind, number, occurrence}``. Accepts either shape per entry — already-native dict
    entries pass through — so it is safe on already-native input too."""
    out = []
    for race in races or []:
        entries = []
        for e in race:
            if isinstance(e, dict):
                entries.append(e)                     # already a suffix-free ref
            elif len(e) > 2 and e[1] and e[2]:
                num, occ = _parse_heat(e[2])
                entries.append({"name": getclass(e[1]), "kind": race_kind(eventdata, e[1]),
                                "number": num, "occurrence": occ})
            else:
                entries.append(e)
        out.append(entries)
    return out


def native_races_to_legacy(races):
    """Suffix-free heat refs → legacy ``[_, class, heat]`` rows. The model and the store are both
    native now, so this is the inverse used by ``from_native`` (legacy export / tests) and to
    derive a legacy ``(class, heat)`` addressing key from a native entry. Already-legacy entries
    pass through."""
    out = []
    for race in races or []:
        entries = []
        for e in race:
            if isinstance(e, dict):
                entries.append(["", _class_name(e["name"], e["kind"]),
                                synth_heat_id(e["kind"], e["number"], e.get("occurrence", 0))])
            else:
                entries.append(e)                     # already a legacy row
        out.append(entries)
    return out


def to_native(eventdata):
    """Legacy suffixed ``eventdata`` → the suffix-free shape (a new dict; input untouched).
    Tags the result with ``schema = SCHEMA`` so the on-disk format is self-describing.
    Idempotent: already-native input (record/classes/races) is returned unchanged — races are
    still run through ``legacy_races_to_native``, which passes native dict entries through."""
    if eventdata.get("schema", 1) >= SCHEMA:
        out = dict(eventdata)
        if "races" in eventdata:                      # native dict entries pass through unchanged
            out["races"] = legacy_races_to_native(eventdata, eventdata["races"])
        return out
    out = dict(eventdata)
    out["schema"] = SCHEMA

    bases, by_base = [], {}                       # classes: group by base, keep appearance order
    for row in eventdata.get("classes", []) or []:
        name = row[1] if len(row) > 1 else ""
        if not name:
            continue
        base = getclass(name)
        if base not in by_base:
            by_base[base] = []
            bases.append(base)
        ph = _phase_of(eventdata, name)
        if len(row) > 0 and row[0]:               # preserve the vestigial legacy col-0 verbatim
            ph["legacy0"] = row[0]
        by_base[base].append(ph)
    if "classes" in eventdata:                    # preserve key presence (don't invent empties)
        out["classes"] = [{"name": b, "phases": by_base[b]} for b in bases]

    nrec = {}                                     # record[base][kind][number] = [records...]
    for cl, heats in (eventdata.get("record") or {}).items():
        base, kind = getclass(cl), race_kind(eventdata, cl)
        kd = nrec.setdefault(base, {}).setdefault(kind, {})
        for h in sorted(heats, key=_parse_heat):  # (number, occurrence) — restart follows original
            num, _occ = _parse_heat(h)
            kd.setdefault(str(num), []).append(heats[h])
    if "record" in eventdata:
        out["record"] = nrec

    if "races" in eventdata:                      # races: suffix-free heat refs
        out["races"] = legacy_races_to_native(eventdata, eventdata["races"])

    for key in _CLASS_KEYED:                          # suffix-keyed caches -> base/kind nested
        if key in eventdata:
            out[key] = _classkeyed_to_native(eventdata, eventdata[key])
    return out


def from_native(native):
    """Suffix-free shape → the legacy suffixed ``eventdata`` (canonical). Inverse of
    :func:`to_native` on canonically-suffixed data. Idempotent: already-suffixed (legacy /
    unversioned) input is returned as-is."""
    if not is_native(native):
        return dict(native)
    out = dict(native)
    out.pop("schema", None)            # the legacy/in-memory shape carries no version tag

    classes = []
    for entry in native.get("classes", []) or []:
        base = entry["name"]
        for ph in entry.get("phases", []) or []:
            pat = ph.get("pattern", "")
            if ph.get("qualifiers"):
                pat = "%s!qualification[%s]" % (pat, ",".join(str(c) for c in ph["qualifiers"]))
            classes.append([ph.get("legacy0", ""), _class_name(base, ph["kind"]), pat])
    if "classes" in native:
        out["classes"] = classes

    record = {}
    for base, kinds in (native.get("record") or {}).items():
        for kind, nums in kinds.items():
            heats = {}
            for num, recs in nums.items():
                for rank, rec in enumerate(recs):
                    heats[synth_heat_id(kind, int(num), rank)] = rec
            record[_class_name(base, kind)] = heats
    if "record" in native:
        out["record"] = record

    if "races" in native:
        out["races"] = native_races_to_legacy(native["races"])

    for key in _CLASS_KEYED:
        if key in native:
            out[key] = _classkeyed_from_native(native[key])
    return out
