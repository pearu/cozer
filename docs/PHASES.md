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
  the scoring differs. That Q-points scoring is a **hardcoded rule** for the `qualification`
  kind — *the top `count` boats score the tier (2 for a primary qheat, 1 for the repechage), the
  rest score 0* — so cozer needs **no general per-qheat scoring-system data**; the only
  parameters are the per-qheat **counts** (the tuple, §5.1) and **which qheat is the repechage**.
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

The only remaining choice is **how many qualify from each qheat** — a **per-qheat** count,
authored compactly as a tuple on the qualification pattern: `!qualification[N,N,M]` = one entry
per qheat (`qheat1→N`, `qheat2→N`, `qheat3→M`). Each entry feeds the **hardcoded** qualification
scoring rule for that qheat (top *count* score the tier — §4.1); no per-qheat scoring-system
data is stored. The **tuple length is the number of qheats**, so a qualification pattern needs
no leading `NofHeats*` count — it would be redundant (if present, it must match the tuple
length). The **repechage is the last qheat** (the last tuple entry — owner Q10.1); it scores 1
(not 2), so the circuit ranking sorts it to the back, and its field is the earlier qheats'
non-qualifiers.

### 5.2 Restarts, labels, and fixing a mis-filed heat

A heat number may hold several records (original + restarts). The **canonical** record for a
number — used for seeding (§5) and the total ranking / final report (`sumanalyze`) — is the
**last non-empty** one, so "for finals use only the last restart" is the default (no manual
selection needed).

- **Restart labels come for free from position:** the 2nd record for a number is the "1st
  restart", the 3rd the "2nd restart" (§2). A report labels them without any selection trick.
- **Empty restart records are skipped**, never canonical. An empty trailing restart signals a
  Timer defect (it should not create a record with no crossings); the ranking ignores it, worth
  a validator warning.
- **Reports selection is a *set*, not an order** (rev 12): checking heats picks *which* count;
  the record used is automatic (last non-empty), and `sumanalyze` is order-independent.

The one case legacy solved with *selection order* is a **mis-filed heat** — the operator
accidentally records under the wrong race/heat in the Timer (e.g. a restart `1r` when it was
heat `1`, or the wrong class), uncorrectable mid-race. The new model prefers to fix the cause,
not re-derive it in a report (**proposed, owner Q10.2/Q10.3 — confirm**):

1. **Prevent** the wrong pick in the Timer — constrain/confirm the race+heat being recorded.
2. **Reassign** afterward — a direct edit-records action to move a heat's records to the correct
   number / restart-position, so the data is right everywhere.

*Fallback if prevention + reassignment prove insufficient: legacy's selection-order mapping —
1st selected = original, 2nd = 1st restart, 3rd = 2nd restart; last used for ranking, the earlier
ones only for the restart labels.*

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
- Qualification: per-qheat counts via `!qualification[N,N,M]`; the **repechage is the last
  qheat** (last tuple entry), scored 1 so it sorts to the back. (§5.1, Q10.1)
- Restart labels ("1st/2nd restart") derive from **record position**; a mis-filed heat is fixed
  by Timer prevention + edit-records reassignment, not selection order (proposed, §5.2). (Q10.2/3)
- Backward-compat via a read-time mapping; workarounds deprecated for new files. (§6)

## 10. Open questions / to revisit

1. **Confirm the mis-filed-heat resolution (§5.2).** Proposed: Timer **mis-pick prevention** +
   an edit-records **heat-reassignment** action, keeping Reports selection a plain set — rather
   than legacy's selection-order mapping (kept as fallback). Needs owner sign-off, then the two
   capabilities are new work items.
2. **Per-kind report catalogue** — §4 lists intent; concrete report names to be fixed during
   implementation.

---

## Change log

- **rev 13** — Q10.1: the **repechage is the last qheat** (last tuple entry, scored 1 → sorts to the back); resolved. Q10.2/Q10.3 (proposed, pending owner sign-off): restart **labels come from record position** (2nd record = 1st restart, …), and a **mis-filed heat** is fixed by Timer mis-pick **prevention** + edit-records **reassignment** rather than legacy's Reports selection-*order* (kept as fallback) — so rev 12's set-not-order selection stands. §9/§10 updated; two new capabilities noted (prevention, reassignment).
- **rev 12** — §5.2: canonical record is the **last non-empty** one, so an **empty restart** record (a Timer defect) is skipped, not used (worth a validator warning); the "finals use only the last restart" case is then the default. Recorded that the new model selects heats by **set, not order** — legacy's order-of-selection significance is not preserved (only report column order could differ; scoring is order-independent). New §10 flag.
- **rev 11** — note: the `!qualification[N,N,M]` **tuple length is the number of qheats**, so the legacy `NofHeats*` prefix is redundant on a qualification pattern (omit it; must match if present).
- **rev 10** — qualification scoring is a **hardcoded rule** (top `count` score the tier, rest
  0), not general per-qheat scoring-system *data* (owner: "the Q-heat scoring system could be
  hardcoded"). Supersedes rev 9's "per-event → per-qheat scoring system" implication: cozer
  needs no per-qheat scoring data — only the per-qheat counts (the tuple) and which qheat is the
  repechage.
- **rev 9** — qualifier counts are **per-qheat** (owner: "N/M are qheat parameters"), authored
  compactly as a tuple `!qualification[N,N,M]` (one entry per qheat), each materializing that
  qheat's Q-points scoring system. Flagged a code implication (cozer's scoring system is
  per-event; qualification needs it per-qheat) and a new open question: how the **repechage**
  qheat (scores 1, sorts to the back) is identified — positional vs structural (§10).
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
