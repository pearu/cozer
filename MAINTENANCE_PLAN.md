# COZER Maintenance & Modernization Plan (rebuild the `cozer` package; old program → `legacy/`)

Status: **DRAFT for approval** · Last updated: 2026-07-18 · Owner: Pearu Peterson

This document is the source of truth for modernizing COZER. The original Python-2 program
has been moved to **`legacy/`** (it must remain functional under Python 2); the new
implementation is built fresh as the **`cozer/`** package. The transition proceeds
**gradually**, **with tests**, and with a **proof that the new core behaves identically to
legacy**. Every phase is independently approvable; **`legacy/` stays untouched and must remain
runnable permanently, independent of phase** (used as the bug-for-bug reference). The new
`cozer` becomes the default at cutover (Phase 6); `legacy/` keeps working regardless.

---

## 1. Context & goals

COZER is a ~20-year-old **Python 2 / wxPython 2.8** desktop application for organizing
powerboat racing events under U.I.M. Circuit Rules. It is still functional but hard to
install and maintain on modern systems, especially Windows (where it is mostly used).

**Goals**

1. Make it **easy to install on Windows and Linux** with contemporary tooling (mamba/conda).
2. Preserve, and provably reproduce, the **core scoring functionality**.
3. Make it **extremely robust**: survive sudden power loss (all recorded data recoverable)
   and survive bugs (the program stays usable and recorded data persists even if a part
   of the program is broken).
4. Modernize dependencies where it improves robustness/maintainability.
5. Lay the groundwork for **live online output** (race state to an external site).

**Hard constraints (from the owner)**

- **Recording must work fully offline** — venue internet may be unstable or absent.
- **Live reporting may assume internet.**
- **Linux + Windows are must-have.**
- **Python 3.13 or newer.**
- **Mobile = viewing only** (reports/live results). Recording on mobile is out of scope.
- Reports must remain **high quality** and carry the **same information per page** as the
  current LaTeX reports (per-report **landscape/portrait** orientation preserved).
- **All changes require owner approval.**

---

## 2. Current architecture (as-is)

*(All source paths below now live under `legacy/cozer/`; historical events under `legacy/events/`.)*

| Layer | Files | GUI-coupled | Role |
|---|---|---|---|
| **Scoring core** | `analyzer.py` | No (pure) | `analyze`, `analyze_endurance`, `sumanalyze`, `countlaps`, ordering. Correctness-critical. |
| **Event/data logic** | `__init__.py` (`MainFrame`), parts of `prefs.py` | Mixed | `CrackRacePattern`, `GetHeats`, `GetAllowedHeats`, `gettimes`, `insertmark`, class predicates. |
| **Reports** | `reports.py` + `data/*.tex`, `*.sty` | No (builds text), then shells out | 9 report types → LaTeX → `dvips`/`dvipdfm` → viewer. |
| **Persistence** | `__init__.py`, `prefs.py` | No | `.coz` = **cPickle protocol 1**; `AutoSaveTimer` (30 s, off by default). |
| **GUI** | `sub_nbs.py`, `tables.py`, `datatable.py`, `timers.py`, `buildmenus.py`, `sub_menus.py`, `sub_help.py` | Yes | Notebook of pages; `timers.py` = live lap timing + graphical record editor. |
| **Live displays** | `led/*.py` | No | Already **Python 3**, standalone, HTTP-driven LED boards. Seed of live output. |
| **Dead code** | `classes.py` | — | Not imported anywhere → drop in cozer. |

### Data model (`eventdata` dict)

- `title`, `venue`, `date`, `officer`, `secretary` — strings
- `scoringsystem` — monotone list of numbers
- `rules` — `[[sortby, action, paragraph, description], …]`
- `classes` — `[[sortby, class, race-pattern], …]`
- `participants` — `[[sortby, firstname, surname, club, class, id], …]`
- `races` — `[[[sortby, class, heat], …], …]`
- `record` — `{class: {heat: (info, {id: [(code, data…), …]})}}`
  - `info` = `{starttime, racetime, course, sheats, duration}`
- Plus: `savechecked`, `configure` (`id_but_size`, `language`), `prevorder`, `sheats`

### Record codes (`prefs.reccodemap`)

`1`=completed lap, `2`=inserted lap, **negative code = disabled** (enable on/off),
`3`=lost lap (LL), `6`=lost two laps (LL2), `4`=penalty lap (PL), `5`=PL5, `8`=PL8, `9`=PL10,
`10`=DNS (DS), `11`=interruption (IR), `12`=DQ, `13`=yellow card (YC), `14`=red card (RC),
`20`=note (NT), `30`=Q, `31`=NQ.

### Report orientation (must be preserved)

| Report | Function | Orientation |
|---|---|---|
| Participants | `participants` | Portrait |
| Intermediate | `intermediate` | Portrait |
| Endurance Full Final | `fullfinal_endurance` | **Landscape** |
| Full Final | `fullfinal` | **Landscape** |
| Short Final | `shortfinal` | Portrait |
| Check List | `checklist` | **Landscape** |
| Info Letter | `infoletter` | Portrait |
| Registration Letter | `registrationletter` | Portrait |
| Laps Protocol | `lapsprotocol` | Portrait |

### Key robustness gaps in the current code

1. **Non-atomic save** — `OnFileSave` writes the only copy in place; a crash mid-write
   corrupts everything. **Highest-priority risk.**
2. **Autosave off by default**, and only during timing.
3. **No backups / no journal** — no recovery point, nothing to replay after a crash.
4. **Opaque pickle** — not hand-inspectable/recoverable; fragile across Python versions.
5. **A bug anywhere can crash the whole app** — pervasive `exec`, backtick-repr, bare `except`.

---

## 3. Target architecture (to-be)

Two cooperating parts, split along the internet boundary:

```
        OFFLINE (venue, robust)                      ONLINE (internet assumed)
 ┌───────────────────────────────────┐        ┌──────────────────────────────────┐
 │  cozer desktop app (PySide6/Qt)  │        │  Live web layer                  │
 │  - registration / classes / races │        │  - responsive live results       │
 │  - live lap timing & recording    │  push  │  - machine-readable ORDER FEED   │
 │  - graphical record editor        │ ─────► │    (JSON) for video producers    │
 │  - report generation (PDF)        │ (best- │  - mobile report viewing         │
 │  - robust local persistence       │ effort)│  - Streamlit host (free tier)    │
 └───────────────────────────────────┘        └──────────────────────────────────┘
        headless core (pure Python)                    shared HTML/CSS templates
   analyzer + reports + data model + I/O          (same source → PDF and web view)
```

