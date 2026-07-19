# Phases — multi-kind race classes in a single event

**Status: DRAFT — under active design. Not approved. Do NOT implement from this yet.**
This is a living specification, iterated with the owner. Each revision must flag any
change that contradicts something already agreed here (see *Change log*).

---

## 1. Motivation

A racing class (e.g. `F125`) reaches its **finals** either directly or after **one seeding
phase** whose results define the finals' starting order (and, for qualification, which boats
race at all). The realistic shapes are exactly:

- `finals`
- `training → finals`
- `time-trial → finals`
- `qualification → finals`

There is **at most one** seeding phase before finals — a `training → time-trial → qualification
→ finals` chain does **not** occur.

- **`finals`** is itself a series of heats that seed each other — `heat1 → heat2 → heat3 → …` —
  and any `heatK` may be re-run as one or two restarts before it seeds the next:
  `heatK`, or `heatK → heatK′`, or `heatK → heatK′ → heatK″` (the restart records of §2).
- **`qualification`** applies when there are too many entries to fit the course: it splits into
  `qheat1` and `qheat2` over disjoint participant subsets; each sends its top boats to the
  finals and the rest to a repechage `qheat3`, whose top boats also reach the finals while the
  remainder are not classified (UIM 305.04, §5.1).
- **`training` and `time-trial`** produce a ranking by **best lap**; in legacy the boat's
  best-lap record is kept and the others disabled in the Edit Records tab.

Today this is modelled with workarounds the owner wants to eventually retire:

- **`/T`, `/Q` suffixes on class names** (`F125/T`, `F125/Q`, `F125`) — a naming hack to
  give each race type its own race pattern, since a class currently has exactly one.
- **`t`, `q` suffixes on heat numbers** (`1t`, `1q`) — to keep those heats' records apart;
  and **`r`, `R` suffixes** (`1r`, `1R`) to keep restarts apart.
- The full event is often **split across two `.coz` files** (e.g. time-trial + finals), so
  the cross-type information flow (seeding) is copied by hand.

Goal: model all race types of a class in **one class, one participant pool, one file**, so
that (a) timing/validation/reporting operate on each type **independently** (a conflict-free
merge) and (b) the seeding information flows **automatically** between types.

These workarounds stay **readable for backward compatibility** and are **deprecated for new
files** (§6).

---

## 2. Core abstraction

```
Class          = (name, participant_pool, phases[])
phase          = (kind, pattern, heats[])           # ONE pattern per phase (Q1)
heats          = [ heat_record, ... ]               # ordered "results list"
heat_record    = [ info, { boat_id: [marks...] } ]  # UNCHANGED shape
info           = { course, sheats, duration, starttime, kind, number, ... }
number         ∈ { 1, 2, 3, ... }                   # heat number; a RESTART repeats a number
```

- A **class** has one identity and one **participant pool** (boat number, driver, club).
  Phases and heats draw **ordered subsets** from this pool.
- A class carries an **ordered list of race patterns**, one per phase. Each pattern's
  trailing `!<kind>` hint sets that phase's kind (`race_kind`, already implemented).
  **The pattern list *is* the phase list**, in running order. The only Classes-tab UI change
  is to allow *N* patterns instead of one.
- **No heat-id suffixes at all** — `t`/`q` are replaced by the phase kind, and (rev 2, owner
  proposal) `r`/`R` are replaced by repetition: **a restart is simply a repeated heat number
  in the phase's results list.** The Nth record carrying number *k* is the (N−1)th restart of
  heat *k*. Nothing to parse out of a key.
- **Canonical record per number:** the **last** record with a given number is used by default
  for seeding and for ranking; the **Reports heat-selection** lets the operator override which
  record(s) count (§5.2) — that override is the main purpose of "checking heats" in Reports.
- **One pattern per phase** (Q1). A restart re-runs the phase's pattern; a *shortened* restart
  is **not** a separate/short pattern — it is handled by scoring rules on the laps state (a
  stopped 2nd restart is scored from the laps state, so a 3rd restart never occurs), not by
  the data model.

---

## 3. Data model / record structure

Current (flat, 2-level): `record[class][heat] = [info, boats]`, phase encoded in the class
suffix (`F125/T`) or heat suffix (`1t`), restart in `1r`/`1R`.

Proposed:

```
record[class]  = [ Phase, ... ]                     # ordered, parallels class.patterns
Phase          = { kind, pattern, heats: [ [info, boats], ... ] }   # ordered results list
```

