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
  and any `heatK` may be re-run as **one** restart before it seeds the next (`heatK → heatK′`).
  A **second** restart is legal **only for the last final heat**, and only if the first restart
  was stopped before 35% of the required laps (UIM 311.02.2); elsewhere a 2nd restart is invalid
  and the validator should flag it. Restart records are §2.
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
| `timetrial` | solo / free, timed | light mis-click | best-time list | best lap → seeds the finals' 1st-heat grid — the master ordering signal, **incl. under a qualification phase** (§5.1) |
| `qualification` | mass-start | mis-click (fast + slow) | qual ranking | per-qheat **Q / DNQ** (top `count` = `Q`) → finalist selection (§4.1) |
| `circuit` | mass-start | mis-click (fast + slow) | finals sheet | UIM points |
| `endurance` | mass-start, duration | mis-click (banded) | endurance sheet | laps in the race duration (§4.1) |

Report names above are **intent, not final** (owner to adjust during implementation/testing).
**Each phase owns its report set** — a phase is, roughly, a standalone race event — and every
generated **PDF filename includes the phase kind name** (`…timetrial…`, `…qualification…`,
`…finals…`), so a merged .coz's outputs stay unambiguous. Adding a kind = add a row + its
handlers; the abstraction does not change.

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
- **Time-trial missed-buoy (UIM 305.04.02)** — if a driver is officially reported to have missed
  a turn buoy, that boat's **fastest lap is deleted** (irrespective of which lap the buoy was
  missed on) and "best" recomputed. **Covered by the existing Edit-Records *disable-lap* action**:
  the operator disables that boat's fastest lap on the report — no new mark type. *Implementation
  check:* the time-trial kind auto-disables all but the best lap, so disabling that best lap must
  **promote the next-fastest** enabled lap (recompute best over the remaining laps), not leave the
  boat timeless. An audit annotation ("removed: missed buoy" vs an ordinary mis-click delete) is
  optional, not required for scoring. (305.04.02 also allows two methods — best full lap, or best
  2 of 4 timed laps — both covered if "best lap" means best of the *timed* laps.)