**Design principles**

- The **headless core** (scoring, data model, report *content*, persistence) is **pure
  Python, no GUI, no network** — fully unit-testable and reused by desktop, PDF, and web.
- The **recording path is the safety kernel**: minimal, isolated, always-persisting; a bug
  in analysis/reporting/GUI must never take it down or lose data.
- **One report template source** (HTML/CSS) renders to **offline PDF** (WeasyPrint) and to
  the **online mobile/live view** — reports and live output share a pipeline.
- Live push is **best-effort and offline-tolerant**: when internet is missing, the app
  keeps recording and queues updates; it resends when connectivity returns.

---

## 4. Technology decisions

| Concern | Old | New (cozer) | Rationale |
|---|---|---|---|
| Language | Python 2 | **Python 3.13+** | Owner requirement; long-term support. |
| GUI | wxPython 2.8 (Classic) | **PySide6 / Qt** | Drop wx; modern, well-maintained, strong Win/Linux. UI kept close to current, improvements welcome. |
| Reports | LaTeX + dvips + viewers | **HTML/CSS → PDF (WeasyPrint)** | Fully **offline**, pure-Python, cross-platform; `@page` controls landscape/portrait; **same templates feed the mobile/live view**. Bar = high quality + same info per page (not pixel-identical). |
| PDF viewing | evince/yap/gsview/acroread | **OS default opener** | No extra viewer dependency. |
| Persistence | cPickle (in-place) | **JSON snapshot + append-only journal (WAL) + atomic writes + rotating backups** | Inspectable, hand-recoverable, crash-safe, power-loss-recoverable. Legacy `.coz` still readable. |
| Subprocess/threads | `os.popen4`, ad-hoc threads | `subprocess` | Removed in Py3; simpler/safer. |
| Install | hand-built wx, MiKTeX, etc. | **mamba env `cozer`** | One command, cross-platform. |
| Live output | LED scripts only | **JSON order feed + responsive web (Streamlit)** | Machine-readable for video producers; mobile viewing. |

**Rejected / deferred**

- **Tectonic** — by default fetches LaTeX packages over the network (cached after first
  use); reliable offline operation needs a pre-warmed cache or a shipped bundle. Given the
  hard offline requirement, **not used**.
- **Markdown reports** — cannot reliably guarantee per-report landscape/portrait, complex
  multi-column result tables, footnote legends, and headers/footers. **Not used.**
- **Mobile recording app** — out of scope (impractical for lap timing).
- **Fallback if WeasyPrint quality is insufficient**: keep LaTeX but ship a full **offline
  TeX Live** inside the conda env (identical output, no per-run downloads).

**Windows installer (done, 2026-07-18):** a single-file native installer built with
`constructor` from `environment.yml` lives in `installer/` and is **CI-verified** on
`windows-latest` (`.github/workflows/windows-installer.yml`): build → silent install →
offscreen smoke test (cozer imports, Qt inits, WeasyPrint renders a PDF) → `.exe`
published as a run artifact. End-user setup: `docs/install-windows.md` (novice-friendly;
Estonian translation drafted: `docs/install-windows.et.md`). **Open item (deferred
until the current bug-hunt stabilizes):** add a release-on-tag workflow step that
publishes the `.exe` as a **GitHub Release** asset named exactly
`COZER-Setup-Windows.exe`, so the guide's direct link
`…/releases/latest/download/COZER-Setup-Windows.exe` gives a public, one-click,
account-free download (replacing the login-gated CI artifact). The same release step
also attaches the cozer **wheel** — the Tier-1 in-app self-update payload (see §6.1).

---

## 5. Transition strategy & repo layout

**Naming decision (2026-07-13):** the original program was moved to **`legacy/`** immediately
(via `git mv`, history preserved), freeing the name **`cozer`** for the new package. `led/`
stays at the repo root as an independent program. In this document, **"legacy"** = the old
Python-2 program under `legacy/`; **"cozer"/"new core"** = the new `cozer/` package.

Repo layout:

```
legacy/               # the ORIGINAL program, moved as-is; must stay Python-2 functional
  cozer/                # old package (analyzer, reports, GUI, data/…)
  cozer.py setup.py install.py *_install.sh MANIFEST.in README.txt
  events/               # historical .coz files (also serve as golden fixtures)
cozer/                # NEW package (built phase by phase)      [created in Phase 0]
tests/                # pytest suite (golden + differential + property-based)
  golden/               # frozen reference outputs generated from legacy
tools/                # reference harness + wx shim (py2.7) + dev utilities
led/                  # independent program (already py3), unchanged
environment.yml       # mamba env `cozer` (py3.13)
environment-ref.yml   # throwaway env `cozer-ref` (py2.7) for goldens
MAINTENANCE_PLAN.md
README.md
```

- Each ported module is accepted only when its **equivalence tests pass** (Section 6).
- **`legacy/` must remain runnable at all times, independent of phase** (never modified by
  the port); Phase 6 only flips the default entry point.

---

## 6. Proof of identical core functionality

The scoring core is pure functions on plain data → **characterization (golden-master) +
differential + property-based** testing.

### 6.1 Run the OLD core headless (no wxPython build needed)

- `analyzer.py` / `reports.py` touch wx only via `prefs` (`Warning`/`Info` → `wx.Bell()`).
- Provide a small **`wx` shim** (`tools/wx_shim.py`, ~30 lines: `Bell`, `Colour`,
  `LogMessage`, minimal constants) so the whole non-GUI core imports under **stock
  Python 2.7** — installable via `environment-ref.yml`, **no wxPython 2.8 build required**.
- Note import-time side effects of `prefs` (creates `log/`, wraps `sys.stdout/err`); the
  harness runs in a subprocess and captures outputs cleanly.

### 6.2 Reference harness → golden fixtures

`tools/refharness.py` (py2.7) loads every `.coz` in `legacy/events/` + `legacy/cozer/data/` and:

- for every `(class, heat)` in `record`: calls `analyze`, `sumanalyze`, `countlaps`,
  `getresorder`, `getsumresorder`;
- for every report type over representative class selections: captures the generated
  **`.tex` text**;
