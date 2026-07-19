# Phases — multi-kind race classes in a single event

**Status: DRAFT — under active design. Not approved. Do NOT implement from this yet.**
This is a living specification, iterated with the owner. Each revision must flag any
change that contradicts something already agreed here (see *Change log*).

---

## 1. Motivation

A racing class (e.g. `F125`) reaches its **finals** after **zero or more seeding phases** whose
results define the finals' starting order (and, for qualification, which boats race at all). A
class's phases are **exactly the race patterns authored for it** in the Classes & Participants
tab — one pattern per phase, in order (§2) — so the **implementation must not hard-code their
number or types**; whatever pattern list is authored defines the phases.

In practice the common shapes are:

- `finals`
- `time-trial → finals`
- `qualification → finals`
- `time-trial → qualification → finals`

where **training is a special case of time-trial** (a practice session used only for seeding,
so `training → finals` is just `time-trial → finals`) and a time-trial, when present, runs
before qualification. These are **conventions, not constraints** the model enforces.

- **`finals`** is itself a series of heats that seed each other — `heat1 → heat2 → heat3 → …` —
  and any `heatK` may be re-run as one or two restarts before it seeds the next:
  `heatK`, or `heatK → heatK′`, or `heatK → heatK′ → heatK″` (the restart records of §2).
- **`qualification`** applies when there are too many entries to fit the course: it splits into
  `qheat1` and `qheat2` over disjoint participant subsets; each sends its top boats to the
  finals and the rest to a repechage `qheat3`, whose top boats also reach the finals while the
  remainder are not classified (UIM 305.04, §5.1).
- **`time-trial`** ranks by **best lap** (cozer keeps each boat's best lap and disables the
  rest, §4).

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
| `timetrial` | solo / free, timed | light mis-click | best-time list | best lap → seeds the finals' 1st-heat start order (the timer ladder order) |
| `qualification` | mass-start | mis-click (fast + slow) | qual ranking | Q-points → finalist selection, drop-worst (§4.1) |
| `circuit` | mass-start | mis-click (fast + slow) | finals sheet | UIM points |
| `endurance` | mass-start, duration | mis-click (banded) | endurance sheet | laps in the race duration (§4.1) |

Report names above are **intent, not final** (owner to adjust during implementation/testing).
Adding a kind = add a row + its handlers; the abstraction does not change.

### 4.1 Notes

- **Training folds into `timetrial`** — there is no separate `training` kind. A practice /
  seeding session is a `timetrial` phase (so §1's `training → finals` and `time-trial → finals`
  are both the `timetrial` kind). Unlike legacy, **cozer auto-disables all but each boat's best
  lap** (an initial mark unselect) rather than the operator doing it by hand in Edit Records.
  *Code ripple: the implemented `RACE_KINDS` still lists `training` — drop it / alias to
  `timetrial`.*
- **Time-trial gets *light* mis-click** — a solo run can still be double-tapped (too-fast) or
  miss a crossing, so the physics/too-fast check applies; there is no wrong-boat case (no pack),
  and the too-slow median check needs ≥4 laps so it's inert on a 3-lap run. *Code ripple:
  validate currently **excludes** time-trials from mis-click — enable the light check.*
- **Qualification = circuit heats with a Q-points scoring system.** Score `qheat1`/`qheat2`
  with `2 … 2 0 … 0` (their top **N** score **2**) and the repechage `qheat3` with `1 … 1 0 … 0`
  (its top **M** score **1**); everyone else scores 0. A boat's qualification is the **best of
  its qual heats** (drop-worst), so a boat that qualifies only via the repechage still counts.
  **Finalists = the non-zero scorers.** The finals' 1st-heat grid is then simply the **circuit
  ranking** of the combined qualification results (points, then best average speed, then best
  lap speed) — and because qheat1/qheat2 qualifiers hold 2 points and qheat3 qualifiers hold 1,
  the repechage qualifiers land **behind** automatically, making the separate "repechage at the
  back" rule (§5.1) redundant. This reuses the whole circuit scoring + mis-click machinery; only
  the scoring system differs. (Only **N/M** remain a parameter, §5.1 / 305.04.)
- **Endurance defines the total race *time*, not a lap count.** The pattern's `/hours` term *is*
  the race duration; it replaces the legacy hack of setting a very high lap number.

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
- **Base case** (Q2, re 2): the first heat with no predecessor is seeded by the **participant
  order** in the Classes & Participants tab. That list is **drag-reorderable** (like the class
  list under the Rules tab), so a lot-draw is entered simply by ordering the participants — no
  dedicated draw-entry UI is needed. *(Requirement: the Classes & Participants tab must support
  reordering the participant list, as the Rules tab already does for classes.)*