- `class.patterns` (in `eventdata["classes"]`) is the **authoring** source; `record[class]`
  phases are the **runtime** materialization (a phase's `course`/`sheats`/`duration` are
  materialized from its pattern when a heat is set up, exactly as `heat.info` does today).
- **Restarts** are repeated `info.number` within a phase's list; the **last** per number is
  canonical (§2). Addressing a heat is now "the records with number *k*" (default: the last),
  not an O(1) key lookup — a small change from the dict of today.
- **Blast-radius note (important):** the `[info, boats]` heat record is untouched, so the
  **scoring core (`analyze`/`sumanalyze`) does not change** — it still takes a single heat.
  Phases + the results-list only change *which heats exist and how they are addressed*
  (iteration + selection), not how a heat is scored. The golden equivalence tests keep
  passing through a compat view.

*(§9/§10 track what is settled vs open, incl. the list-vs-dict container now chosen as list.)*

---

## 4. Race kinds and per-kind dispatch

Everything discipline-specific switches on `phase.kind` (via `race_kind`, already central).
This per-kind dispatch is what makes phases **independent / conflict-free**.

| kind | timer | validate | report | scoring |
|---|---|---|---|---|
| `training` | solo / free, timed | light | best-time list | best lap (others disabled) → seeds finals |
| `timetrial` | solo run (3 laps) | no mis-click (solo) | TT ranking | best lap (others disabled) |
| `qualification` | mass-start heat | mis-click | qual ranking | points → finalist selection |
| `circuit` | mass-start | mis-click (fast + slow) | finals sheet | UIM points, drop-worst |
| `endurance` | mass-start, duration | mis-click (banded) | endurance sheet | laps in duration |

Report names above are **intent, not final** (owner to adjust during implementation/testing).
Adding a kind = add a row + its handlers; the abstraction does not change.

---

## 5. Starting-order flux (information flowing between heats)

Every heat has a **start order**: the ordered boat list that seeds the grid. It is
**derived, not stored**:

```
start_order(heat) = seed( previous_heat, ranking(previous_heat) )
ranking(heat)     = the analyzer's finishing order for that heat's canonical record,
                    computed AFTER edit-records corrections are applied (Q2)
```

- **Derived, not stored** (Q2, confirmed): there is no separate seeding data to keep in sync.
  The start order is computed from the *current* ranking of the previous heat whenever needed
  (timer grid, report participant list).
- **No retroactive risk** (Q2 clarification): a later protest may re-evaluate an earlier heat,
  but that only changes the **points/best-laps aggregated into the final report**, not the
  grid of a later heat that has **already been raced**. Seeding flows strictly **forward** and
  is consumed when a heat starts; once a heat is run, its own records stand. So re-deriving is
  always safe.
- **Restarts** share their heat number's start order (a restart re-runs the same heat, so it
  uses the same grid). The **last** record of a number then seeds the **next** number.
- **Base case** (Q2, re 2): the first heat with no predecessor is seeded by **registration /
  boat-number order**. Some events draw the first-start order by **lot**; rather than a
  dedicated draw-entry UI (likely overkill), the operator can arrange the registration order
  to be the draw result, and the base case reads it. (Flag if a dedicated draw entry is
  actually wanted.)
- **Seed rule is per-transition** (`from-kind → to-kind`) and **hard-coded initially**,
  pluggable so a new rule drops in. Examples: "sort by best training time, fastest on top";
  "grid heat→heat by previous ranking".
- **Consumers:** the **timer orders its buttons by the start order** (fastest on top, not boat
  number); **reports print the start order** as the heat's participant list.

### 5.1 Qualification → finals (UIM 305.04) — *rule captured, exact `seed()` TBD*

When a class has too many entries to fit the course, entries are split and a repechage gives a
second chance (UIM **305.04**):

1. Entry list too large → split into **two qualification heats**.
2. **Top N** qualify for the final.
3. Non-qualified boats race a **third (repechage) qualification heat**; its **top M** qualify.
4. The remaining boats in the 3rd heat are **not classified** and race no final heat.

This is the heaviest `seed()` (subset selection + ordering + elimination). The exact N/M and
grid mapping is **deferred** — to be specified with the owner against 305.04.

### 5.2 Restarts and Reports heat-selection