- captures **both return values and input mutations** (old `analyze` mutates `record`:
  appends IR/DNS marks via `insertmark`, sets `racetime`, calls `saveorder`);
- **freezes `time.*`** to a fixed instant (reports embed `time.ctime`).

Outputs are serialized deterministically to `tests/golden/` (canonical JSON for
data; normalized text for `.tex`, ignoring only timestamps).

### 6.3 Differential tests against cozer

- The **same harness logic** runs against `cozer` and must reproduce the goldens
  value-for-value (numbers/dicts by equality; `.tex`/report content by normalized-string
  equality). Dict-ordering differences (Py2 vs Py3) are neutralized by canonical sorting;
  ordering that is user-visible in reports is already `sort`-driven in the code.

### 6.4 Synthetic edge cases + property-based

Generate `.coz` inputs for cases thin/absent in the 8 sample events, push them through
**both** old (py2.7) and new (py3.13), and assert equality:

- empty record, single boat, all-DNS, ties;
- interruption / restart (`r`) / second restart (`R`) / qualification (`q`) / time-trial (`t`);
- penalty laps (PL/PL5/PL8/PL10), lost laps (LL/LL2), disabled marks (negative codes);
- endurance duration-coefficient thresholds (25 / 50 / 75 / 90 %);
- `hypothesis` fuzzing of record sequences.

**Definition of core equivalence:** for all fixtures + synthetic + fuzzed inputs, cozer
returns results equal to old cozer (and equal to the frozen goldens).

### 6.5 Behavior specs from the project wiki (test-design inputs)

The wiki documents domain behaviors the equivalence tests must exercise explicitly:

- **EnduranceRaces** — duration-based scoring, point coefficients (25/50/75/90 %).
- **MultipleDriversPerBoat** — `;`-separated multi-driver names (`get_fullname` in `reports.py`).
- **TimeTrials** — `/T` classes, per-lap timing and ordering.

These map directly onto the synthetic edge cases in §6.4 and the sample events
(`Endurance_EC1_Parnu_2013.coz`, etc.).

### 6.6 UIM rule updates vs the equivalence baseline

The equivalence proof establishes **cozer == legacy as a baseline**. A 2026 rule change is
exactly where we *want* cozer to differ from legacy, so rule updates must be a **separate,
deliberate, versioned delta layer** — not folded into the "identical" guarantee (which would
otherwise force us to replicate outdated rules or invalidate the proof).

**Review surface** — UIM rules live in two places:

- **A. Algorithmic coefficients in `analyzer.py`** (change computed points/places), currently
  magic numbers: `requiredlapscoef=0.70` (311.02.1), `restartrequiredlapscoef=0.35`
  (311.02.7_1), `requiredlaps4pointscoef=0.75` (318.02_1) + the EC2001/318.02_2 `ceil`
  exception, restart full/half points (311.02.7), second restart (311.02.7_4), and endurance
  point coefficients 90/75/50/25 % → 1.0/0.75/0.5/0.25/0 (902.17) plus the 0.4/0.9 leader
  thresholds. Mirrored in `reports.py` (902.17 award notes).
- **B. Rule data templates** `data/rules_UIM.py`, `rules_UIM_2010.py`,
  `rules_UIM_endurance_2013.py` — ~40+ paragraph citations + descriptions, editable in the GUI.

**Design: versioned rules profiles.**

- Extract category-A coefficients into a **single citation-annotated profile module** in
  cozer (e.g. `cozer/rules.py`), not scattered constants.
- Provide a **`legacy/2009` profile** that reproduces historical results exactly — the golden
  equivalence tests (§6) run against it, so the proof stays valid — and a **`UIM-2026`
  profile** reviewed against the 2026 rulebook (category B → new `rules_UIM_2026` template).
- **Each event selects its profile**: historical `.coz` events keep their profile (goldens
  hold); new events use `UIM-2026`.
- **Each 2026 change = one focused edit + one targeted test (new expected result) + owner
  sign-off against the rulebook**, logged as an intentional divergence.

**Sequencing:** the clause-by-clause audit runs as the *Rules review* workstream **after
Phase 2** (so we diverge from a proven baseline), and must be complete before the first live
event run on the new `cozer` (see §6.7).

**Status — circuit Rules review (implemented & pushed, 2026-07-18).** The circuit workstream
is done; the approach evolved from the sketch above:

- ✅ **Category-A coefficients need no change** — the legacy values already match the 2026
  rulebook (circuit 75%-for-points, citation moved 318.02_1 → **317.02**; endurance 40%
  threshold **902.32** and 25/50/75/90 % duration coefficients **902.34/905.34**). So the
  planned `cozer/rules.py` coefficient-profile module was **not** needed; only citations moved.
- ✅ **Category-B rules are composable `.cozj` rulesets** (not a `rules_UIM_2026` Python
  template): `cozer/rulesets/uim_{general,circuit,endurance}_2026.cozj`, combined per event
  via `cozer/app/ruleset.py` (general + circuit / general + endurance).
- ✅ **New 2026 record codes** (`records.py` + analyzer parity + labels/colours): `BC` blue
  card (406.05), `LP2` lose-two-positions (307.01/.02, with analyzer reorder), `PL3/PL4/PL15`
  endurance penalty laps, and the §209 result-outcome codes **`DSQ/DNS/DNR/ACC/DNQ/DNF`**.
- ✅ **Backward compatibility is structural, not a per-event profile toggle.** §209 codes are
  first-class codes recorded at entry time; a pre-§209 event keeps `DQ/DS/NQ/IR` and its
  reports reproduce exactly (reports print the stored code — no remap). §209 codes score
  identically to their pre-§209 equivalents (`DSQ`≡`DQ`, `DNS`/`DNR`/`ACC`≡`DS`, `DNQ`≡`NQ`,
  `DNF`≡`IR`); **all golden equivalence tests stay green.**
- ✅ **Era inferred from the event's own rules** (no explicit profile field): the analyzer
  auto-inserts `DNF`/`DNS` when the ruleset defines them, else `IR`/`DS`; a deprecation hint
  warns when a pre-§209 code is applied in a 2026 event.
- ✅ **`/T` class convention kept** — load-bearing in `racepattern.py` (`get_allowed_heats`/
  `get_heats`), shared with `/Q` (a friendlier UI is future TT work). **Long-lap (319)** needs
  no new code (existing `PL`/`LL` cover the not-taken case).
