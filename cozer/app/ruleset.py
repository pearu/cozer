"""Composable rule sets, stored in the ordinary ``.coz`` / ``.cozj`` event
structure — no new file format.

A *ruleset* file is an event whose ``kind`` is ``"ruleset"``: it defines only the
reusable parts of an event — the scoring system, the class-name vocabulary, and
the penalty/rules list — and carries no races or recorded results, so cozer can
present a restricted editor for maintaining it (see ``MainWindow._apply_kind``).

An event *imports* one or more rulesets: their contents are merged **additively**
into the event's own data (its local copy). Later edits to a shared ruleset
therefore never retroactively change an event that already imported it. Seeding
the predefined class names is just importing a bundled UIM ruleset; several thin
rulesets combine (general UIM + circuit, or general + endurance).

Pure functions over ``eventdata`` dicts; the GUI and store wrap them.
"""
import os

RULESET_KIND = "ruleset"
EVENT_KIND = "event"


def kind_of(eventdata):
    return eventdata.get("kind", EVENT_KIND)


def is_ruleset(eventdata):
    return kind_of(eventdata) == RULESET_KIND


def classnames_of(eventdata):
    """The class-name vocabulary: the explicit ``classnames`` list, unioned with
    any class names already used in this event's ``classes`` (order-preserving),
    so the picker never omits a class the event actually races."""
    names = list(eventdata.get("classnames") or [])
    seen = set(names)
    for row in eventdata.get("classes") or []:
        if len(row) > 1 and row[1] and row[1] not in seen:
            seen.add(row[1])
            names.append(row[1])
    return names


def ruleset_payload(source):
    """The (scoringsystem, classnames, rules) a source contributes. A full event
    used as a ruleset source yields class names derived from its ``classes``."""
    return {
        "scoringsystem": list(source.get("scoringsystem") or []),
        "classnames": classnames_of(source),
        "rules": [list(r) for r in (source.get("rules") or [])],
    }


def _rule_key(r):
    # A rule's identity is (action, paragraph); the index-0 sort field and the
    # index-3 human description are NOT part of it, so a reworded same-paragraph
    # rule is the same rule (deduped, existing kept), matching accumulate_ruleset.
    padded = (list(r) + ["", "", ""])[:3]   # 3 pads: a short/empty rule can't IndexError
    return (str(padded[1]), str(padded[2]))


def import_ruleset(event, source):
    """Additively, **non-destructively** merge ``source`` (a ruleset or event dict)
    into ``event`` in place. Class names and rules are unioned (order-preserving,
    deduped by (action, paragraph)); the imported scoring system fills the event's
    only if it has none -- an existing scoring system is never overwritten.
    Returns the list of changed ``event`` keys."""
    payload = ruleset_payload(source)
    changed = []

    names = classnames_of(event)
    seen = set(names)
    added = False
    for n in payload["classnames"]:
        if n and n not in seen:
            seen.add(n)
            names.append(n)
            added = True
    if added or "classnames" not in event:
        event["classnames"] = names
        changed.append("classnames")

    rules = [list(r) for r in (event.get("rules") or [])]
    seen_r = {_rule_key(r) for r in rules}
    added_r = False
    for r in payload["rules"]:
        if _rule_key(r) not in seen_r:
            seen_r.add(_rule_key(r))
            rules.append(list(r))
            added_r = True
    if added_r:
        event["rules"] = rules
        changed.append("rules")

    # scoring system: fill only if the event has none -- never overwrite. An event
    # that already scores keeps it; an import then contributes only names + rules.
    if payload["scoringsystem"] and not (event.get("scoringsystem") or []):
        event["scoringsystem"] = list(payload["scoringsystem"])
        changed.append("scoringsystem")

    return changed


def accumulate_ruleset(target, source, label=""):
    """Merge a source's scoring system, class names and rules into ``target`` in
    place, **non-destructively** (used by the CLI to accumulate several files into
    one event): add class names and rules that aren't already present, and fill
    the scoring system only if the target's is empty. Existing target data is
    never overwritten — a source value that conflicts with existing data is
    reported but not applied. Returns the list of conflict messages.
    """
    reports = []
    # class names: add new (union, order-preserving)
    names = target.setdefault("classnames", [])
    seen = set(names)
    for n in classnames_of(source):
        if n and n not in seen:
            seen.add(n)
            names.append(n)
    # rules: add new by (action, paragraph); keep existing on conflict
    rules = target.setdefault("rules", [])
    have = {}
    for r in rules:
        if len(r) > 2:
            have[(r[1], r[2])] = (list(r) + ["", "", "", ""])[3]
    for r in (source.get("rules") or []):
        r = (list(r) + ["", "", "", ""])[:4]
        key = (r[1], r[2])
        if key in have:
            if have[key] != r[3]:
                reports.append("%srule %s/%s kept as %r (source has %r)"
                               % (label, r[1] or "?", r[2] or "?", have[key], r[3]))
        else:
            have[key] = r[3]
            rules.append(list(r))
    # scoring system: fill only if empty; never overwrite
    src_score = list(source.get("scoringsystem") or [])
    if src_score:
        cur = list(target.get("scoringsystem") or [])
        if not cur:
            target["scoringsystem"] = src_score
        elif cur != src_score:
            reports.append("%sscoring system kept (source differs)" % label)
    return reports


def new_ruleset(name=""):
    """A blank ruleset eventdata (kind == 'ruleset', no races/records)."""
    return {
        "title": name, "venue": "", "date": "", "officer": "", "secretary": "",
        "kind": RULESET_KIND,
        "scoringsystem": [], "classnames": [], "rules": [],
        "classes": [], "participants": [], "races": [], "record": {},
        "configure": {"language": "English"},
    }


def bundled_dir():
    """Directory of the bundled seed rulesets shipped with cozer."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "rulesets")
