# Reports — UIM-compliant result reporting per race kind

> **Status:** draft / audit + plan (seeded 2026-07-20 by session `7948e787` from a
> report-vs-rulebook audit). Reports are the active domain of session `b76f2173`; this
> doc is the shared plan + decision log, mirroring `PHASES.md`. Nothing here is
> implemented yet. Owner-call items are collected in §7.

## 1. Motivation

cozer's result documents must satisfy **UIM 209** (required result content) plus the
per-kind rules — **305.04.02** (time trial), **305.04.03** (qualification), **317**
(finals scoring). A 2026-07 audit of the report builders (`cozer/reports/final.py`,
`intermediate.py`, `laps.py`, `endurance.py`, `common.py`, `labels.py`) against those
rules found several discrepancies, one of them a correctness bug. This document records
the requirements, the current behaviour, the gaps, and the plan — so both sessions and
the owner work from one reference, the way `PHASES.md` served the phases refactor.

## 2. Report kinds and the per-phase model

Reports are **per phase** (see `PHASES.md` §4: each phase owns its report set; the PDF
filename carries the phase kind). Current report set (menu in `cozer/app/main.py`):

| Report | Builder | Serves phase kind(s) |
|--------|---------|----------------------|
| Participants | `build_participants` | (entry list, kind-agnostic) |
| Intermediate | `build_intermediate` | any single heat; **istt mode** → time trial |
| Full / Short Final | `build_full_final` / `build_short_final` | circuit (finals) |
| Full / Short Final (legacy) | `*_legacy` | byte-faithful legacy output |
| Endurance Full Final | `build_endurance_final` | endurance |
| Laps Protocol | `build_laps_protocol` | any (per-lap crossing tally) |
| Check List / Letters | `build_checklist` / `build_*_letter` | operational, kind-agnostic |

**There is no qualification report** — a qualification phase currently falls through to
the intermediate/finals builders as circuit-style tables (see §5.2).

## 3. UIM requirements — the compliance checklist

### 3.1 Common to every result (209 "Posting of the Results")

Each posted race/heat result must include, **per boat/driver**:
- position, boat number, driver first name + surname, **nationality** (IOC-3 code or
  full country name), **time (or speed) / laps**, points.

And per document:
- header: UIM title, class name, race/heat number, race date, venue;
- **restart notation:** letter `R` after the race/heat number for a restart; `R2` for a
  last-heat second restart;
- **all** entered-and-accepted drivers listed; non-qualifiers marked **DNQ**;
- §209 outcome codes where applicable: **DNS / DNF / DNR / DSQ / ACC / DNQ**.

### 3.2 Time trial — 305.04.02

Result = **best full-lap time**. The ranking metric is a *time* (fastest single complete
lap). The time-trial report is the "best-time list"; it also feeds finals grid order via
307.01 (dead-engine jetty positions from time-trial times).

### 3.3 Qualification — 305.04.03

Qualification heats rank boats; the top N per the phase's `qualifiers` advance (**Q**),
the rest are **DNQ**. The qualification report must show, per qheat, the 209 result
content **and** the Q/DNQ advancement outcome.

### 3.4 Finals / circuit — 317

Multi-heat: per-heat results plus aggregate points (317 scoring; 311 restart handling
per kind). All 209 common content applies per heat and in the summary.

## 4. Current state — what each report emits today