- ☐ **Endurance §209 + endurance-ruleset finalization** — held (low priority): 902/905 have
  their own Art 31/36 and don't reference §209, so whether §209 governs endurance is a domain
  call. The `uim_endurance_2026.cozj` draft (rules + scoring) exists but is parked.
- ☐ **Full class vocabulary + canonicalization** beyond the seeded circuit classes —
  deferred. Principle: the 2026 rulebook is authoritative; where internally inconsistent we
  define our own canonical (from the class-definition tables), most-recent-source-first.

Tracked as GitHub issues **#8** (time-trial + `/T` UI), **#9** (endurance + §209), **#10**
(class vocabulary + canonicalization), **#11** (record codes/analyzer — done), **#12**
(report §209 — resolved). Commits: `099b3f5`, `84c0b8c`, `ed42cfe`, `7becdcf`, `32995a7`,
`17c6631`.

### 6.7 First event (anchor & timeline)

**Event:** F-500 European Championship 2026 + F-250/F-125/OSY-400/F4/F2/GT-30/GT-15 Baltic &
Estonian (round 2), **Lake Harku, Tallinn**, **24–26 July 2026**; organizer Tallinn Powerboat
Club / Estonian Powerboat Association; held **under the current (2026) UIM rules**.

**Class race patterns** (for fixtures + the UIM-2026 profile; cozer `CrackRacePattern` form):
GT-30/F4/F2/F-500 = 8 laps × 1500 m; GT-15 = 8 × 1100 m; OSY-400/F-125/F-250 = 5 × 1500 m;
qualification heats = 4 laps; **4 heats, all scored**; first-heat grid by time trial;
restarts per **UIM 311**; max 18 boats on course.

**⚠ TIMELINE RISK:** as of 2026-07-13 this event is **~11 days away**. The full port
(Phases 0–6, with equivalence proof, GUI, reports, robustness) **cannot be responsibly
completed and validated** in that window for a live European Championship. **Decision
required** (see §10): the realistic path is to run this event on **legacy** cozer and target
the new `cozer` at a later event.

**Decision (2026-07-13):** proceed for now **assuming the new `cozer` can be ready** for this
event; **revisit this timeline risk ~2026-07-20** with a week of progress to judge against.

### 6.8 Known py2 → py3 porting hazards (equivalence-critical)

Confirmed during Phase 1; the port (Phase 2) must reproduce legacy behavior exactly:

- **`round()` differs**: py2 rounds half **away from zero**; py3 rounds half to **even**.
  The analyzer rounds speeds to 2 decimals (`roundopt=2`), so the port must emulate py2
  rounding rather than call py3 `round()`.
- **Integer division**: legacy relies on py2 `/` doing integer division in places
  (confirmed `1/2 == 0` under py2.7); the port must use `//` where legacy did int division.
- **String convention**: goldens use the `USE_UNICODE=0` path (no str↔unicode re-encoding);
  the port loads legacy `.coz` with `pickle.load(..., encoding='latin-1')` and applies the
  same canonicalization (`tools/golden_io.py`) so text compares identically.
- **Dict ordering**: legacy sorts wherever order is user-visible; goldens canonicalize with
  sorted keys, so py2/py3 dict-iteration differences don't affect comparison.

### 6.9 Future: adopting py3-native idioms (retiring `_py2compat.py`, `.keys()`, …)

`_py2compat` is the equivalence anchor — it reproduces Python-2 numeric/ordering behavior so
the port matches legacy exactly. Elimination cost differs by part:

- **`round2`** (round-half-away-from-zero): replacing with py3-native `round()`/Decimal changes
  results only for *exact half* cases — a **deliberate divergence**. Measurable: scan all
  real+synthetic golden values for where the two rounding rules differ (likely few/none).
- **`py2_cmp` / `py2_sorted`** (mixed int/str ordering): reducible to a small explicit py3-native
  **sort key** (numbers-before-strings, matching py2) with *no* behavior change (tests stay
  green), or removed by normalizing ids to one type (a divergence).
- **`.keys()` iterations**: some are redundant (`for k in d.keys()` ≡ `for k in d`) and can be
  dropped freely (tests stay green); others exist only for legacy error-parity (e.g.
  `sumanalyze` uses `res[h].keys()` so a `None` heat raises `AttributeError` like legacy rather
  than `TypeError`) — removing those is a deliberate divergence, like the items above.

**Plan:** keep `_py2compat` through the equivalence baseline; once coverage is ~100% and the
synthetic corpus exists, produce an **effort/impact report** quantifying exactly which results
would change under native semantics, then decide per the versioned-profile model (§6.6):
legacy profile stays faithful, a modern profile may adopt native semantics.
*(Owner asked to understand this effort — revisit after the Phase 2 coverage work.)*

---

## 7. Phased plan

Each phase ends with an **owner approval gate**. **`legacy/` must remain runnable at all
times, independent of phase** (including after cutover) — it is never modified by the port.

**Task tracking:** for now this plan (esp. the phase checklists) *is* the task list. Switch
to **GitHub issues** later, once the project is far enough along that issue tracking beats
the single-document view; keep the plan as the living design doc.

### Phase 0 — Scaffolding & environment
- Create mamba env **`cozer`** (py3.13) and **`cozer-ref`** (py2.7).
- Verify **PySide6** and **WeasyPrint** resolve on **win-64 and linux-64** (and py2.7 ref env).
- Scaffold `cozer/`, `tests/`, `tools/`; add `environment.yml`, `environment-ref.yml`.
- Set up pytest + CI (GitHub Actions: Linux **and** Windows).
- **Deliverable:** reproducible env + green empty test run on both OSes.

### Phase 1 — Lock the core (reference = legacy)  *(in progress)*
- ✅ `tools/wx_shim.py` (fake wx for py2.7), `tools/golden_io.py` (shared py2/py3
  canonical JSON), `tools/refharness.py`.
- ✅ Generated `tests/golden/analyze/` from the legacy core over all events
  (10 files, 115 class/heat records: `analyze` + input mutations + `resorder` +
  `countlaps`); verified reproducible (regeneration is a no-op diff).
- ☐ Extend goldens to `sumanalyze` and report `.tex` text; add synthetic edge
  cases (interruption / restart / qualification / time-trial / endurance thresholds).
- **Deliverable:** frozen equivalence baseline (analyzer core done; extensions pending).

