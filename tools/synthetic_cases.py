"""Synthetic edge-case race records exercising legacy analyzer branches that do
not occur in the 8 real events (rare record codes, restart/qualification/
time-trial heats, endurance point tiers, etc.).

Shared by ``tools/refharness.py`` (py2, golden generation) and
``tests/test_analyzer_equivalence.py`` (py3, differential check), so each case
is proven equivalent legacy<->port -- not just executed.

Kept py2.7/py3.13-compatible: plain dicts / lists / tuples only.
"""

SS = [400, 300, 225, 169, 127, 95, 71, 53, 40, 30, 22, 17, 13, 9, 7, 5, 4, 3, 2, 1, 0]


def _laps(n, t=20.0):
    return [(1, t) for _ in range(n)]


def get_cases():
    cases = []

    # 1) Circuit heat exercising every handled record code + disabled/unused codes
    #    and a mixed int/str id (py2 ordering path).
    cases.append({
        'name': 'circuit_codes',
        'heat': '1',
        'scoringsystem': SS,
        'info': {'course': [1000, 1000, 1000], 'racetime': 100000.0},
        'rec': {
            1: _laps(3),
            2: [(3, 5.0, 'LL')] + _laps(4),
            4: [(4, 5.0, 'PL')] + _laps(4),
            5: [(5, 5.0, 'PL5')] + _laps(2),
            6: [(8, 5.0, 'PL8')] + _laps(2),
            7: [(10, 5.0, 'DS')],
            8: [(11, 500.0, 'IR')] + _laps(2),
            9: [(12, 5.0, 'DQ')] + _laps(3),
            10: [(13, 5.0, 'YC')] + _laps(3),
            11: [(14, 5.0, 'RC')] + _laps(3),
            12: [(20, 5.0, 'NT')] + _laps(3),
            13: [(30, 5.0, 'Q')] + _laps(3),
            14: [(31, 5.0, 'NQ')] + _laps(3),
            15: [(1, 20.0), (-1, 2.0), (-2, 1.0), (1, 21.0),
                 (6, 5.0, 'LL2unused'), (9, 6.0, 'PL10unused'), (-10, 7.0, 'x')],
            'X1': _laps(2),
        },
    })

    # 2) Qualification heat (isqualification path; Q/NQ; qualification==3 check).
    cases.append({
        'name': 'qualification',
        'heat': '1q',
        'scoringsystem': SS,
        'info': {'course': [1000, 1000, 1000], 'racetime': 1000.0},
        'rec': {1: [(30, 5.0, 'q')] + _laps(3),
                2: [(31, 5.0, 'nq')] + _laps(1),
                3: _laps(3)},
    })

    # 3) Time trial heat (istimetrial path; laptime len>1 and <=1 branches).
    cases.append({
        'name': 'timetrial',
        'heat': '1t',
        'scoringsystem': SS,
        'info': {'course': [1000, 1000, 1000], 'racetime': 1000.0},
        'rec': {1: _laps(3, 18.0), 2: [(1, 20.0)]},
    })

    # 4) Restart 'r': full-points and half-points branches.
    cases.append({
        'name': 'restart_r_full',
        'heat': '1r',
        'scoringsystem': SS,
        'info': {'course': [1000, 1000, 1000, 1000], 'racetime': 100000.0},
        'rec': {1: _laps(4), 2: _laps(3), 3: _laps(2)},
    })
    cases.append({
        'name': 'restart_r_half',
        'heat': '1r',
        'scoringsystem': SS,
        # racetime tuned so no auto-IR fires (t + 2.5*esttime is not < racetime),
        # leader completes 2 of 10 laps -> minlaps4points(2) <= totallaps(2) <
        # minrestartrequiredlaps(3) -> the 0.5*points branch.
        'info': {'course': [1000] * 10, 'racetime': 90.0},
        'rec': {1: [(1, 20.0), (1, 20.0)], 2: [(1, 30.0), (1, 20.0)]},
    })

    # 5) Restart 'R' (isrestarted2).
    cases.append({
        'name': 'restart_R',
        'heat': '1R',
        'scoringsystem': SS,
        # 2-lap course so the leader finishes (code 0) and hits the isrestarted2
        # points branch.
        'info': {'course': [1000, 1000], 'racetime': 100000.0},
        'rec': {1: _laps(2), 2: _laps(1)},
    })

    # 6) get_racetime compute branch (info without 'racetime').
    cases.append({
        'name': 'no_racetime',
        'heat': '1',
        'scoringsystem': SS,
        'info': {'course': [1000, 1000]},
        'rec': {1: _laps(2), 2: _laps(1), 3: [(11, 3.0, 'ir')] + _laps(1)},
    })

    # 7) "disable last lapmarks" branch (a boat records a lap after the leader).
    cases.append({
        'name': 'late_lapmarks',
        'heat': '1',
        'scoringsystem': SS,
        'info': {'course': [1000, 1000, 1000], 'racetime': 100000.0},
        'rec': {1: [(1, 5.0), (1, 5.0), (1, 5.0)],
                2: [(1, 6.0), (1, 12.0), (1, 100.0)]},
    })

    # 8) Endurance heat exercising endurance codes (+ one point tier).
    cases.append({
        'name': 'endurance_codes_75',
        'heat': '1',
        'scoringsystem': SS,
        'info': {'course': [1000] * 20, 'duration': 1000.0, 'racetime': 800.0},
        'rec': {
            1: _laps(5),
            2: [(3, 5.0, 'LL')] + _laps(3),
            3: [(6, 5.0, 'LL2')] + _laps(3),
            4: [(4, 5.0, 'PL')] + _laps(3),
            5: [(5, 5.0, 'PL5')] + _laps(2),
            6: [(8, 5.0, 'PL8')] + _laps(2),
            7: [(9, 5.0, 'PL10')] + _laps(2),
            8: [(10, 5.0, 'DS')],
            9: [(11, 5.0, 'IR')] + _laps(2),
            10: [(12, 5.0, 'DQ')] + _laps(2),
            11: [(13, 5.0, 'YC')] + _laps(2),
            12: [(14, 5.0, 'RC')] + _laps(2),
            13: [(20, 5.0, 'NT')] + _laps(2),
            14: [(30, 5.0, 'unused-in-endurance')] + _laps(2),
        },
    })

    # 9) Endurance point tiers (racetime/duration -> 1.0 / 0.5 / 0.25).
    for nm, rt in [('endurance_full', 950.0), ('endurance_50', 600.0),
                   ('endurance_25', 300.0)]:
        cases.append({
            'name': nm,
            'heat': '1',
            'scoringsystem': SS,
            'info': {'course': [1000] * 20, 'duration': 1000.0, 'racetime': rt},
            'rec': {1: _laps(6), 2: _laps(3)},
        })

    # racetime < 25% of duration -> pointscoeff 0; boat 3's single lap overruns
    # racetime + 10 min -> endurance pastafterstoppage branch.
    cases.append({
        'name': 'endurance_none',
        'heat': '1',
        'scoringsystem': SS,
        'info': {'course': [1000] * 20, 'duration': 1000.0, 'racetime': 100.0},
        'rec': {1: _laps(6), 2: _laps(3), 3: [(1, 2000.0)]},
    })

    # Non-integer points (leader value 7 * 0.75 = 5.25) -> ceil() int(f)<f branch.
    cases.append({
        'name': 'endurance_ceil',
        'heat': '1',
        'scoringsystem': [7, 5, 3, 2, 1],
        'info': {'course': [1000] * 20, 'duration': 1000.0, 'racetime': 800.0},
        'rec': {1: _laps(5), 2: _laps(3)},
    })

    # Branch coverage: marks with time > racetime (guard-false paths) and
    # duplicate / empty-note marks (note-dedup false paths). Circuit + endurance.
    _dedup = [
        (10, 10.0, ''), (10, 11.0, 'd'), (10, 12.0, 'd'),
        (12, 10.0, ''), (12, 11.0, 'a'), (12, 12.0, 'a'),
        (14, 10.0, ''), (14, 11.0, 'r'), (14, 12.0, 'r'),
        (13, 10.0, ''), (13, 11.0, 'y'), (13, 12.0, 'y'),
        (20, 10.0, ''), (20, 11.0, 'n'), (20, 12.0, 'n'),
    ]
    cases.append({
        'name': 'circuit_guards_notes',
        'heat': '1',
        'scoringsystem': SS,
        'info': {'course': [1000, 1000, 1000], 'racetime': 50.0},
        'rec': {
            1: [(1, 20.0), (1, 20.0)],
            2: [(4, 100.0, 'x'), (5, 100.0, 'x'), (8, 100.0, 'x'),
                (3, 100.0, 'x'), (11, 100.0, 'x'), (1, 20.0)],
            3: _dedup + [(30, 10.0, ''), (30, 11.0, 'q'), (30, 12.0, 'q'),
                         (31, 10.0, ''), (31, 11.0, 'z'), (31, 12.0, 'z'), (1, 20.0)],
        },
    })
    cases.append({
        'name': 'endurance_guards_notes',
        'heat': '1',
        'scoringsystem': SS,
        'info': {'course': [1000] * 20, 'duration': 1000.0, 'racetime': 50.0},
        'rec': {
            1: [(1, 20.0), (1, 20.0)],
            2: [(4, 100.0, 'x'), (5, 100.0, 'x'), (8, 100.0, 'x'), (9, 100.0, 'x'),
                (3, 100.0, 'x'), (6, 100.0, 'x'), (11, 100.0, 'x'), (1, 20.0)],
            3: _dedup + [(3, 10.0, ''), (3, 13.0, 'l'),
                         (6, 10.0, ''), (6, 13.0, 'm'), (1, 20.0)],
        },
    })

    return cases