A heat number may have several records (original + restarts). By default the **last** is
canonical for seeding (§5) and for the total ranking / final report (`sumanalyze`). The Reports
"check which heats" feature is exactly the manual override of that default — letting the
operator choose which record of a number is counted (e.g. keep the 1st restart, not the 2nd).
This is why heat-selection exists in Reports, and it generalises cleanly to the results-list
model.

---

## 6. Backward compatibility

Legacy files read via a one-time mapping; the workarounds stay readable and become deprecated
for new files:

- `F125/T`, `F125/Q`, `F125` → one class `F125` with phases `[timetrial, qualification,
  circuit]`.
- heat `1t` / `1q` → number `1` inside the time-trial / qualification phase.
- heat `1r` / `1R` → a 2nd / 3rd record with number `1` in that phase's results list.
- `istclass` / `isqclass` and the `t`/`q`/`r`/`R` suffixes become a **legacy-reader detail**.
- New files write only `!kind` + phase lists + plain heat numbers; `race_kind` reads the
  explicit kind and no code parses suffixes.

---

## 7. Extensibility

- **New kind:** add a row to the §4 table + its timer/validate/report/scoring handlers. No
  model change.
- **New seeding rule:** add a per-transition `seed()` (§5). No model change.
- **New phase for a class:** add a pattern to the class's pattern list.

---

## 8. Implementation sequencing (agreed, Q4 — for later, not now)

1. Backward-compat reader that loads legacy `.coz` into the new in-memory phase shape (no
   behavior change; goldens pass through a compat view).
2. Move timer / validate / report onto phases (per-kind dispatch).
3. Add the start-order flux (derived seeding) last.

---

## 9. Settled so far

- Core abstraction `(class, participants, phases[])`, phase = `(kind, pattern, heats[])`. (§2)
- One pattern per phase; restart nuances are rule-based, not pattern-based. (Q1)
- Heat ids are **plain numbers** — no `t`/`q`/`r`/`R`; restarts are repeated numbers in the
  phase results list, last one canonical. (§2, rev 2)
- `phase.heats` is an **ordered list** of records (not a number-keyed dict). (§3, Q1-re-1)
- Scoring core (`analyze`/`sumanalyze`) unchanged; phases are an organizational layer. (§3)
- Start order is **derived** from the previous heat's post-edit ranking; forward-only, no
  retroactive risk. (§5, Q2)
- Start-order base case = registration/boat-number order; a lot-draw is reflected via
  registration order rather than a dedicated UI. (§5)
- Backward-compat via a read-time mapping; workarounds deprecated for new files. (§6)

## 10. Open questions / to revisit

1. **Qualification → finals `seed()`** — exact UIM 305.04 mapping (N, M, grid order,
   elimination). Deferred (§5.1).
2. **Dedicated draw entry?** — confirmed *not* needed for now (registration order carries it);
   revisit only if a first-start draw must be entered as distinct data. (§5)
3. **Reports heat-selection UI** on the results-list model — how the operator picks which
   record of a repeated number counts (§5.2). To detail with the report work.
4. **Per-kind report catalogue** — §4 lists intent; concrete report names to be fixed during
   implementation.

---

## Change log

- **rev 3** — §1 corrected: a class runs **at most one** seeding phase before finals (realistic
  shapes: `finals`, `training→finals`, `time-trial→finals`, `qualification→finals`), NOT a
  four-type chain (that earlier example was wrong). Spelled out finals-as-heat-series with
  restarts and qualification's qheat1/2 + repechage qheat3 (305.04). Recorded that
  training/time-trial rank by **best lap** (others disabled in Edit Records); §4 scoring
  aligned.
- **rev 2** — restarts: drop `r`/`R` suffixes; model a restart as a **repeated heat number**
  in a phase **results list** (was: keep `1r`/`1R` in rev 1). `phase.heats` becomes an ordered
  list (was a number-keyed dict). Start order confirmed **derived** with the no-retroactive-risk
  rationale (protests hit only final-report aggregates). Base case seeding = registration order,
  covering lot-draws without a dedicated UI. `patterns`→`pattern` typo fixed. Report names
  marked as non-final. Open questions renumbered.
- **rev 1** — initial spec from the design discussion; owner answers Q1 (one pattern per phase;
  restart = rule-based scoring), Q2 (start order derived), Q3 (qual→finals per UIM 305.04, exact
  rule deferred), Q4 (sequencing agreed; doc created).