### Phase 2 — Port headless core to cozer  *(in progress)*
- ✅ `cozer/_py2compat.py` (round2, py2_cmp/py2_sorted), `cozer/records.py`
  (codes + insertmark + gettimes), `cozer/analyzer.py` (analyze / analyze_endurance /
  countlaps / getresorder / get_racetime / transpose / ceil).
- ✅ Legacy `.coz` read in py3 via `pickle.load(..., encoding='latin-1')`.
- ✅ **Differential proof green**: ported analyzer reproduces the legacy goldens
  byte-for-byte across **all 10 events / 115 class-heat records** (analyze + input
  mutations + resorder + countlaps).
- ✅ Coverage (`pytest-cov`, branch): **100% of statements, 98% overall** across the ported
  core. 16 synthetic edge-case fixtures added, validated **through legacy** — the differential
  proof now covers the rare rule paths (LL/LL2/PL*/DQ/YC/RC/NT/Q/NQ, restart r/R, qualification,
  time-trial, endurance point tiers) too. Remaining ~2% are benign partial branches
  (note-dedup / guard fall-throughs); dead legacy branches carry justified `# pragma: no cover`.
- ✅ Ported data-model logic: `cozer/classes.py` (predicates) + `cozer/racepattern.py`
  (`crack_race_pattern`, `get_classes`, `get_allowed_heats`, `get_heats`) — proven equivalent
  across all 10 events + 9 synthetic model cases; **100% statements / 99% overall**. Enabled by
  a **catch-all `wx` shim** so the harness runs the *actual* legacy MainFrame methods headless
  (analyze goldens verified byte-identical after the shim swap).
- ✅ Ported `sumanalyze`/`getsumresorder` (final standings across heats) — proven equivalent
  across all events, incl. the empty-scoring-system crash path (a `.keys()` faithfulness fix
  the differential test caught). **Headless scoring + race-model core is now fully ported and
  proven; 100% statements / 99% overall, 42 tests.**
- ✅ `reports` **content** generation — delivered in Phase 4 (all 9 reports).
- **Deliverable:** differential tests green ⇒ **core equivalence proven & automated** (analyzer done).

### Phase 3 — Robust persistence  *(library core done)*
- ✅ `cozer/store.py`: atomic snapshot writes (`tmp` + `fsync` + `os.replace`; atomic on
  Win + Linux) with rotating backups; append-only **journal** fsync'd per recorded mutation;
  **crash-replay recovery** on open (snapshot + journal), tolerant of a torn final line;
  human-readable JSON snapshot; legacy `.coz` import + lossless JSON codec. It is the *safety
  kernel* — recording durability does not depend on analysis/reports/GUI.
- ✅ **Tests (55 total; `store.py` 100%):** codec round-trip + analyze-through-store
  equivalence, atomic-write failure (original preserved, no temp leak), **power-loss journal
  replay**, truncated-journal tolerance, backup rotation.
- ✅ Wired the store into the recording path (Phase 5c/5d): the Timer journals each lap and
  Edit Records journals each saved mark/edit as it happens; autosave available.
- **Deliverable (met at the library level):** power loss at any instant ⇒ all journaled data recovers.

### Phase 4 — Portable report rendering (offline)  *(pipeline + Full Final done)*
- ✅ Offline HTML/CSS → PDF pipeline (`cozer/reports/render.py`, WeasyPrint); per-report
  `@page` orientation; `table-layout:fixed` + a colgroup summing to 100% so tables always fit
  the page width (numbers never split — a `&#8203;` break point only at the `/`).
- ✅ `cozer/reports/latexish.py`: decodes legacy LaTeX in free text (accents like `\v{c}`→č,
  `\\`→line break, `_`/`^`→sub/sup, `~`→nbsp) to safe HTML — real `.coz` files carry LaTeX.
- ✅ **Full Final** (landscape) built from the proven core (`build_full_final`), **owner-signed-off
  on quality**; tests: LaTeX decoder, result formatting / break-at-slash, model assembly vs
  `sumanalyze`/`getsumresorder`, landscape + page-fit rendering.
- ✅ Short Final (portrait), Participants + Drivers-Meeting Check List — with **localized
  labels** (en/et, `cozer/reports/labels.py`, extracted from the legacy `*_cozer.tex`) and
  shared helpers (`cozer/reports/common.py`).
- ✅ Intermediate (portrait), Laps Counter Protocol (portrait), Endurance Full Final
  (landscape). Coverage swept — 77 tests, 97% overall (reports modules 90–100%, core 98–100%).
- ✅ Info Letter (localized bio form) + Registration Letter (bilingual EN/ET entry form),
  ported from the legacy letter macros. **All 9 reports done** (78 tests, 96% overall).
- ✅ Replaced `os.popen4`/viewers with the OS default opener — the Reports tab (Phase 5a)
  opens the produced PDF in the OS viewer.
- **Gate:** hardest report (Full Final) signed off ✅ → the rest built on the same pipeline.

### Phase 5 — GUI (PySide6) + robustness hardening  *(done)*
- Rebuild the notebook UI (General Information / Timer / Edit Records / Reports / Log) in Qt,
  staying close to today's layout and workflow (improvements welcome).
- ✅ **5a (foundation):** `cozer/app/` PySide6 main window backed by the crash-safe store
  (open legacy `.coz` / new `.cozj`, atomic save); event-information form; a **Reports tab**
  that renders any of the 9 reports to PDF and opens it in the OS viewer (this replaces the
  legacy `os.popen4`/viewer calls). `python -m cozer` launches it; offscreen headless smoke
  tests run in CI.
