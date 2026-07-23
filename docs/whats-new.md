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