- **Seed rule is per-transition** (`from-kind → to-kind`) and **hard-coded initially**,
  pluggable so a new rule drops in. Examples: "sort by best training time, fastest on top";
  "grid heat→heat by previous ranking".
- **Consumers:** the **timer orders its buttons by the start order** (fastest on top, not boat
  number); **reports print the start order** as the heat's participant list.

### 5.1 Qualification → finals (UIM 305.04)

When a class has too many entries to fit the course, entries are split and a repechage gives a
second chance (UIM **305.04**):

1. Entry list too large → split into **two qualification heats** `qheat1`, `qheat2` (disjoint
   participant subsets).
2. **Top N** of the two qualify for the final.
3. Non-qualified boats race a **third (repechage) qualification heat** `qheat3`; its **top M**
   qualify.
4. The remaining boats in `qheat3` are **not classified** and race no final heat.

**Grid order for the finals' 1st heat** is just the **circuit ranking** of the combined
qualification results under the §4.1 Q-points scoring: points (desc), then best average speed,
then best lap speed. Because qheat1/qheat2 qualifiers hold **2** points and the qheat3 repechage
qualifiers hold **1**, the repechage qualifiers land at the back automatically — reproducing UIM
305.04's *"positioned at the lower end of the jetty"* with **no special case**. (Within a points
tier, the disjoint qheat1/qheat2 fields are interleaved by the circuit speed tie-breaks.)

Only **N and M** (how many qualify at each stage) remain event/rule parameters; the ordering and
elimination fall out of the Q-points + circuit ranking.

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
- Start-order base case = the **participant order** in Classes & Participants, which is
  drag-reorderable (like classes under Rules) — so a lot-draw needs no dedicated UI, just a
  reorder. (§5)
- Backward-compat via a read-time mapping; workarounds deprecated for new files. (§6)

## 10. Open questions / to revisit

1. **Qualification `seed()` — N and M only.** The ordering and elimination now fall out of the
   Q-points + circuit ranking (§5.1); only how many qualify at each stage (N, M) remains an
   event/rule parameter.
2. **Reports heat-selection UI** on the results-list model — how the operator picks which
   record of a repeated number counts (§5.2). To detail with the report work.
3. **Per-kind report catalogue** — §4 lists intent; concrete report names to be fixed during
   implementation.

---

## Change log

- **rev 8** — base-case seeding resolved: the **participant list in Classes & Participants is
  drag-reorderable** (like the class list under Rules), so a lot-draw is entered by reordering
  — no dedicated draw-entry UI. Adds a small UI requirement (participant reordering). Closed the
  §10 "dedicated draw entry?" question; also fixed a stale §10 line still describing the pre-rev-7
  qualification ordering.
- **rev 7** — qualification Q-points made **tiered**: `qheat1`/`qheat2` qualifiers score **2**,
  the `qheat3` repechage scores **1** (reconciling an edit slip that wrote both "2…2 0…0" and
  "score 1"). The finals grid is now the plain **circuit ranking** of the combined qual results
  (points, avg speed, lap speed), so the qheat3 qualifiers sit at the back *because they hold
  fewer points* — the explicit "repechage at the back" rule (rev 5) is now redundant, and the
  rev 5 "order qheat1/2 by total qualification time" is superseded by the circuit speed
  tie-breaks. Only N/M remain open.
- **rev 6** — §1 generalized: a class has **zero or more** phases, defined entirely by the
  race-pattern list authored in the Classes tab; the implementation must not hard-code the
  count or types ("one or two seeding phases" was too specific). The listed shapes are common
  conventions, not enforced constraints.
- **rev 5** — §1: a **time-trial may precede qualification** (`time-trial → qualification →
  finals` is real), so the "at most one seeding phase" claim is replaced by "at most one
  time-trial and one qualification, time-trial first"; **training is a special case of
  time-trial**. §5.1: qual→finals **grid order fixed** — qheat1/2 qualifiers by total
  qualification time (circuit two-heat ranking over disjoint sets), qheat3 repechage qualifiers
  at the back (305.04 jetty rule); only N/M remain open (§10).
- **rev 4** — §4 reshaped. `training` folds into `timetrial` (no separate kind; cozer
  auto-disables all but the best lap). Time-trial gets a **light** mis-click check (physics
  only). `qualification` is modelled as a circuit heat with a `1…1 0…0` **Q-points** scoring
  system (non-zero scorers = finalists, best-of-qual-heats drop-worst). `circuit` scoring is
  plain UIM points. Endurance's pattern defines the total **race time** (`/hours`), not a high
  lap count. Two **code ripples** flagged (to handle when implementing): drop/alias `training`
  in the implemented `RACE_KINDS`; stop excluding time-trials from the mis-click check.
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