- ✅ **5b:** data entry under the General Information tab — event fields plus **Classes &
  Participants** (one subtab per class: its race pattern + a participant spreadsheet
  Boat#/Name/Surname/From, boat-# unique within a class, From-column autocomplete),
  **Races** (race list + class/heat grid), and **Rules** (scoring system + class-name
  vocabulary + penalty rules). Edits are made in place on eventdata; Save snapshots via the
  store. Add-Class is a strict picker over the rule-set catalog and grid input is validated
  (see 5e).
- ✅ **5c:** live **Timer** — race selector + per-boat buttons; each click records a lap
  through the store (append + **fsync to the journal immediately**), so a power loss loses
  nothing; autosave toggle; button colors carry state (white=idle / green=in-progress /
  magenta=finished). Verified: the recorded data feeds the proven analyzer.
- ✅ **5d:** **Edit Records** — a *graphical timeline editor* faithful to legacy
  `EditWin1`/`RecordEditor`: one row per boat (results order) with lap marks at cumulative
  time and event marks at absolute time, the analysed result in each row header, a draggable
  red race-stop line, right-click-at-a-time → rules-by-code menu (insert mark there) plus
  Insert-lap / Enable-Disable / Delete on the nearest mark, and zoom. Every edit committed
  through the store (journaled). Geometry + edit ops (`mark_positions`, `insert_lap_split`,
  `toggle_nearest`, `delete_nearest`) are pure/unit-tested; the widget paints them and turns
  mouse events into them. **Log** pane captures status messages. Post-race edits are now
  **buffered** (a per-heat draft) and written only on "Save changes" — leaving a modified
  record prompts save/discard/cancel, so an accidental finish-line drag can't silently
  overwrite a completed race; the row-header column is frozen (always visible when zoomed).
- ✅ **5e (rule sets, patterns, validation, CLI, reporting):**
  - **Composable rule sets** on the ordinary `.coz`/`.cozj` structure — no new format. Two
    additive `eventdata` keys: `kind` (`"event"`/`"ruleset"`) and a `classnames` vocabulary
    (the `classes`/`participants` representations are unchanged). A *ruleset* file defines only
    scoring / class names / rules and opens in a **restricted editor**; an event **imports**
    rulesets **non-destructively** (adds new class names + rules, fills empty scoring, never
    overwrites). Bundled UIM rulesets ship under `cozer/rulesets/`; opening a legacy `.coz`
    seeds class names from its classes. `python -m cozer f1.cozj f2.cozj …` accumulates
    several files (rulesets → a fresh event, or applied to one event file), reporting any
    conflicts to the terminal + Log.
  - **Race-pattern dialog** — structured circuit fields (first/other lap, laps, heats, scored)
    + live preview + an editable raw string for endurance/exotic patterns; the internal
    pattern string is unchanged (parsed by `crack_race_pattern`).
  - **Input validation** (parity with legacy `ValidateTable`; *cozer suggests, the organizer
    decides*): Races class/heat are editable dropdowns offering the defined classes and the
    valid next heats from `get_heats` (encoding the `N`→`N+1` and `N`→`Nr`→`NR` ordering);
    an undefined or duplicated class is **hard-rejected**, an out-of-order heat is advisory;
    duplicate `(action, paragraph)` rules are advisory; blank paragraphs and status markers
    (Q/NQ/IR/DS) are never flagged.
  - **Crash & bug reporting** — uncaught exceptions and in-app bug reports file to the cozer
    GitHub issues via **device-flow OAuth**, attaching the event/journal for reproduction;
    offline reports queue and submit on sign-in. Feeds the §6.1 self-update loop.
  **GUI + app suite runs green in CI (offscreen, Linux + Windows).** UX polish welcome after
  the live trial.
- ✅ **UX:** friendlier race-pattern editor — the cryptic
  `NofHeats*(NofLaps*LapLength+..):Scored` syntax now has a structured dialog with a live
  preview (5e), keeping the internal pattern-string representation unchanged
  (parsed by `crack_race_pattern`).
- **UX:** apply a **color scheme** (the app is currently default black-and-white). Reuse the
  legacy palette from `legacy/cozer/prefs.py` — `edit_bg`/`warning_bg`/`disableedit_bg` for
  cells, and `mycolors`/`reccodecolours` for the Timer button states (waiting/coming/late/
  finish) and record-mark colors — via a Qt stylesheet, so the UI is familiar and the timing
  colors stay information-carrying. *(Owner requested; applied in 5c — app-wide tint +
  Timer button states; further polish/record-editor colors possible.)*
- **Safety kernel isolation:** the timing/recording subsystem is separated and guarded so a
  bug in any page/report/action is caught, logged, and surfaced **without crashing the app
  or losing data**. Autosave **on by default**.
- **Deliverable:** feature-parity desktop app; GUI smoke tests + manual test checklist
  against the sample events.

### Phase 6 — Cutover
- Full **mock event end-to-end**, in two complementary forms:
  - ✅ **Automated e2e integration tests** (`tests/test_e2e.py`, CI): (1) a from-scratch run —
    new event + store → import rulesets → classes/participants/patterns/races → record laps
    through the Timer/store (journaled) → power-loss journal-replay recovery → edit records +
    save → render **all 9 reports**; (2) **wc2000 updated to 2026 rules** (real data, class
    names remapped to the 2026 catalog) → analysis comparability + snapshot round-trip +
    representative reports; (3) **full heat re-enactment** — rebuilds a real wc2000 heat
    *purely through button clicks + Edit Records* (the recording paths, not by initialising
    the structures) and asserts it matches the historical record exactly. Catches cross-part
    regressions the per-part unit tests can't. *(Extending the re-enactment to every heat is a
    future slow test.)*
  - ☐ **Manual acceptance pass** — a human runs the same flow for what a test can't judge:
    UX flow and report *quality/appearance*.
- ☐ **User guide / tutorial** *(follow-up to the e2e test)* — a non-technical-operator
  walkthrough of the *same* mock-event scenario the e2e test drives, with step screenshots
  **generated from that flow** (headless render tooling) so they auto-refresh as the UI
  changes. Written once the UI settles near cutover; the e2e test defines the canonical
  scenario it reuses.
- Make the new `cozer` package the **default entry point** (console script / launcher).
- ☐ *(low priority — basically already verified)* Confirm **`legacy/` still runs** under
  Python 2 + wxPython 2.8 + MiKTeX/LaTeX (moved in Phase 0, not Python-3-ified; already built
  and run headless under Xvfb for reference screenshots). Its install scripts (`setup.py`,
  `install.py`, `Ubuntu_install.sh`, `conda_install.sh`, `README.txt`) and the captured
  install recipe (below) stay with it, so the last-known-good program remains runnable if the
  new work is unfinished at the next event.
- **Deliverable:** new `cozer` is the default; `legacy/` still runs the old program;
  documented install for Win + Linux.

#### 6.1 Distribution & in-app self-update *(owner-agreed direction; build during cutover)*

Non-technical Windows users must **never touch `pip`, `mamba`, or a shell** — every update
happens behind a button. Chosen model — a **thin stable runtime** + an **updatable cozer
code payload**, in **two tiers** (updated 2026-07-18 to match the `constructor` installer;
supersedes the earlier PyInstaller + codeload-tarball sketch):

