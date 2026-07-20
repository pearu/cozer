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

- **[FIXED 2026-07-20] Lap Time on a time trial.** `analyze` now reports `laptime` as the
  **best (max-speed) lap's measured time** (was `lapstime[-1] - lapstime[-2]` — the *last* lap,
  and `0` on a single-lap heat, so a 1-lap TT showed `-`). Per **D2** this is the best-lap
  *time*, and it is picked automatically. NB legacy was **not** buggy here: the TT operator
  manually disabled every lap except the single fastest one so one lap remained; the new cozer
  makes that manual curation unnecessary (a deliberate divergence from legacy — the synthetic
  analyze golden's 1-lap TT was re-anchored `0 → 20.0`).

### 5.2 Qualification

- **[FIXED 2026-07-20, per-qheat] Intermediate report is now qualification-aware.** For a
  qualification qheat it shows an `isqual` table — finishing order + a **Q/DNQ** Status column
  (the qheat's top-`count` qualify, `qualification.classify_qheat`). This is the *Intermediate-like*
  view, printed after each qheat (owner). Hooks the per-phase model (`ph.kind == "qualification"`).
- **[TODO, combined] A *Final-like* qualification summary** — one combined Q/DNQ advancement table
  per class (who reached the finals across all qheats, incl. the repechage). Follow-up (item 2b).

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
| 1 | ~~Time-trial best-lap **time**~~ | ✅ **DONE** | `analyze` reports the best (max-speed) lap's measured time; fixes the 1-lap `-`. See §5.1. |
| 2 | Qualification per-qheat (Intermediate-like) | ✅ **DONE** | Intermediate report `isqual` mode: per-qheat results + Q/DNQ Status (top-N qualify). See §5.2. |
| 2b | Qualification summary (Final-like) | **P1** (gap) | Combined Q/DNQ advancement per class across all qheats (incl. repechage). Follow-up. |
| 3 | Restart `R` / `R2` display | P2 | Map heat-id `1r`→`1R`, last-heat `1R`→`1R2` in heat headers (context-aware). Presentation-only. |
| 4 | Nationality column | P2 | Depends on **D1**. |
| 5 | Laps for all finishers | P3 | Depends on **D3**. |

## 7. Decisions (owner calls — OPEN)

- **D1 — Nationality data model.** Is `participants[i][3]` *the* nationality field (then
  relabel the column "Nationality" and validate IOC-3/country), or do we add a distinct
  nationality field separate from "From/club"? 209 requires nationality specifically.
- **D2 — Time-trial metric. DECIDED (owner, 2026-07-20): best-lap _time_, from the recorded
  lap-time values.** 305.04.02 is specific about time. Use the **measured lap time** — the best
  completed lap's crossing interval from the record — **directly**; do **not** compute it from
  speed (`lap_length ÷ speed`) unless the measured interval is genuinely unavailable, and do not
  use analyze `laptime` (0 on a 1-lap heat). Ships with the §5.1 P1 fix when reports resume.
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
  for later. Owner decided **D2 = best-lap time**, taken from the recorded lap-time values
  (not speed-derived). D1 / D3 remain open.
- **2026-07-20** — Plan item **1 done**: `analyze` reports the best (max-speed) lap's measured
  time as `laptime`, fixing the 1-lap TT `-` (§5.1). Synthetic analyze golden re-anchored
  `0 → 20.0` (deliberate divergence — legacy relied on manual lap-disabling). D1/D3 still open.
- **2026-07-20** — Plan item **2 (per-qheat) done**: the Intermediate report is qualification-aware
  (`isqual` mode) — per-qheat Q/DNQ Status (top-N qualify), the "printed after each qheat" view
  (owner). `qualification.classify_qheat` added. Item **2b** (combined Final-like qual summary)
  remains.
