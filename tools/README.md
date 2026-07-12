# tools/

Developer utilities for the cozer modernization (see `../MAINTENANCE_PLAN.md`).

Planned (Phase 1):

- `wx_shim.py` — a minimal fake `wx` module so the **legacy** core (`legacy/cozer/`)
  imports and runs under stock **Python 2.7** without building wxPython 2.8.
- `refharness.py` — runs the legacy core (py2.7, `cozer-ref` env) over
  `legacy/events/*.coz` and `legacy/cozer/data/*.coz` to generate the golden
  fixtures in `tests/golden/` (return values **and** input mutations; time frozen).