- **Runtime** (Python + PySide6 + WeasyPrint + native libs — rarely change): the
  **`constructor` Windows installer** (§4; `installer/`) — a self-contained conda bundle
  installed once. (Linux: the conda env.)
- **cozer code** (`cozer/` package — **pure Python**, changes often incl. in-event hotfixes):
  a small **wheel** installed into the bundled env.

**Tier 1 — cozer-code update (frequent, light, fully in-app):**
- Each fix/feature ships as a **cozer wheel** attached to a **GitHub Release** (KBs–MBs).
  Cutting these is cheap → expected to be **frequent**.
- `Help → Check for updates…` compares `__version__` to the latest release, downloads the
  wheel over HTTPS (reusing the `crashreport` GitHub transport; auth via the existing
  device-flow sign-in if the repo is private), **verifies it imports**, then runs
  `pip install --upgrade` into `sys.prefix` **programmatically behind the button — the user
  never sees pip**, keeps the previous version for **instant rollback**, and prompts restart.
  The recording journal makes restart safe.
- Closes the loop **crash-report → push fix → publish wheel → operator "Update to latest" →
  restart**, with no new installer. (Optional zero-release hotfix channel: install the wheel
  from `main`'s latest CI run.)

**Tier 2 — full runtime update (rare):**
- Only when a release also bumps the **bundled native deps** (Python/Qt/WeasyPrint). Then the
  operator downloads the **new installer** and reinstalls (still a double-click; no shell).
- Release metadata carries a **needs-reinstall / minimum-runtime** marker; if a wheel would be
  incompatible with the installed runtime, the in-app updater says "download the new installer"
  instead of pip-updating.

**UI / safety (both tiers):** `Help → Check for updates…` + `Help → About` (version); a
**dismissible startup banner** that is *specific* — highlight when a new version fixes an issue
**this operator reported** (submitted issue URLs stored in config). **Suppress the banner
during an active timing session; verify-before-swap; never update mid-race.** Reuses the
`crashreport` GitHub transport.

**Version check** compares `__version__` to the latest release tag.

#### Current (legacy) install — captured from the project wiki (to preserve)

- **Windows** (`WindowsUsage`): Python **2.7.3**; wxPython **2.8.12.1**
  (`wxPython2.8-win32-unicode-2.8.12.1-py27.exe`); **MiKTeX 2.9** (Basic); GitHub Desktop
  to clone; Adobe Reader optional (add the dir containing `AcroRd32.exe` to `PATH` for PDF
  printing, else Yap prints DVI). Run by double-clicking `cozer.py`.
- **Linux**: `Ubuntu_install.sh` (hand-builds wxPython 2.8) + system `latex/dvips/gv/evince`.
- wxPython 2.8 is **not** on conda-forge, so the legacy env cannot be a clean mamba recipe;
  its build instructions stay documented with `legacy/`.

### Phase 7 — Live output (internet assumed)
- **First increment (priority): live competitor-ordering feed.** During a race, publish the
  current ordering as **machine-readable JSON** at a stable URL so external web apps (e.g.
  video producers) can grab it, plus a **responsive human view**.
- **Offline-tolerant push:** desktop app publishes best-effort; queues while offline, resends
  on reconnect. Recording never blocks on the network.
- **Host:** **Streamlit** viewer designed to fit the **free tier** (mind idle-sleep, resource
  caps, public apps); the JSON feed kept small/cacheable for machine consumers.
- Later: full live results, integration with `led/` displays, mobile report viewing.

---

## 8. Environments

`environment.yml` (draft — versions verified in Phase 0):

```yaml
name: cozer
channels: [conda-forge]
dependencies:
  - python=3.13
  - pyside6            # desktop GUI (Win + Linux)
  - weasyprint         # HTML/CSS -> PDF, offline
  - pip
  - pytest
  - hypothesis         # property-based edge cases
  - pymupdf            # extract PDF text for report equivalence tests
  # Phase 7 (live): streamlit  (kept optional / separate to stay in free tier)
```

`environment-ref.yml` (throwaway, for goldens):

```yaml
name: cozer-ref
channels: [conda-forge]
dependencies:
  - python=2.7         # runs OLD core headless via tools/wx_shim.py
```

**Solve status — VERIFIED 2026-07-13** (dry-run solves from the Linux server, no install):

| Env / platform | Result | Key versions |
|---|---|---|
| `cozer` / **linux-64** | ✅ resolves (166 pkgs, ~405 MB) | python 3.13.14, pyside6 6.11.1, qt6-main 6.11.1, weasyprint 69.0, pymupdf 1.28 |
| `cozer` / **win-64** (cross-solve `CONDA_SUBDIR=win-64`) | ✅ resolves | pyside6 6.11.1 (py313), qt6-main 6.11.1, weasyprint 69.0, pymupdf 1.28, python 3.13.14 |
| `cozer-ref` / **linux-64** | ✅ resolves (23 pkgs) | python 2.7 |

Windows package availability is confirmed **without a Windows machine** via cross-platform
solves. Fallbacks (unlikely needed): py3.12, pip wheels; for reports, offline TeX Live.

**Known setup gotcha — GUI segfault in `libfontconfig` on launch.** `python -m cozer` may crash
with `Segmentation fault` whose gdb trace bottoms out in `FcCharSetFindLeafForward` /
`FcCharSetHasChar` (Qt text shaping during `show()`). Cause: conda's `libfontconfig` reading a
fontconfig cache written by a *different* fontconfig version (the env's `fonts.conf` shares
`~/.cache/fontconfig` with the system). **Fix (confirmed on the owner's laptop, 2026-07-14):**
`rm -rf ~/.cache/fontconfig ~/.fontconfig "$CONDA_PREFIX"/var/cache/fontconfig/* && "$CONDA_PREFIX/bin/fc-cache" -rf`.
Validated fallback: set `FONTCONFIG_FILE` to an env-only config (env fonts + a private cachedir).
Deferred (not landed): opt-in `COZER_SAFE_FONTS=1` launcher + `faulthandler` in the entry point.

### 8.1 Development & testing topology

| Where | Runs | Purpose |
|---|---|---|
| **Linux server (this session, headless)** | headless core, pytest, golden/differential tests, WeasyPrint PDF rendering, persistence, GUI tests via `QT_QPA_PLATFORM=offscreen` | primary development; no display needed |
| **Linux laptop** | full `cozer` env locally; **code mounted from the server via sshfs**; runs the PySide6 GUI on the laptop's display | interactive GUI testing |
| **Windows (later, VirtualBox)** | full `cozer` env | final Windows verification; availability already de-risked by the win-64 cross-solve |

Note: over sshfs the **code** is shared but the **environment is local to each machine** —
the laptop needs its own `cozer` env (below). Headless GUI tests on the server/CI use Qt's
offscreen platform plugin.

**Slow GUI startup over sshfs.** Running `python -m cozer` directly off the sshfs mount is
slow because every `cozer/*.pyc` import is a network round-trip (importtime confirmed: even an
empty `cozer/app/__init__.py` took ~0.9 s; PySide6, local, is ~80 ms). If dev startup speed
matters, run from a **local checkout** instead of the mount. End users install locally, so they
never hit this. `python -m cozer path/to/event.coz` opens an event on launch (handy for
testing).

### 8.2 Laptop GUI setup (Linux laptop)

```bash
# 1. Mount the server's cozer working copy (adjust user@host and paths)
mkdir -p ~/mnt/cozer
sshfs user@server:/home/pearu/git/pearu/cozer ~/mnt/cozer

# 2. Create the same env locally from the repo's environment.yml
mamba env create -f ~/mnt/cozer/environment.yml   # creates env `cozer`
mamba activate cozer

# 3. Run the GUI against the mounted code
cd ~/mnt/cozer
python -m cozer            # (entry point available from Phase 5)
```

`environment.yml` is the single source of truth used on server, laptop, and Windows.
(These instructions are committed to the repo in Phase 0 alongside `environment.yml`.)

---

## 9. Robustness design (details)

- **Atomic snapshot save:** serialize → write `*.tmp` → `fsync` → `os.replace` over target.
  The real file is never partially written.
- **Journal (WAL):** during timing, append each event `{t, class, heat, id, code, data}` to
  `<event>.journal`, fsync per append. On startup, if a journal is newer than the snapshot,
  **replay** it to recover. Truncate/rotate the journal after a successful snapshot.
- **Backups:** keep rotating `*.bak1..N` snapshots; never overwrite the last good backup in place.
- **Canonical JSON** form is human-readable and hand-recoverable; legacy `.coz` remains supported.
- **Error isolation:** every page/report/user action wrapped so exceptions are logged and
  shown, but the app and the recording kernel keep running. Prefer explicit exceptions over
  bare `except`; remove `exec`/backtick-repr during the port.
- **Recovery drills** are part of the test suite and the Phase 6 mock event.
- **Crash reporting** (`cozer/app/crashreport.py`): an unhandled error (via `sys.excepthook`,
  which PySide6 routes GUI-slot exceptions through) is always captured to a local JSON crash
  report (traceback + context + full event snapshot) next to the event, so nothing is lost and
  the app keeps running. When signed in to GitHub (in-app **device-flow** login) it auto-files
  the report as a `needs-triage` issue titled `[<date>/<venue>] Crash: …`, deduped by a
  traceback fingerprint; offline reports queue and drain when back online. All network calls go
  through an injectable transport (stdlib `urllib`, no new dep) and are unit-tested without the
  network. The GitHub OAuth App is registered (public client id baked into `crashreport.py`, no
  secret — device flow needs none); **Help → Sign in to GitHub** (device-flow dialog) and
  **Help → Report a bug** are wired, and queued reports drain on sign-in. Future: AI triage of
  `needs-triage` issues, and an in-app self-update UI (Help → Check for updates) that ties into
  this — notify the user when a version fixing *their* reported issue is available.
- **Fast startup:** `cozer.reports` (hence `weasyprint`) is imported lazily on first report, not
  at launch; a `QSplashScreen` covers the remaining window setup.

---

## 10. Risks & open items

- **⚠ First-event timeline** — the first event (§6.7) is **24–26 July 2026**, ~11 days from
  2026-07-13; the full port cannot be finished/validated by then. **Recommended:** run that
  event on **legacy**; target the new `cozer` at a later event. **Decision 2026-07-13:**
  proceed assuming new `cozer` can be ready; **revisit ~2026-07-20**.
- **PySide6/WeasyPrint on py3.13/Windows** — ✅ verified 2026-07-13: env builds on linux-64,
  the win-64 solve resolves, and CI "create env + import" passed on both Linux and Windows.
- **WeasyPrint typography vs LaTeX** — mitigated by the Phase 4 sample-first gate; fallback
  to offline TeX Live if quality parity fails.
- **Unicode handling** — old normalize/denormalize is asymmetric (decode latin-1 / encode
  UTF-8); Estonian names (õ ä ö ü) are common. cozer targets correct UTF-8 throughout;
  any intentional divergence from old (buggy) behavior is flagged for approval and covered
  by tests.
- **Old `analyze` mutates input** — captured explicitly by the golden harness.
- **Streamlit free-tier limits** — design the feed/viewer to fit; keep the machine feed a
  small, cacheable JSON independent of the viewer app.

---

## 11. Definition of done (cutover criteria)

1. All core-equivalence tests green (goldens + synthetic + fuzzed) on Linux **and** Windows.
2. All 9 reports render offline at owner-approved quality with correct orientation.
3. Power-loss and bug-isolation recovery drills pass.
4. A full mock event runs end-to-end in cozer.
5. One-command mamba install works on a clean Windows and a clean Linux machine.
6. Live ordering JSON feed publishes during a race and is consumable by an external app.

---

## 12. References

- **2026 UIM Circuit Rulebook** (authoritative for upcoming events; drives the §6.6 rules
  review): <https://www.uim.sport/Documents/RuleBookRelease/RuleBookRelease143/2026%20UIM%20Circuit%20Rulebook%20-%20republished%20on%2028.05.26.pdf>
- **Project wiki** (behavior specs & legacy install): `EnduranceRaces`,
  `MultipleDriversPerBoat`, `TimeTrials`, `WindowsUsage`, `Schedule Tallinn 2024` —
  <https://github.com/pearu/cozer/wiki>
- **Legacy install recipe** captured in Phase 6 above (Windows: Py 2.7.3 / wxPython 2.8.12.1
  / MiKTeX 2.9 / Adobe Reader; Linux: `Ubuntu_install.sh`).
```