- **Full / Short Final** (`final.py`): columns = Place · Name (+ sub-rows for co-drivers)
  · **From** · No. (boat#) · per-heat [Res, Pts] · Summary [Res, Pts]. The per-heat *Res*
  cell shows `avgspeed/maxlapspeed` (and `…/NL` **only** when a boat is short of full
  laps) plus footnoted §209 note-codes; Summary *Res* = best `avgspeed/maxlapspeed`.
  Renders the phase-kind subtitle and the **DNQ tail** (every entered non-finalist, 209).
  Header meta = title · venue · date (officer/secretary in footer).
- **Intermediate** (`intermediate.py`): single heat (or multi-heat summary). Non-TT →
  [Res, Pts]. **istt (time-trial) mode** → columns Place · Name · From · No. · **Lap
  Time**, where Lap Time = analyze `laptime`. Shows start time.
- **Laps Protocol** (`laps.py`): per-lap crossing tally.
- **Endurance Full Final** (`endurance.py`): laps completed within the duration.

## 5. Discrepancies (audit 2026-07)

### 5.1 Time trial

- **[BUG] Lap Time is blank (`-`) on the common 1-lap heat.** The istt column reads
  analyze `laptime`, which is **0** on a single-lap heat, so the report prints `-` — even
  though `maxlapspeed` is a valid best-lap figure (verified: 1-lap TT → `laptime=0`,
  `maxlapspeed=180.0`, cell renders `-`). The one report meant to be a "best-time list"
  cannot show a time on practice/solo runs. → **P1**, see §6.

### 5.2 Qualification

- **No qualification report exists.** Nothing renders a qual ranking with per-qheat
  **Q/DNQ** advancement; a qualification phase falls through to intermediate/finals as
  circuit-style tables. Biggest gap. → **P1**, see §6.

### 5.3 Finals / circuit (and shared across kinds)

- **Nationality (209).** Reports show a **From** column (label "Klubi" = *club* in ET),
  backed by the free `participants[i][3]` field that events fill with club **or** city
  **or** nationality. 209 requires *nationality* specifically (IOC-3 / country). There is
  even an unused `Country` ("Linn" = *city*) label. Nationality is not a guaranteed,
  distinctly-labelled field. → **P2 + owner call D1**.
- **Restart notation (209).** Heat headers show the raw heat id `1r` / `1R`. 209 wants
  heat-number + `R` (first restart) and `R2` (last-heat second restart). Presentation
  mismatch. → **P2**.
- **Laps per result (209).** Finishers get speed only; the completed-lap count appears
  (`…/NL`) **only** when a boat is short. 209 says "time (or speed) / **laps**". Defensible
  (full count implicit) but strictly under-specified. → **P3 + owner call D3**.

### 5.4 Not discrepancies (recorded to avoid re-litigating)

- **Speed instead of time in finals** — 209 explicitly allows "time (**or speed**)"; OK.
- **Header meta** — title / class / heat no. / date / venue all present; OK.
- **§209 outcome codes** — DNS/DNF/DSQ/ACC/DNQ render as footnoted note-codes; OK.

## 6. Plan (prioritized)

| # | Fix | Priority | Notes |
|---|-----|----------|-------|
| 1 | Time-trial best-lap **time** | **P1** (bug) | Derive from the best lap's crossing interval, or `lap_length / maxlapspeed`; stop trusting analyze `laptime` (0 on 1-lap). |
| 2 | **Qualification report** (new kind) | **P1** (gap) | 209 result content per qheat + **Q/DNQ** advancement; hooks `qualification.classify`; slots into the per-phase report model. |
| 3 | Restart `R` / `R2` display | P2 | Map heat-id `1r`→`1R`, last-heat `1R`→`1R2` in heat headers (context-aware). Presentation-only. |
| 4 | Nationality column | P2 | Depends on **D1**. |
| 5 | Laps for all finishers | P3 | Depends on **D3**. |

## 7. Decisions (owner calls — OPEN)

- **D1 — Nationality data model.** Is `participants[i][3]` *the* nationality field (then
  relabel the column "Nationality" and validate IOC-3/country), or do we add a distinct
  nationality field separate from "From/club"? 209 requires nationality specifically.
- **D2 — Time-trial metric. DECIDED (owner, 2026-07-20): best-lap _time_.** 305.04.02 is
  specific about time. Derive it from the best lap's crossing interval (or lap length ÷
  best-lap speed) — *not* analyze `laptime`, which is 0 on a 1-lap heat. Ships with the §5.1
  P1 fix when reports work resumes.
- **D3 — Laps for all finishers.** Show the completed-lap count for every result, or keep
  the current "only when short" (`NL`) convention?

## 8. Open questions

- Does the qualification report show one table per qheat, or a combined ranking with a
  Q/DNQ column? (Ties to how `classify` exposes per-qheat vs aggregate order.)
- Restart `R2` is defined by 209 only for the *last heat's* second restart — does the
  display mapping need finals-context (which heat is "last") that the report has?
- Legacy byte-faithful reports (`*_legacy`) are intentionally frozen — do any 209 fixes
  apply to them, or only to the native builders?

## Change log

- **2026-07-20** — Initial draft: audit of the four native report builders vs UIM 209 /
  305.04.02 / 305.04.03 / 317; discrepancies (§5), plan (§6), decisions (§7). Seeded by
  `7948e787`; handed to `b76f2173` (reports owner) to own/extend.
- **2026-07-20** — Owner parked reports for now (still testing 3c-2); committing this plan
  for later. Owner decided **D2 = best-lap time**. D1 / D3 remain open.
