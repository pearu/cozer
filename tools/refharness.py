#!/usr/bin/env python2
"""Reference harness -- run under the ``cozer-ref`` (Python 2.7) env.

Generates the golden fixtures the Python-3 port is proven against, by running
the ACTUAL legacy code headless (catch-all wx shim, tools/wx_shim):

  tests/golden/analyze/<event>.json  -- analyze / resorder / countlaps (+ input
                                        mutations) per class-heat; plus
                                        _synthetic.json (tools/synthetic_cases).
  tests/golden/model/<event>.json    -- CrackRacePattern / GetAllowedHeats /
                                        GetHeats / GetClasses per event (run on a
                                        fake, uninitialised MainFrame instance).

Usage:  <cozer-ref python> tools/refharness.py
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

sys.path.insert(0, HERE)                            # wx_shim, golden_io, synthetic_cases
sys.path.insert(0, os.path.join(REPO, 'legacy'))    # `import cozer` -> legacy package

import wx_shim
wx_shim.install()

# prefs has import-time side effects (creates ./log, wraps stdout); run from a
# throwaway dir so nothing lands in the repo.
_workdir = tempfile.mkdtemp(prefix='cozer_ref_')
os.chdir(_workdir)

import cozer as legacy_cozer       # noqa: E402  (ORIGINAL package under legacy/)
import cozer.prefs as prefs        # noqa: E402
import cozer.analyzer as analyzer  # noqa: E402
import golden_io                   # noqa: E402


def _err(e):
    return {'__error__': '%s: %s' % (type(e).__name__, e)}


def _write(path, text):
    f = open(path, 'w')
    f.write(text)
    f.close()


def load_coz(path):
    f = open(path, 'rb')
    try:
        data = pickle.load(f)
    finally:
        f.close()
    return prefs.normalize_str(data)


# --- analyze goldens -------------------------------------------------------

def run_one(record_ch, heat, scoringsystem):
    out = {}
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
    rc2 = copy.deepcopy(record_ch)
    try:
        out['countlaps'] = analyzer.countlaps(heat, rc2)
    except Exception as e:
        out['countlaps'] = _err(e)
    return out


def process_analyze(data):
    scoringsystem = data.get('scoringsystem', [])
    record = data.get('record', {}) or {}
    out = {'scoringsystem': scoringsystem, 'analyze': {}}
    for cl in sorted(record.keys()):
        for h in sorted(record[cl].keys()):
            out['analyze'][u'%s||%s' % (cl, h)] = run_one(record[cl][h], h, scoringsystem)
    return out


# --- model goldens (CrackRacePattern / GetAllowedHeats / GetHeats) ---------

def make_frame():
    mf = legacy_cozer.MainFrame.__new__(legacy_cozer.MainFrame)
    mf.debug = 0
    mf.Debug = lambda *a, **k: None
    mf.Warning = lambda *a, **k: None
    mf.Info = lambda *a, **k: None
    mf.Message = lambda *a, **k: None
    return mf


def process_model(data, mf):
    mf.eventdata = data
    out = {'classes': mf.GetClasses(), 'crack': {}, 'allowedheats': {}, 'getheats': {}}
    for l in data.get('classes', []):
        cl = l[1] if len(l) > 1 else ''
        pat = l[2] if len(l) > 2 else ''
        if cl and pat:
            try:
                out['crack'][cl] = mf.CrackRacePattern(pat, cl)
            except Exception as e:
                out['crack'][cl] = _err(e)
        if cl:
            try:
                out['allowedheats'][cl] = mf.GetAllowedHeats(cl)
            except Exception as e:
                out['allowedheats'][cl] = _err(e)
    for raceid in range(len(data.get('races', [])) + 1):
        try:
            out['getheats'][str(raceid)] = mf.GetHeats(raceid)
        except Exception as e:
            out['getheats'][str(raceid)] = _err(e)
    return out


def main():
    a_dir = os.path.join(REPO, 'tests', 'golden', 'analyze')
    m_dir = os.path.join(REPO, 'tests', 'golden', 'model')
    for d in (a_dir, m_dir):
        if not os.path.isdir(d):
            os.makedirs(d)
    coz_files = sorted(glob.glob(os.path.join(REPO, 'legacy', 'events', '*.coz')) +
                       glob.glob(os.path.join(REPO, 'legacy', 'cozer', 'data', '*.coz')))
    mf = make_frame()
    total = 0
    for path in coz_files:
        name = os.path.splitext(os.path.basename(path))[0]
        data = load_coz(path)
        ag = process_analyze(data)
        ag['event'] = os.path.basename(path)
        _write(os.path.join(a_dir, name + '.json'), golden_io.dumps(ag))
        mg = process_model(data, mf)
        mg['event'] = os.path.basename(path)
        _write(os.path.join(m_dir, name + '.json'), golden_io.dumps(mg))
        total += len(ag['analyze'])
        sys.__stdout__.write('  %-42s %3d heats, %2d classes\n'
                             % (name, len(ag['analyze']), len(mg['classes'])))

    # synthetic edge cases (analyze only)
    import synthetic_cases
    syn = {}
    for case in synthetic_cases.get_cases():
        syn[case['name']] = run_one((case['info'], case['rec']), case['heat'], case['scoringsystem'])
    _write(os.path.join(a_dir, '_synthetic.json'), golden_io.dumps(syn))
    sys.__stdout__.write('  %-42s %3d synthetic cases\n' % ('_synthetic', len(syn)))

    # synthetic model cases
    smc = synthetic_cases.get_model_cases()
    syn_model = {}
    for nm in sorted(smc):
        syn_model[nm] = process_model(smc[nm], mf)
    _write(os.path.join(m_dir, '_synthetic.json'), golden_io.dumps(syn_model))
    sys.__stdout__.write('  %-42s %3d synthetic model cases\n' % ('_synthetic(model)', len(syn_model)))

    sys.__stdout__.write('Wrote analyze (%d files, %d heats + %d syn) and model (%d files + %d syn)\n'
                         % (len(coz_files), total, len(syn), len(coz_files), len(syn_model)))


if __name__ == '__main__':
    main()