def get_model_cases():
    """Synthetic eventdata exercising race-pattern / heat branches absent from
    the real events (endurance patterns, /Q and /T classes, multi-term patterns,
    restart/qual/time heats in the race list)."""
    return {
        'endurance_pat': {
            'classes': [['x', 'END', '40*1500/1']],
            'races': [[['x', 'END', '1']]],
        },
        'endurance_plain': {
            'classes': [['x', 'END2', '1500/2']],   # no '*' in lap part
            'races': [],
        },
        'multiterm': {
            'classes': [['x', 'M', '2*(3*1000+2*500):2'],
                        ['x', 'M2', '3*1000:1'],
                        ['x', 'M3', '2*3*1000:1']],
            'races': [],
        },
        'restart_races': {
            'classes': [['x', 'R', '3*(4*1000):2']],
            'races': [[['x', 'R', '1']], [['x', 'R', '1r']],
                      [['x', 'R', '1R']], [['x', 'R', '2']]],
        },
        'heats_progression': {
            'classes': [['x', 'A', '3*(4*1000):2'],
                        ['x', 'A/Q', '2*(2*1000):1'],
                        ['x', 'A/T', '2*(2*1000):1']],
            'races': [
                [['x', 'A', '1'], ['x', 'A/Q', '1q'], ['x', 'A/T', '1t']],
                [['x', 'A', '2'], ['x', 'A/Q', '2q'], ['x', 'A/T', '2t']],
                [['x', 'A', '3']],
            ],
        },
        'not_allowed_heat': {
            'classes': [['x', 'B', '2*(3*1000):1']],
            'races': [[['x', 'B', '9']]],           # heat 9 not allowed
        },
        'edge_patterns': {
            'classes': [['x', 'C', ''],                 # empty pattern
                        ['x', 'S', '1000:1'],           # single heat, no '*'
                        ['x', 'K', '1*(2*3*1000):1'],   # inner 3-factor lap term
                        ['x', 'N', '3*(4*1000)']],      # no ':' -> sheats fallback
            'races': [],
        },
        'no_classes': {},                               # get_classes / get_heats KeyError
        'undefined_and_empty_race': {
            'classes': [['x', 'B', '2*(3*1000):1']],
            'races': [[['x', '', ''], ['x', 'Z', '1']]],  # empty row + undefined class
        },
    }
