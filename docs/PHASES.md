# Phases — multi-kind race classes in a single event

**Status: DRAFT — under active design. Not approved. Do NOT implement from this yet.**
This is a living specification, iterated with the owner. Each revision must flag any
change that contradicts something already agreed here (see *Change log*).

---

## 1. Motivation

A single racing class (e.g. `F125`) runs several **race types in sequence** within one
event — typically *training → time-trial → qualification → finals* — and results of the
earlier types define the starting order (and even the entry list) of the later ones.

Today this is modelled with two workarounds the owner wants to eventually retire:

- **`/T`, `/Q` suffixes on class names** (`F125/T`, `F125/Q`, `F125`) — a naming hack to
  give each race type its own race pattern, since a class currently has exactly one.
- **`t`, `q` suffixes on heat numbers** (`1t`, `1q`) — to keep those heats' records apart.
- The full event is often **split across two `.coz` files** (e.g. time-trial file +
  finals file), so the cross-type information flow (seeding) is copied by hand.

Goal: model all race types of a class in **one class, one participant pool, one file**,
so that (a) timing/validation/reporting operate on each type **independently** (a
conflict-free merge) and (b) the seeding information flows **automatically** between types.

These workarounds stay **readable for backward compatibility** and are **deprecated for
new files** (§6).

---

## 2. Core abstraction

```
Class          = (name, participant_pool, phases[])
phase          = (kind, pattern, heats{})          # one pattern per phase (Q1)
heats          = { heat_id: heat_record }
heat_id        ∈ { 1, 1r, 1R, 2, 2r, 2R, ... }     # number + restart variant; NO t/q suffix
heat_record    = [ info, { boat_id: [marks...] } ] # UNCHANGED from today
```

- A **class** has one identity and one **participant pool** (boat number, driver, club).
  Phases and heats draw **ordered subsets** from this pool.
- A class carries an **ordered list of race patterns**, one per phase. Each pattern's
  trailing `!<kind>` hint sets that phase's kind (`race_kind`, already implemented).
  **The pattern list *is* the phase list**, in running order. The only Classes-tab UI
  change is to allow *N* patterns instead of one.
- **`t`/`q` heat suffixes become redundant** because the kind lives on the phase; heat ids
  are just the number plus a restart variant (`r`, `R`).
- **One pattern per phase** (Q1). A restart re-runs the phase's pattern; a *shortened*
  restart course is **not** a separate pattern — it is handled by scoring rules on the
  laps state (§5, Q1), not by the data model.

---

## 3. Data model / record structure

Current (flat, 2-level): `record[class][heat] = [info, boats]`. Phase is encoded in the
class suffix (`F125/T`) or heat suffix (`1t`). This cannot hold a time-trial `1` and a
finals `1` at the same time — hence the suffixes.

Proposed (add a phase level so heat numbers can restart at `1` per phase):

```
record[class]  = [ Phase, ... ]                    # ordered, parallels class.patterns
Phase          = { kind, pattern, heats: { heat_id: [info, boats] } }
info           = { course, sheats, duration, starttime, kind, ... }  # gains `kind`
```

- `class.patterns` (in `eventdata["classes"]`) is the **authoring** source; `record[class]`
  phases are the **runtime** materialization (a phase's `course`/`sheats`/`duration` are
  materialized from its pattern when its heats are set up, exactly as `heat.info` does today).
- **Blast-radius note (important):** the `[info, boats]` heat record is untouched, so the
  **scoring core (`analyze`/`sumanalyze`) does not change** — it still takes a single heat.
  Phases only change *which heats exist and how they are addressed* (iteration + keys), not
  how a heat is scored. The golden equivalence tests continue to pass through a compat view.

*(Open: phases as an ordered list vs a dict keyed by kind — a list is proposed, allowing
order = running order and, in principle, repeated kinds. See §10.)*

---

## 4. Race kinds and per-kind dispatch

Everything discipline-specific switches on `phase.kind` (via `race_kind`, already central).
This per-kind dispatch is what makes the phases **independent / conflict-free**.

| kind | timer | validate | report | scoring |
|---|---|---|---|---|
| `training` | solo / free, timed | light | best-time list | unscored → seeds next |
| `timetrial` | solo run (3 laps) | no mis-click (solo) | TT ranking | best / aggregate lap |
| `qualification` | mass-start heat | mis-click | qual ranking | points → finalist selection |
| `circuit` | mass-start | mis-click (fast + slow) | finals sheet | UIM points, drop-worst |
| `endurance` | mass-start, duration | mis-click (banded) | endurance sheet | laps in duration |

Adding a kind = add a row here + its handlers; the abstraction does not change.

---

## 5. Starting-order flux (information flowing between heats)

Every heat has a **start order**: the ordered boat list that seeds the grid. It is
**derived, not authored**:

```
start_order(heat) = seed( previous_heat, ranking(previous_heat) )
ranking(heat)     = the analyzer's finishing order for that heat, computed on its records
                    AFTER edit-records corrections are applied (Q2)
```

