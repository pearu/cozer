# What's new in COZER

*Eesti keeles / in Estonian: [whats-new.et.md](whats-new.et.md).*

This page explains — in plain terms, no computer knowledge needed — what has changed and
improved in COZER. The most recent notes are near the top. If you are coming from the older
COZER, the **"Coming from the old COZER"** overview at the end covers the big picture.

> **Note.** COZER 3 is a **release candidate** right now — it is being tried out before the
> final version. If you spot something wrong, please send a bug report (the **Report a bug…**
> button in the top-right corner) — it helps a lot.

---

<!-- RELEASE STEP: as each new version comes out, add a short "## COZER … (month year)" section here,
     newest first (above the "Coming from the old COZER" overview), summarising the important changes
     since the previous release in plain terms. Keep whats-new.et.md (Estonian) a step in sync.
     `tools/bump_version.py` prints a reminder; see docs/RELEASE.md. -->

## Championship points export, and clearer disqualification across heats (July 2026)

<!-- release-notes:3.0.0rc20 -->

- **Export championship points to a spreadsheet.** The **Reports** tab has a new **Export championship
  points…** button. Tick the classes you want (or leave them all unticked for every class) and it writes a
  **CSV spreadsheet** — one row per driver with the class, finishing **place**, boat number, name, club,
  nationality and the event's points — ready to feed into a championship or series that spans several
  events (this event being one round). The **place** is the part that matters: your series can apply its
  own points table, since it may score differently from the race event.
- **Clearer disqualification across heats.** A technical disqualification — for example an illegal boat,
  motor or fuel (U.I.M. §317.08 / §508.09) — applies to **every heat** the boat raced, not just one. COZER
  now **warns** if a boat is disqualified in some heats but not all, and **Edit Records** shows the rule
  article and a hint that the mark covers all heats — so the final result comes out right.

## A reprimand notice, and tidier multi-page results (July 2026)

<!-- release-notes:3.0.0rc19 -->

- **A new Reprimand notice.** The Reports tab has a new **Reprimand** printout — the formal notice an
  Officer of the Day issues to a driver for an unacceptable action (U.I.M. §406.04). It prints as a
  ready-to-fill form: the event heading and the OOD / Secretary lines are filled in, and you write in
  the driver, the offence (with a checklist of grounds), and sign it. It carries the rule's wording —
  that a repeat draws a heavier penalty, and that the reprimand stays on record for 12 months.
- **The results sheet keeps the signatures on the first page.** On the **Full Final**, a long list of
  notes used to push the Officer / Commissioner signature lines onto a second page. The signatures now
  sit in the **top-right corner**, so they always stay on the first page — and the results table itself
  does not move.
- **Clearer page numbering on long reports.** Every report footer now shows **"Page 1 / 3"** (with the
  total page count), and every page except the last is marked **"continued…"** at the bottom-right, so
  it is obvious when a printout runs onto further pages.
- **Live broadcast touches** (already live on live.cozer.ee — no update needed): the event header is
  flagged as **unofficial**, and the idle-page tagline lays out more tidily.

## Steady Timer buttons, broadcast starting grid, and a public event page (July 2026)

<!-- release-notes:3.0.0rc18 -->

- **The Timer's buttons no longer shift when you press Start.** The elapsed-time clock reserves its space,
  so starting a time trial doesn't nudge the buttons beside it.
- **The live broadcast shows the starting grid order before the start.** Before a race begins, the boats in
  the broadcast are listed in the **same starting order as the Timer's ladder** (e.g. heat 2 in heat 1's
  finishing order), instead of boat-number order.
