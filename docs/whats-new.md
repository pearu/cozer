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

## Live broadcast, and a smoother timing screen (July 2026)

- **Live broadcast.** COZER can now show the **unofficial running order live on a web page** — point a
  venue screen or a stream overlay at it. Set it up under **Reports ▸ Live broadcast** (your live-server
  address, a publish secret, and a short event name), then switch it on with the **Broadcast** button on
  the Timer. The overlay shows each boat's place, laps completed, and a live **time to catch the
  leader** — boats about to overtake are highlighted, and it counts the leader down to **LAST LAP** and
  **FINISH**.
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
