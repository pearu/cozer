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
- **[FIXED 2026-07-20, combined] *Final-like* qualification summary** — a new **Qualification**
  report (`reports/qsummary.py`, menu "Qualification"): one table per class with every boat's
  overall Q/DNQ, ordered primaries (by qheat) → repechage → DNQ, showing the source qheat
  (or "Rep."). Uses `qualification.classify` (aggregate). Registered in `_REPORTS`.

### 5.3 Finals / circuit (and shared across kinds)

- **Nationality (209).** Reports show a **From** column (label "Klubi" = *club* in ET),
  backed by the free `participants[i][3]` field that events fill with club **or** city
  **or** nationality. 209 requires *nationality* specifically (IOC-3 / country). There is
  even an unused `Country` ("Linn" = *city*) label. Nationality is not a guaranteed,
  distinctly-labelled field. → **P2 + owner call D1**.
- **[FIXED 2026-07-20] Restart notation (209).** Report heat headers now display via
  `reports.common.heat_label`: `1r`→`1R` (first restart), `1R`→`1R2` (second restart); TT/qual
  ids show a **bare number** (`2t`→`2`, `3q`→`3`) since the phase is shown separately. Applied in
  the finals / intermediate / laps headers. Presentation-only (the model keeps the raw ids). §8
  "does R2 need last-heat context?" → **no**: the `R` suffix already encodes the second restart.
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
| 2b | Qualification summary (Final-like) | ✅ **DONE** | New "Qualification" report (`qsummary.py`): combined Q/DNQ per class, primaries → repechage → DNQ. See §5.2. |
| 3 | ~~Restart `R` / `R2` display~~ | ✅ **DONE** | `reports.common.heat_label`: `1r`→`1R`, `1R`→`1R2` in finals/intermediate/laps headers. See §5.3. |
| 4 | Nationality column | P2 | Depends on **D1**. |
| 5 | Laps for all finishers | P3 | Depends on **D3**. |

## 7. Decisions (owner calls — OPEN)

- **D1 — Nationality. DECIDED (owner, 2026-07-20): a distinct field.** Nationality is a new
  participant field (index 6), separate from From/club. **Column visibility rule (owner):** a
  report shows the From *and* the Nationality column only when it holds >1 distinct non-empty
  value across the event — an all-empty or uniform column (a national event's all-`EST`, or an
  event with no clubs) is hidden. **Status: foundation done** (`a90d51f` — field + Participants
  GUI column + `show_from`/`show_nationality`/`nationalities_index`). **Participants report
  DONE**: conditional From + Nationality columns (fixes the mislabeled "Country"→club); a
  "Nationality" label added (et = "Rahvus", owner to verify). **Results reports DONE**:
  qualification summary (`69fa45e`), intermediate (`… D1 intermediate`), and finals
  (`2038da1`) all carry the conditional From + Nationality columns. `final.py._table_html` is
  shared with the *frozen* `*_legacy` reports, so the conditional columns are gated on
  `phase_native`: the legacy path passes the defaults (From-always, no Nationality) and stays
  byte-identical — the byte-identity goldens confirm it. **D1 report display complete.**
- **D2 — Time-trial metric. DECIDED (owner, 2026-07-20): best-lap _time_, from the recorded
  lap-time values.** 305.04.02 is specific about time. Use the **measured lap time** — the best
  completed lap's crossing interval from the record — **directly**; do **not** compute it from
  speed (`lap_length ÷ speed`) unless the measured interval is genuinely unavailable, and do not
  use analyze `laptime` (0 on a 1-lap heat). Ships with the §5.1 P1 fix when reports resume.
- **D3 — Laps for all finishers.** Show the completed-lap count for every result, or keep
  the current "only when short" (`NL`) convention?

## 8. Open questions

- ~~Does the qualification report show one table per qheat, or a combined ranking?~~
  **RESOLVED**: both — per-qheat is Intermediate-like (`isqual`), combined is the Final-like
  Qualification report (§5.2).
- ~~Restart `R2`: does the display mapping need last-heat context?~~ **RESOLVED: no** — the `R`
  suffix already encodes the second restart, so `heat_label` maps context-free (§5.3).
- Legacy byte-faithful reports (`*_legacy`) are intentionally frozen — do any 209 fixes
  apply to them, or only to the native builders? *(so far: native builders only.)*

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
  (owner). `qualification.classify_qheat` added.
- **2026-07-20** — Plan item **2b (Final-like) done**: new **Qualification** report
  (`reports/qsummary.py`, menu entry) — combined per-class Q/DNQ advancement across all qheats
  (primaries → repechage → DNQ). Reports item 2 complete.
- **2026-07-20** — Plan item **3 done**: restart notation. `reports.common.heat_label` maps
  `1r`→`1R`, `1R`→`1R2` in the finals / intermediate / laps heat headers (presentation-only).
- **2026-07-20** — **D1 report display done**: conditional From + Nationality columns wired
  through the intermediate and finals reports (participants + qsummary already done). Native
  builders only — `final.py._table_html` gates on `phase_native`, so the frozen `*_legacy`
  reports keep From-always / no-Nationality and stay byte-identical (goldens green).
  Remaining: D1 (nationality) + D3 (laps) owner calls.