- **Improved live pages** (already live on live.cozer.ee — no update needed): a new per-event page at
  **live.cozer.ee/&lt;event&gt;/** with a class·heat·phase header and a live viewer count; combined heats
  (two or more classes on the water) now show every class with its own live timing; and various layout
  polish for time trials.

## Safer against losing work, and share a heat's timing between computers (July 2026)

<!-- release-notes:3.0.0rc17 -->

- **COZER guards against losing unsaved work.** If you try to quit with unsaved changes, COZER now asks
  whether to **Save**, **Discard**, or **Cancel** — no more accidental loss. And in the **Timer**, pressing
  **Stop** now **saves automatically**, so a finished session's timing is written to the file at once.
- **Move a heat's timing between two computers running the same event.** If a second timer records a heat on
  another laptop, you can transfer it: there, tick that one heat on the **Reports** tab and use **Export heat
  records…** (it suggests a file name like *event-class-heat-phase*); on the main laptop, use **Import heat
  records…** on the **Timer** tab and choose the file. COZER matches the heat by its **class, phase and
  number** — even if the two race orders differ — adds it to the schedule if it's missing, and asks before
  overwriting any timing you already have. It refuses if the class, phase or race pattern don't match, or if
  a boat in the file isn't in your event.

## Time-trial timer clock, clearer records title, and combined-class broadcast (July 2026)

<!-- release-notes:3.0.0rc16 -->

- **Time trial: the Timer shows the time since Start.** During a time trial, after you press **Start** the
  Timer displays **"Time since Start: M:SS"** so you can see how long the session has run (a time trial
  ends on the clock, not on laps). It shows for time trials only and clears when you press Stop.
- **The records line reads heat-first.** The Timer's records title now shows the **heat number before the
  phase** — *"F 500 · heat 1 · time trial"* instead of *"… time trial · heat 1"*, which some found
  confusing. A plain race heat is unchanged.
- **Live broadcast: combined-class heats show every class.** When one heat runs **two or more classes**
  together (small classes sharing the water), the broadcast now **stacks each class's table** instead of
  showing only the first.

## Current-only outcome codes for 2026 events, and a time-trial broadcast view (July 2026)

<!-- release-notes:3.0.0rc15 -->

- **A 2026 event only offers the current outcome codes.** For an event run under the 2026 U.I.M. rules
  (§209), the right-click **insert-mark** menu no longer offers the old codes **DQ / DS / NQ / IR** — only
  their current equivalents: **DSQ** (disqualified), **DNS** (did not start), **DNQ** (did not qualify) and
  **DNF** (did not finish). Older events are unchanged and keep their own codes.
- **Live broadcast — a proper time-trial view.** During a time trial the live viewer now ranks boats by
  their **fastest lap so far**: the leader's row shows its best-lap **time and speed**, and every other row
  shows how far **behind the leader** that boat's best lap is (`+seconds`). The driver-name column is also
  wider so long names fit.
- **Tip — a practice *and* a time-trial before the race.** If your programme runs both, give the class a
  **Time-trial with two heats**: run the practice as the first heat and the timed session as the second. To
  keep a heat out of the starting order (e.g. the practice), open it in **Edit Records** and drag its **red
  "race stopped" line** back to just after the start — before any boat finishes a full lap. That heat then
  counts for nothing: it is ignored for the starting order of the race *and* for the Practice / Time-trial
  results, so the order comes from the timed session. Trim every heat except the one that should count.

## Time-trial best lap now counts every lap, and visible tick-marks (July 2026)

<!-- release-notes:3.0.0rc14 -->

- **A time trial's best lap now considers every lap the boat completes.** The lap count in a class's
  pattern is only an estimate of how many laps fit the session — it no longer limits the result. If a
  competitor's fastest lap comes on a lap beyond that estimate, it now counts (previously it could be
  missed, which could change the order). Laps after the race is stopped are still not counted, and the
  first lap (the run-up from the start to the lap line) is still excluded, as before.
- **Tick-marks are visible again when a box is checked.** On Windows, ticking a checkbox (for example when
  choosing classes and heats for a report) left the box looking empty. Checked boxes now show a clear
  filled mark.

## Restart races, start order, and a printed start list (July 2026)

<!-- release-notes:3.0.0rc13 -->

- **You can now add a restart as its own race.** When a race is stopped and re-run, schedule the restart
  on the **Races** tab: the **Heat** box now offers *"1 - restart"* (and only the sensible next choices —
  never heat 3 before heat 2 has been run; the final heat may be restarted twice). The restart is kept
  and reported as a **separate heat**, so the stopped run's timing is never lost. A time trial, being
  individual timed runs rather than a race, is never restarted.
- **Starting a race that already has timing no longer risks losing it.** Pressing **Start** on a heat that
  already holds recorded crossings now warns you clearly — it says **how many crossings would be erased** —
  and points you to add a restart instead, or to use **Resume** to keep timing the same run. Measured data
  is never overwritten silently.
- **A restart lines up in the order the boats held when the race was stopped.** (U.I.M. §311.01.7) Instead
  of repeating the original start order, the restart's grid — and the timer's running order — now shows the
  boats in their positions at the moment of the stoppage.
- **The timer starts in grid order, not boat-number order.** Before the start, the timer's ladder now lists
  boats in their **starting-grid** order (heat 2 in heat 1's finishing order, a final in the qualifying
  order, and so on); once boats begin lapping, the leader moves to the top as before.
- **New "Start List" report.** A printable list of **jetty / start positions** per class and heat, taken
  from that same grid order — the paper grid to post before a race.
- **Keep a lap COZER flagged but that is actually correct.** In **Edit Records**, right-click a lap that was
  marked as suspicious and choose **Acknowledge** to keep it and silence the warning.

## A fix for entering participants (July 2026)

<!-- release-notes:3.0.0rc12 -->

- **Deleting a participant no longer disturbs the other classes.** On the Classes / Participants tab,
  removing a driver from one class could — after switching to another class — show drivers under the
  **wrong class**, or make COZER stop responding while entering participants. That is fixed: each class
  list now re-checks itself against the current entries, so a deletion in one class leaves every other
  class untouched.

## Results note when a place was decided on the fastest lap (July 2026)

<!-- release-notes:3.0.0rc11 -->

- **When two boats tie, the results say how the place was decided.** If two boats finish on the **same
  points and the same average speed**, the placing is settled by their **fastest lap** (U.I.M. §318.03) —
  a number that was previously invisible on the sheet. The result reports now add a short note under the
  table, e.g. *"Places 2-3 decided on fastest lap (§318.03): #12 (92.4 km/h) over #7 (91.8 km/h)"* (shown
  as a time instead, if you chose the total-time view). Nothing changes when a place is decided the usual
  way (points, or average speed).

## A fix for total-time results (July 2026)

<!-- release-notes:3.0.0rc10 -->

- **Total-time results now show each boat's fastest heat.** When the Reports **Result: total time**
  option is used, a multi-heat final's summary time is the boat's **fastest single heat** (matching the
  speed view's best-heat figure), not the heats added together. Only the total-time view (off by
  default) is affected.

## No more "frozen" screen, penalty notes on results, and a complete inspection form (July 2026)

<!-- release-notes:3.0.0rc9 -->

- **COZER no longer looks "frozen."** When COZER asks something (a save prompt, a confirmation), the
  dialog now always **jumps to the front and flashes in the taskbar**, so it can never hide behind
  another window — a browser, the broadcast page, or a window on a second monitor — while quietly waiting
  for an answer. Purely-informational messages ("no data warnings", "up to date") no longer interrupt at
  all; they appear in the status bar. A crash when opening the **Phases** window was also fixed.
- **Write the reason for a penalty, and it prints on the results.** In **Edit Records** you can now add a
  short **note** to a penalty/rule mark (why it was given); it is collected into a **Notes** section on
  the result printout. The insert-rule menu also shows the **U.I.M. article** beside each rule.
- **A complete pre-race inspection form.** The **Inspection (Cockpit)** printout now lists the **full
  U.I.M. 2026 checklist** for a reinforced-cockpit class (F2 / F4 / F 500) on **one page** — every item
  is mandatory unless marked otherwise, and items proven by a certificate sit in a separate "documents"
  block rather than being re-checked at the ramp.
- **Results: choose speed or time, cleaner lap counts.** A new **Result: speed / total time** choice in
  the Reports tab; and the completed-lap count now shows **only for a boat that did not finish the full
  distance** (a footnote explains that no lap count means all laps were completed).
- **A tidier live broadcast.** Broadcast setup now lives in its own **Broadcast** menu, defaults to
  **live.cozer.ee**, and offers a **channel switcher** so a viewer can pick between the timekeepers' feeds.
- **Small fixes.** Drop-down lists are readable again (the highlighted row was invisible on some
  systems); heat numbers under the phase tabs show as a plain number; and the Class/Heat picker in Edit
  Records drops the `/T`/`/Q` ending.

## Time-trials, inspection forms, and the broadcast on a phone (July 2026)

<!-- release-notes:3.0.0rc8 -->

- **Time-trials scored fairly, with their own results form.** The time between **Start and the first
  lap-line** is no longer counted — it is the run-up, not a lap — so the fastest boat off the line can't
  get an unfairly short "best lap." A new **Practice / Time-trial** printout ranks boats by their **best
  full lap**, with no points or heat columns (for COZER, practice and solo time-trial are the same).
- **A tidier Reports tab.** The classes to include are now organised into **phase tabs** — Time-trials /
  Qualifications / Circuit — showing each class by its plain name, without the `/T` or `/Q` ending that
  confused people. (This also fixed a crash when generating the time-trial report.)
- **Pre-race inspection forms.** Two new printouts — **Inspection (Cockpit)** and **Inspection
  (Non-cockpit)** — the U.I.M. 2026 pre-race scrutineering checklists, one page per boat with the class,
  number and driver pre-filled.
- **The live broadcast on a phone.** The broadcast page now lays itself out nicely on a **smartphone**,
  so you can follow the running order on the go. (The chroma-key overlay for a video stream is unchanged.)

## Catching timing mistakes, and a cleaner live broadcast (July 2026)

<!-- release-notes:3.0.0rc7 -->

- **The live broadcast no longer shows "all 0.0" after a finish.** If a boat was tapped once more just
  after it crossed the finish line, the running order could collapse so every gap read **+0.0**. That is
  fixed — a stray extra click no longer disturbs the finished order. The overlay also makes the **START**
  and **FINISH** moments stand out, highlights a boat about to overtake, freezes each boat's time the
  instant it finishes, and shows **DNF** for a boat with no timing once the winner is home.
- **Edit Records now points out likely mis-clicks.** A lap that looks wrong — much shorter than the
  boat's usual lap (a double-tap), much longer (a missed crossing), or an impossible time — now
  **blinks** on the timeline, and **hovering it explains why**. Right-click the mark to disable it, so
  cleaning up a heat before the results is much quicker.
- **The "data warnings" are smarter.** They used to warn about *every* lap when the entered course
  length didn't match the boats' real speed. Now each boat is compared to **its own pace**, so the
  warning count flags only genuine oddities — and it matches the blinking marks in Edit Records exactly.
- **Timer touches.** Clicking a boat gently greys and shrinks its button (a guard against an accidental
  double-tap), the ladder and grid buttons share the same colours, boats that finish drop below the
  **Finish** line in the running order, and the full ladder appears as soon as you pick a race.

## Live broadcast, and a smoother timing screen (July 2026)

- **Live broadcast.** COZER can now show the **unofficial running order live on a web page** — point a
  venue screen or a stream overlay at it. Set it up under **Reports ▸ Live broadcast** (your live-server
  address, a publish secret, and a short event name), then switch it on with the **Broadcast** button on
  the Timer. The overlay shows each boat's place, laps completed, and a live **time to catch the
  leader** — boats about to overtake are highlighted, and it counts the leader down to **LAST LAP** and
  **FINISH**.

  ![The COZER live running-order overlay — flag, boat number and name, laps, and live seconds-to-catch-the-leader](img/broadcast-view.png)

  *What a stream or venue screen shows — place, flag and name, laps completed, and the live **seconds
  to catch the leader** (the leader counts down instead: here **3 TO GO**). The overlay's dark
  background is keyed out, so over your video only the text and flags appear.*
- **Delete race data.** The Edit Records tab has a **Delete** button that clears a heat's recorded laps
  and returns it to its just-before-Start state — with a clear warning when there is timed data to lose.
- **A smoother timing screen.** The full running-order ladder appears the moment you pick a race (before
  Start), the boat buttons stand out when pressed, and a small button copies the broadcast link for the
  display screens.

---

## COZER 3 — the modern COZER (2026)

The first modern version. See the overview below for what is new compared with the old COZER.

---

## Coming from the old COZER

If you organised events with the older COZER, here is what is different — and what is
reassuringly the same.

### The same rules, the same results

- COZER still scores events by the **U.I.M. Circuit Rules**, and it works out results **the same
  way** the old program did — the numbers you rely on are unchanged.
- It has also been brought up to date with the **2026 U.I.M. rule book**: the newer result codes
  (*Did Not Start*, *Did Not Finish*, *Disqualified*, and so on) and **nationality as an official
  three-letter country code** (EST, FIN, …).
- Your **old event files still open** — COZER reads the legacy `.coz` files directly.

### A cleaner, modern window

- A fresh look and a simple **tabbed layout**: general information, the timing screen, records,
  and reports — each on its own tab.
- The class, participant and race lists are easier to read and edit.

### Easy to install and keep up to date

- **One installer** for Windows — you no longer set up anything else by hand; everything COZER
  needs comes bundled. (See the [Windows installation guide](install-windows.md).)
- COZER can **check for a newer version by itself** — **Help ▸ Check for updates…** — and help
  you get it. No more hunting around for the latest copy.

### Better reports

- A dedicated **Nationality** column (the official country code), shown only when it actually
  varies across the event — a national event doesn't waste space on an all-EST column. The same
  goes for the **From** (club) column.
- **Qualification reports** — a per-heat **Q / DNQ** sheet to post after each qualifying heat, plus
  a summary of who reached the finals.
- **Restart notation** on the heat headings: `1R` for a restart, `1R2` for a second restart.
- **Time trial is simpler.** COZER automatically uses each boat's **fastest lap time** — you no
  longer have to disable the other laps by hand to leave just the best one.
- **Details for the notice board.** Each results sheet now carries a *Printed on* stamp, a
  *Posted at __:__* line for you to write the posting time in by hand, and **signature lines** for
  the OOD / Race Director and the U.I.M. Sports Commissioner — as the rules require.
- An optional **"show lap count for all finishers"** setting, for the reports that need it.

### When something goes wrong

- If COZER hits a problem, you can send a **bug report in one click** — with a picture of the
  screen attached — using the **Report a bug…** button in the top-right corner. Signing in with a
  free **GitHub** account lets these reports go straight to the people who can fix them.

---

*This English page is the source text; keep it and the Estonian version
([whats-new.et.md](whats-new.et.md)) a step in sync.*
