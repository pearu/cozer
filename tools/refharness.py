#!/usr/bin/env python2
"""Phase 1 reference harness -- run under the ``cozer-ref`` (Python 2.7) env.

Loads every legacy ``.coz``, runs the LEGACY scoring core over each
(class, heat), and writes canonical golden fixtures to
``tests/golden/analyze/<event>.json``.

It captures BOTH the return values AND the input mutations, because the legacy
``analyze`` mutates the record it is given (``get_racetime`` sets
``info['racetime']``; ``insertmark`` appends inferred IR/DNS marks).

Usage::

    <cozer-ref python> tools/refharness.py
"""
import os
import sys
import copy
import glob
import tempfile

try:
    import cPickle as pickle
except ImportError:
    import pickle

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEGACY_PKG = os.path.join(REPO, 'legacy', 'cozer')

# Make the legacy modules importable as top-level names (py2 implicit relative
# imports) and install the wx shim before importing prefs.
sys.path.insert(0, HERE)
sys.path.insert(0, LEGACY_PKG)
import wx_shim
sys.modules['wx'] = wx_shim

# prefs has import-time side effects (creates ./log, wraps stdout); run from a
# throwaway dir so nothing lands in the repo.
_workdir = tempfile.mkdtemp(prefix='cozer_ref_')
os.chdir(_workdir)

import prefs        # noqa: E402
import analyzer     # noqa: E402
import golden_io    # noqa: E402


def _err(e):
    return {'__error__': '%s: %s' % (type(e).__name__, e)}


def load_coz(path):
    f = open(path, 'rb')
    try:
        data = pickle.load(f)
    finally:
        f.close()
    return prefs.normalize_str(data)   # faithful to legacy OpenCozFile


def run_one(record_ch, heat, scoringsystem):
    """record_ch = (info, rec) for one class/heat -> golden dict."""
    out = {}
    # analyze mutates its input: run on a fresh copy, capture result + mutation.
    rc = copy.deepcopy(record_ch)
    try:
        res = analyzer.analyze(heat, rc, scoringsystem)
        out['analyze'] = res
        out['record_after_analyze'] = rc
        try:
            out['resorder'] = analyzer.getresorder(res)
        except Exception as e:
            out['resorder'] = _err(e)
    except Exception as e:
        out['analyze'] = _err(e)
    # countlaps does not mutate; fresh copy for isolation anyway.
    rc2 = copy.deepcopy(record_ch)
    try:
        out['countlaps'] = analyzer.countlaps(heat, rc2)
    except Exception as e:
        out['countlaps'] = _err(e)
    return out


def process(path):
    data = load_coz(path)
    scoringsystem = data.get('scoringsystem', [])
    record = data.get('record', {}) or {}
    golden = {'event': os.path.basename(path),
              'scoringsystem': scoringsystem,
              'analyze': {}}
    for cl in sorted(record.keys()):
        heats = record[cl]
        for h in sorted(heats.keys()):
            golden['analyze'][u'%s||%s' % (cl, h)] = run_one(heats[h], h, scoringsystem)
    return golden


def main():
    out_dir = os.path.join(REPO, 'tests', 'golden', 'analyze')
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    coz_files = sorted(glob.glob(os.path.join(REPO, 'legacy', 'events', '*.coz')) +
                       glob.glob(os.path.join(REPO, 'legacy', 'cozer', 'data', '*.coz')))
    total = 0
    for path in coz_files:
        name = os.path.splitext(os.path.basename(path))[0]
        golden = process(path)
        f = open(os.path.join(out_dir, name + '.json'), 'w')
        f.write(golden_io.dumps(golden))
        f.close()
        n = len(golden['analyze'])
        total += n
        sys.__stdout__.write('  %-45s %3d class/heat records\n' % (name, n))
    sys.__stdout__.write('Wrote %d golden files (%d records) to %s\n'
                         % (len(coz_files), total, out_dir))


if __name__ == '__main__':
    main()