- **Qualification = circuit heats that emit a `Q` / `DNQ` outcome — no scoring system.** A qheat
  is analyzed for its **finishing ranking** (the same `analyze` path, so mis-click and all the
  circuit machinery still apply), then a **hardcoded rule** marks each boat directly: **top
  `count` → `Q`** (qualified), the rest **`DNQ`**. There is **no `1…1 0…0` scoring array** and no
  Q-points — qualification needs only the qheat *ranking* + the per-qheat *count*, not a points
  system. `DNQ` is exactly the **§209** report code (§5.1 step 4), so the qualification outcome and
  the finals-report tail are the **same** thing, not two parallel systems. *(This is where decision
  A leads: once the grid is ordered by time-trial times, a numeric tier had no remaining job.)* A
  boat is a finalist iff it is `Q` in **any** of its qheats; because qheat1/qheat2 are **disjoint**
  and the repechage `qheat3` runs **only** their non-qualifiers, a boat's `Q` comes from **exactly
  one** qheat. **Primary-vs-repechage is not stored** — it is **derived from the source qheat**: a
  `Q` whose qualifying heat is the **last (repechage) qheat** is a repechage qualifier and seeds to
  the back (§5.1). The only stored parameters are the per-qheat **counts** (the tuple, §5.1) and
  **which qheat is the repechage** (the last).
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
4. The remaining boats in `qheat3` are **not classified** and race no final heat — but they are
   **not dropped from the report**: UIM **209** *("All entered drivers … must be mentioned in the
   race final results … which not qualified to the final heats with mentioning **DNQ**")* requires
   the finals report to list every entered-and-accepted boat, so non-qualifiers appear in a **DNQ
   tail** (below the classified finishers, no final points). *Not classified* governs
   scoring/seeding; the DNQ tail governs the report — the two coexist. `DNQ` is already a
   first-class outcome code (§209 work). (§10-E) *(Conversely, a `DNQ` boat may be **promoted** to
   a withdrawn finalist's slot — the make-up rule, §10-F.)*

**Qualification only *selects* finalists** — it does not order the finals grid. Each qheat marks
its **top `count`** boats **`Q`** (qualified) and the rest **`DNQ`**, directly from the qheat
ranking with no scoring system (§4.1): top **N** of qheat1/qheat2, top **M** of the repechage
qheat3. A boat is a finalist
iff it is `Q` in **any** of its qheats. **Primary-vs-repechage is not encoded in the outcome** — it
is read from the **source qheat**: a `Q` from the last/repechage qheat is a repechage qualifier.
(Each boat's `Q` comes from exactly one qheat — the primaries are disjoint and the repechage runs
only their non-qualifiers — so the source is never ambiguous.)

**Grid order for the finals' 1st heat = the time-trial times** (UIM **307.01**, owner decision A).
A class that runs qualification also runs a preceding **time-trial** (305.04.03 makes time trials
mandatory for grouping), and *those times* set the 1st-final grid; qualification decides only *who
is in*. The **time-trial is the master ordering signal** (7948e787 review): it orders the
grouping, the **qualifying-heat** jetty positions *and* the **first-final** jetty positions
(307.01 seeds the grid from the time trial in *both* directions — never random). Qualification's
*only* grid contribution is sending the **repechage qualifiers to the back** — identified by their
**source qheat** (the last qheat), not by any score: the grid is [primary-`Q` boats by time-trial
time] then [repechage-`Q` boats by time-trial time]. *Fallback:* a pure `qualification → finals`
with no recorded time-trial phase orders the grid by the **circuit ranking**, applying the same
structural split — [primary-`Q` by circuit rank] then [repechage-`Q` by circuit rank] — so the
repechage still lands at the back **without relying on a point tier** (305.04.03 makes this shape
rare — a time trial is mandatory whenever grouping is needed).

*(307.01 is the **jetty / dead-engine start** rule; the flying start — 306, ≤14 boats, not for
World/Continental — defines no time-trial grid.)*

The only remaining choice is **how many qualify from each qheat** — a **per-qheat** count,
authored compactly as a tuple on the qualification pattern: `!qualification[N,N,M]` = one entry
per qheat (`qheat1→N`, `qheat2→N`, `qheat3→M`). Each entry feeds the **hardcoded** qualification
rule for that qheat (top *count* → `Q`, rest `DNQ` — §4.1); no per-qheat scoring-system
data is stored. The **tuple length is the number of qheats**, so a qualification pattern needs
no leading `NofHeats*` count — it would be redundant (if present, it must match the tuple
length). The **repechage is the last qheat** (the last tuple entry — owner Q10.1); its field is
the earlier qheats' non-qualifiers, and its `Q` boats seed to the **back** of the finals grid —
identified **structurally** (source qheat = the last one), with the grid itself ordered by
time-trial times (decision A) or, in the no-time-trial fallback, by circuit rank under the same
primary-then-repechage split.

### 5.2 Restarts, labels, and fixing a mis-filed heat

**Restart handling is per-kind** (UIM **311.02.3** / **311.03.5**, owner decision B):

- **Multi-heat** circuit / finals — **take-last**: the last non-empty record is canonical, laps
  from earlier starts are **discarded** (311.02.3: *"Laps gained in previous starts are
  discarded"*). The remaining-laps restart threshold is **70%** (311.02.1).
- **Single-heat** racing (a one-heat final) & **endurance** — **aggregate**: laps from the
  original start and all restarts are **combined** for final positions (311.03.5), with a **20%**
  remaining-laps threshold (311.03.2), not 70%/take-last.

This document's focus is the **circuit (multi-lap)** path; the aggregate branch is recorded so
folding phases **does not introduce bugs into single-lap / endurance** events. The default
described next is the *multi-heat take-last* rule.

A heat number may hold several records (original + restarts). For multi-heat racing the
**canonical** record for a number — used for seeding (§5) and the total ranking / final report
(`sumanalyze`) — is the **last non-empty** one, so "for finals use only the last restart" is the
default (no manual selection needed); single-heat/endurance aggregate instead, per the split
above.

- **Restart labels come for free from position:** the 2nd record for a number is the "1st
  restart", the 3rd the "2nd restart" (§2). A report labels them without any selection trick.
- **Empty restart records are skipped**, never canonical. An empty trailing restart signals a
  Timer defect (it should not create a record with no crossings); the ranking ignores it, worth
  a validator warning.
- **Reports selection is a *set*, not an order** (rev 12): checking heats picks *which* count;
  the record used is automatic (last non-empty), and `sumanalyze` is order-independent.

The one case legacy solved with *selection order* is a **mis-filed heat** — the operator
accidentally records under the wrong race/heat in the Timer (e.g. a restart `1r` when it was
heat `1`, or the wrong class), uncorrectable mid-race. The new model fixes the cause, not the
report (**settled, owner Q10.2/Q10.3**):

1. **Prevent** the wrong pick in the Timer — constrain/confirm the race+heat being recorded so a
   mis-pick is hard to make.
2. **Reassign** afterward in **Edit Records** — a **"Reassign…"** action on the open heat sets
   its target identity (**Class → Phase → heat number**, plus its **slot among same-numbered
   records**: original / 1st restart / 2nd restart) and moves the whole heat's records there via
   one journaled store op. The dialog **defaults to the current identity**, so the common
   `1`↔`1r` fix is a single field change; a full class/phase move is the same dialog. *(Edit-
   Records home confirmed — owner; the exact dialog widgetry is refinable during implementation.)*

*(Fallback, if prevention + reassignment ever prove insufficient: legacy's Reports
selection-order mapping — 1st selected = original, 2nd = 1st restart, …; last used for ranking.)*

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
- Qualification is a **membership gate only**: per-qheat counts via `!qualification[N,N,M]` (the
  **repechage is the last tuple entry**). Each qheat is analyzed for its ranking, then marks its
  top `count` boats **`Q`** and the rest **`DNQ`** directly — **no scoring system, no Q-points**
  (rev 22); `DNQ` is the same **§209** code the finals report already uses, so outcome and report
  tail are one thing. **Primary-vs-repechage is derived from the source qheat** (a `Q` from the
  last/repechage qheat is a repechage qualifier), not stored. The **first-final grid is ordered by
  time-trial times** (UIM 307.01, decision A) — the time-trial is the *master ordering signal*
  (grouping, qualifying-heat jetty positions, first-final jetty positions); qualification only
  *selects* finalists and seeds the repechage to the back (structurally); the circuit ranking is
  the no-time-trial fallback. A single combined repechage (`qheat3`) matches the rulebook worked
  example (305.04.03 p.56) — no per-group second chance. (§5.1, Q10.1, A, rev 22)
- **N and M are an organizer choice**, not rules-determined (7948e787 re-review): 305.04 gives no
  formula — the p.56 8/8/4 is an *example*, and `G·N + M = H` alone allows several splits (P=30,
  H=20 → five). So the `!qualification[N,N,M]` tuple **stays explicit**. A boats-per-heat **H**
  racepattern param (to validate the tuple + default `M = H−G·N`) was considered and **deferred**
  (owner, 19 Jul 2026). (§5.1, §10-F)
- **Non-qualifiers stay in the finals report**, marked **DNQ** (no final points) — UIM 209
  requires every entered-and-accepted boat to appear; *not classified* (seeding) and the DNQ tail
  (report) coexist. (§5.1 step 4, §10-E)
- **Reports are per-phase**: each phase owns its report set (a phase ≈ a standalone race event),
  and every generated **PDF filename includes the phase kind name** so a merged .coz's outputs
  stay unambiguous. Report machinery is reused unchanged (`analyze`/`sumanalyze`). (§4, §10-E)
- **Missed-buoy (305.04.02) needs no new machinery**: the existing Edit-Records *disable-lap*
  action deletes the boat's fastest lap; best-lap recomputes to the next-fastest. (§4.1, §10-D)
- **Restart handling is per-kind** (decision B): multi-heat circuit/finals **take-last** (earlier
  laps discarded, 70% threshold — 311.02.3/311.02.1); single-heat & endurance **aggregate** (20%
  threshold — 311.03.5/311.03.2). Circuit is this doc's focus; the aggregate branch is recorded so
  folding phases does not break single-lap/endurance events. (§5.2, B)
- Restart labels ("1st/2nd restart") derive from **record position**; a mis-filed heat is fixed
  by Timer mis-pick **prevention** + an Edit-Records **"Reassign…"** action (Class → Phase →
  number + restart slot, defaulting to the current identity), not selection order (§5.2). Two
  new work items: the Timer guard and the Reassign action. (Q10.2/3)
- Backward-compat via a read-time mapping; workarounds deprecated for new files. (§6)

## 10. Open questions / to revisit

**One open item (F), surfaced by the 7948e787 re-review (19 Jul 2026)** — the make-up / substitution
rule; everything else is resolved. Findings **A**/**B** (grid order, per-kind restarts) were folded
into §5.1/§5.2/§9; **C**/**D**/**E** are closed (kept as a record). The re-review also **confirmed**
that N and M are an **organizer choice**, not rules-determined (§9).

- **C. *(closed, 19 Jul 2026)* — a single combined repechage matches the rulebook.** The 305.04.03
  worked example (p.56) runs **2 selection heats → one combined second-chance heat** grouping all
  non-selected boats — exactly `qheat1`/`qheat2` + a single trailing `qheat3`. So the
  `!qualification[N,N,M]` model needs no per-group repechage; the earlier grammatical ambiguity
  resolves toward our model. (§5.1)
- **D. *(closed, 19 Jul 2026)* — missed-buoy is handled by existing Edit Records.** The 305.04.02
  penalty (delete the fastest lap on an official missed-buoy report) is the existing *disable-lap*
  action — no new mark type. Implementation check: disabling the best lap must promote the
  next-fastest (§4.1). Optional audit annotation only. (§4.1)
- **E. *(closed, 19 Jul 2026)* — reports are per-phase; only naming/layout is left to
  implementation.** **Each phase has its own report set** (a phase ≈ a standalone race event) and
  every **PDF filename includes the phase kind name** (§4). The machinery is reused unchanged
  (`analyze`/`sumanalyze`, §9); the one content requirement is the qualification→finals **DNQ
  tail** — {entered ∧ accepted} − {finalists}, marked `DNQ`, no final points (UIM 209; §5.1 step
  4). Exact column layouts / display names are an implementation/testing detail. (§4)
- **F. *(open — approach decided 19 Jul 2026: manual override)* — make-up / substitution rule**
  (305.04.03 cont., p.56). When a qualified finalist withdraws, organizers may promote a `DNQ` boat
  from the repechage to fill the slot — *"not after the penultimate heat."* The Q/DNQ outcome is
  **static**, so the model needs a **manual `DNQ → Q` outcome override in Edit Records** (reusing
  the Reassign/edit machinery). The **approach is settled**; the exact mechanism/widgetry is an
  implementation detail. Organizer-driven and rare. (§4.1, §5.1 step 4)

*Confirmed faithful by the review (no change): timetrial = best lap (305.04.02); circuit = UIM
points (317); split-into-groups + mandatory time trials (305.04.03); repechage-to-the-back intent
(305.04/307.01); 70% multi-heat restart threshold (311.02.1); "3rd restart never" (311.02.2).*

---

## Change log

- **rev 23** — folded the **7948e787 re-review** (owner decisions, 19 Jul 2026). The re-review confirmed revs 16–22 faithful and internally consistent. **N/M answered:** an **organizer choice**, not rules-determined (305.04 has no formula; `G·N+M=H` alone allows several splits) → the `!qualification[N,N,M]` tuple **stays explicit**; a boats-per-heat **H** param (validation + fill-to-capacity default) was **deferred** (owner: hold). §9 records this. **New open item §10-F:** the **make-up / substitution rule** (p.56) — a `DNQ` boat may be promoted to a withdrawn finalist's slot (not after the penultimate heat); approach decided (**manual `DNQ → Q` override in Edit Records**, reusing the Reassign machinery), mechanism left to implementation; pointer added in §5.1 step 4. Trivial clarity fix: §4 `timetrial` row now cross-refs §5.1 (it seeds the finals grid even under a qualification phase). §10 reopened with the single item F. Still **DRAFT — not approved for implementation.**
- **rev 22** — **went fully categorical** (owner, 19 Jul 2026): qualification emits a **`Q` / `DNQ` outcome directly**, with **no scoring system and no Q-points** at all. A qheat is analyzed for its *ranking* (so mis-click and the circuit machinery still apply), then the hardcoded rule marks **top `count` → `Q`, rest `DNQ`** — the `1…1 0…0` numeric encoding of rev 21 is gone. `DNQ` is the same **§209** code the finals-report tail already uses, so the qualification outcome and the report tail are a single thing, not parallel systems. Primary-vs-repechage stays **derived from the source qheat** (unchanged). Stored parameters unchanged: the per-qheat counts (`!qualification[N,N,M]`) and which qheat is the repechage (the last). Updated §4 table, §4.1, §5.1, §9. Still **DRAFT — not approved for implementation.**
- **rev 21** — **simplified Q-points to a single tier** (owner, 19 Jul 2026), a consequence of decision A. Since the grid is now ordered by time-trial times, the old `2`-vs-`1` tier (whose only job was to make the Q-points circuit ranking sort the repechage behind) is redundant: every qheat now scores **`1 … 1 0 … 0`** (top `count` = qualified). Recognized this single tier *is* a binary **Q / DNQ** flag — the same `DNQ` already surfaced in the finals report (§209), so qualification produces no parallel numeric system. **Primary-vs-repechage is now derived structurally from the source qheat** (a `Q` from the last/repechage qheat), not from a score or a new code; the no-time-trial fallback applies the same primary-then-repechage split explicitly rather than leaning on the point gap. Updated §4 table, §4.1, §5.1 (three paragraphs), §9. *(Owner is weighing a fully categorical Q/DNQ framing — dropping the numeric encoding entirely — as a possible follow-up; this rev writes the single tier so that step is light.)* Still **DRAFT — not approved for implementation.**
- **rev 20** — consistency fix found in a pre-re-review sweep: **§4.1's qualification note still described the pre-decision-A grid** (finals 1st-heat grid = *circuit ranking* of Q-points, calling the repechage-at-the-back rule "redundant"). rev 17 rewrote §5.1 for decision A but left this mirror text stale (grep missed it — the phrase wraps a line break). Reconciled: the grid is ordered by **time-trial times** (decision A); Q-points only *select* finalists and the tier *marks* the repechage to the back; the circuit ranking is the **no-time-trial fallback** only. No other live grid statement was stale. Still **DRAFT — not approved for implementation.**
- **rev 19** — closed the last two open items (owner, 19 Jul 2026), leaving **no open design questions**. **D (missed-buoy):** handled by the existing Edit-Records *disable-lap* action (delete the fastest lap on an official report) — no new mark type; §4.1 rewritten with the best-lap-recompute implementation check + optional audit annotation. **E (report catalogue):** closed — **reports are per-phase** (each phase owns its report set, a phase ≈ a standalone race event) and every **PDF filename includes the phase kind name** (owner); machinery reused unchanged, DNQ tail the one content requirement, names/layout left to implementation. §4/§9/§10 updated. Still **DRAFT — not approved for implementation.**
- **rev 18** — folded two more 7948e787 rulebook items (owner, 19 Jul 2026). **DNQ tail:** §5.1 step 4 + §10-E now require the finals report to list every entered-and-accepted boat, non-qualifiers marked **DNQ** with no final points (UIM **209**; `DNQ` already a first-class §209 code). *Not classified* (scoring/seeding) and the DNQ tail (report) coexist. **Closed §10-C:** the 305.04.03 worked example (p.56) is **2 selection heats → one combined repechage**, matching the `qheat1`/`qheat2` + single `qheat3` model — no per-group repechage needed (p.56 also independently confirms decision A). Still **DRAFT — not approved for implementation.**
- **rev 17** — **owner resolved review findings A and B** (19 Jul 2026). **A:** the first-final grid is ordered by **time-trial times** (307.01), not the qual-heat ranking — the time-trial is the *master ordering signal* (grouping, qualifying-heat jetty positions, first-final jetty positions; 7948e787's 305.04.02/305.04.03/307.01 read); **qualification is a membership gate only** (selects finalists, sends the repechage to the back); the Q-points ranking is now just the no-time-trial fallback. Rewrote §5.1, removed the §4↔§5.1 conflict. **B:** restart handling is **per-kind** — multi-heat circuit/finals **take-last** (70% threshold, 311.02.3/311.02.1), single-heat & endurance **aggregate** (20% threshold, 311.03.5/311.03.2); §5.2 states the split and notes circuit is this doc's focus so folding phases must not break single-lap/endurance. Both moved from §10 open questions to §9 settled. Still **DRAFT — not approved for implementation.**
- **rev 16** — folded the **UIM 2026 rulebook review** (7948e787). Corrections applied: §1 a 2nd restart is legal only for the last final heat (311.02.2); §4.1 add the time-trial missed-buoy rule (305.04.02 → delete fastest lap). Two **owner decisions** flagged inline + in §10: (A) first-final grid should be **time-trial times** not the qual ranking (307.01), (B) restart handling is **per-kind** — aggregate for single-heat & endurance (311.03.5), take-last for multi-heat (311.02.3). Minor flags: per-group repechage not expressible by the tuple (305.04.03); jetty-vs-flying-start context (306/307.01). Review confirmed the rest faithful.
- **rev 15** — owner confirmed the **Edit-Records "Reassign…"** action (option 1) as the mis-filed-heat GUI home; dropped the alternatives and the "proposed" hedge. §10 now has a single open item (the per-kind report catalogue); the abstraction and behavior are otherwise settled.
- **rev 14** — mis-filed-heat resolution **settled**: prevent-and-reassign. GUI = an Edit-Records **"Reassign…"** action setting a heat's Class → Phase → number + restart slot (defaults to current identity, so the common 1<->1r fix is one field); moves the records via one journaled store op. Two new work items noted (Timer mis-pick guard, Reassign action); legacy selection-order kept only as fallback. §9/§10 updated.
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