- **Derived, not stored:** there is no separate seeding data to keep in sync. Whenever the
  start order is needed (timer grid, report participant list), it is computed from the
  *current* ranking of the previous heat. So correcting an early heat in edit-records
  transparently updates every downstream start order — no stale state. (Owner's Q2: "the
  start order for the next heat is generally defined by the ranking of the previous heat;
  the ranking of a heat is defined after edit records is applied.")
- **Workflow:** rank heat *N* (after its edit-records corrections) → derive heat *N+1*'s
  start order → race heat *N+1*. In normal operation the previous heat is final before the
  next starts, so the order is stable at heat start.
- **Chain / restarts:** the flux runs through *every* heat and restart — training → TT →
  qualification → finals heat 1 → heat 2 → …. A **restart inherits its parent heat's start
  order** (a restart is a re-run of the same heat). Restart *scoring* is governed by UIM
  rules on the laps state (e.g. a stoppage in the 2nd restart is scored from the laps state
  so a 3rd restart never occurs — Q1), not by the seeding.
- **Base case:** the first heat with no predecessor orders by registration / boat number.
- **Seed rule is per-transition** (`from-kind → to-kind`) and **hard-coded initially**,
  pluggable so a new rule drops in later. Examples: "sort by best training time, fastest on
  top"; "grid heat→heat by previous ranking".
- **Consumers:** the **timer orders its buttons by the start order** (fastest on top, not
  boat number); **reports print the start order** as the heat's participant list.

### 5.1 Qualification → finals (UIM 305.04) — *rule captured, exact `seed()` TBD*

When a class has too many entries to fit the course, entries are split across qualification
heats and a repechage gives a second chance (UIM **305.04**):

1. Entry list too large → split into **two qualification heats**.
2. **Top N** (from those heats) **qualify** for the final.
3. Non-qualified boats race a **third qualification heat** (2nd chance); its **top M
   qualify** for the final.
4. The remaining boats in the 3rd heat are **not classified** and race no final heat.

This is the heaviest `seed()` (subset selection + ordering + elimination). The exact
N/M/ordering and how it maps onto the finals grid is **deferred** — to be specified with the
owner against 305.04 before implementation.

---

## 6. Backward compatibility

Legacy files read via a one-time mapping; the workarounds stay readable and become
deprecated for new files:

- `F125/T`, `F125/Q`, `F125` → one class `F125` with phases `[timetrial, qualification,
  circuit]`.
- heat `1t` / `1q` → heat `1` inside the time-trial / qualification phase; `1`, `1r` stay in
  the finals phase.
- `istclass` / `isqclass` and the `t` / `q` heat suffixes become a **legacy-reader detail**.
- New files write only `!kind` + phase lists; `race_kind` reads the explicit kind and never
  needs the suffixes.

---

## 7. Extensibility

- **New kind:** add a row to the §4 table + its timer/validate/report/scoring handlers. No
  model change.
- **New seeding rule:** add a per-transition `seed()` (§5). No model change.
- **New phase for a class:** add a pattern to the class's pattern list.

---

## 8. Implementation sequencing (agreed, Q4 — for later, not now)

1. Backward-compat reader that loads legacy `.coz` into the new in-memory phase shape
   (no behavior change; goldens pass through a compat view).
2. Move timer / validate / report onto phases (per-kind dispatch).
3. Add the start-order flux (derived seeding) last.

---

## 9. Settled so far

- Core abstraction `(class, participants, phases[])`, phase = `(kind, pattern, heats)`. (§2)
- One pattern per phase; restart nuances are rule-based, not pattern-based. (Q1)
- Heat ids drop `t`/`q`; keep number + `r`/`R`. (§2)
- Scoring core (`analyze`/`sumanalyze`) unchanged; phases are an organizational layer. (§3)
- Start order is derived from the previous heat's post-edit ranking, not stored. (§5, Q2)
- Backward-compat via a read-time mapping; workarounds deprecated for new files. (§6)

## 10. Open questions / to revisit

1. **Phases: ordered list vs kind-keyed dict** — list proposed (order = running order, allows
   repeated kinds). Confirm.
2. **Qualification → finals `seed()`** — exact UIM 305.04 mapping (N, M, grid order,
   elimination). Deferred (§5.1).
3. **Manual start-order override?** — is the operator ever allowed to hand-adjust a derived
   grid, or is it always computed? (Not yet raised; flag if relevant.)
4. **Per-kind report catalogue** — which concrete reports each kind produces (§4 lists
   intent, not final report names).

---

## Change log

- *rev 1* — initial spec from the design discussion; incorporates owner answers Q1 (one
  pattern per phase; restart = rule-based scoring), Q2 (start order derived from previous
  heat's post-edit ranking), Q3 (qual→finals per UIM 305.04, exact rule deferred), Q4
  (sequencing agreed; this doc created).
