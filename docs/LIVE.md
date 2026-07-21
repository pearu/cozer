# Live ordering feed — unofficial real-time running order

> **Status:** plan (2026-07-21, owner-decided). The MAINTENANCE_PLAN **Phase 7 / DoD #6** feature:
> cozer publishes the *unofficial* live running order during a race to a small feed that a
> broadcast-style viewer renders (like the on-screen order in motorsport TV). Seeded by `7948e787`;
> reports/GUI/release are `b76f2173`'s domain — coordinate before implementing. Nothing here is built
> yet. **Design preview of the viewer:** the published artifact (a dark "timing tower" mock).

## 1. What it is

During a heat, as boats cross the lap line the operator records the crossing in the **Timer**; the
running order changes. When broadcasting is on, cozer pushes a small **ordering snapshot** to a feed;
one or a few **controlled viewer screens** (broadcast overlay / venue display) render it. It is
explicitly **unofficial** — distinct from the §209 official signed/posted results.

## 2. Decisions (owner, 2026-07-21)

- **D-LIVE-1 — Transport: GitHub Gist (MVP).** Reuses the existing authenticated GitHub client
  (`crashreport._http` + the OAuth device-flow token); zero new hosting/auth. Fits the scope below.
- **D-LIVE-2 — Audience: a few controlled screens, not public.** 1 viewer (2–3 while debugging), all
  operated by us — *not* a public page (public is a possible future, see §8). This is what makes gist
  viable: a controlled viewer can poll the **gist API** (authed) for fresh data, inside rate limits.
- **D-LIVE-3 — Cadence: event-driven + a slow background flush.** Publish when the operator records a
  crossing (the order changed); a background timer may also re-post periodically. A **couple of
  seconds** from click to a live update is fine — no high-frequency streaming needed.
- **D-LIVE-4 — View contents (top → bottom):** **class name** and **phase kind** as the header
  (this *replaces* a UIM logo — avoids the mark-usage question); ordered rows of **position · boat
  number · driver surname · 3-letter (IOC) nationality**; the **COZER logo** at the bottom (owner
  supplies); a small **"last updated HH:MM:SS"**; a clear **"unofficial"** label. Visually appealing
  (broadcast timing-tower look). Nationality codes come from `cozer/countries.py` (IOC set).
- **D-LIVE-5 — Timer control:** a **"Broadcast live order"** checkbox in the Timer toggles publishing.
- **D-LIVE-6 — Large fields page (viewer-side).** With more than ~10 boats the tower shows one page
  (**top 10 by default**) and **occasionally flips to the lower group**, then back — top-weighted
  dwell — with a page strip ("Positions 11–20 of 20"). This is purely a **viewer** behaviour: the
  feed/snapshot still carries the **full** order (§4); the publisher is unchanged. **The view
  parameters — page size (⇒ the number of splits = ⌈field ÷ page_size⌉) and the dwell times — are
  configured *in cozer* and carried in the feed's `view` block (§4).** The viewer holds **no** view
  constants of its own; it renders exactly what cozer sends.

## 3. Architecture — decouple the transport

The one design rule that protects the investment: cozer never talks to gist directly. A small
**publisher** computes an ordering snapshot and hands it to a pluggable **sink**:

```
Timer crossing ──▶ order snapshot (from ladder()) ──▶ Publisher.emit(snapshot)
                                                          └─▶ GistSink   (MVP, §6)
                                                          └─▶ KV / Realtime sink (future, §8)
```

Swapping the transport later (for a public audience) touches only the sink — not the Timer or the
ordering code. `cozer/app/live.py` (new), mirroring how `update.py` reuses `crashreport`.

## 4. Data model — the snapshot

Small, stable, viewer-agnostic JSON (the "machine feed"):

```json
{
  "class": "F 500", "phase": "circuit", "heat": "2",
  "updated": "2026-08-15T14:32:05Z", "unofficial": true,
  "view": {"page_size": 10, "top_dwell_s": 20, "page_dwell_s": 6},
  "order": [
    {"pos": 1, "boat": "7",  "surname": "Tamm",  "nat": "EST"},
    {"pos": 2, "boat": "14", "surname": "Ozols", "nat": "LAT"}
  ]
}
```

- `order` is built from **`timer.ladder()`** (already computes the live order from crossings —
  timer.py notes it is "what the Phase-7 live feed will publish"), joined to participants for
  surname + `countries.IOC` nat. It is always the **full** field — the viewer pages it (§7).
- `phase` is the phase kind (`timetrial`/`qualification`/`circuit`/`endurance`); the viewer maps it
  to a display word ("Time Trial" / "Qualification" / "Final" / "Endurance").
- `updated` is stamped at publish time.
- **`view`** carries the **operator-configured display parameters, set *in cozer***: `page_size`
  (rows per screen — the number of splits is ⌈field ÷ page_size⌉) and the dwell times
  (`top_dwell_s`, `page_dwell_s`). The viewer obeys these and holds no view constants; absent or
  `page_size: 0` ⇒ show the whole field, no paging. (Room here for future display params too.)

## 5. cozer side (publisher + Timer)

- **`cozer/app/live.py`** — `snapshot(eventdata, cl, h)` (build the JSON from `ladder()` + participants
  + `countries`), and a `GistSink` that PATCHes the gist via `crashreport._http("PATCH",
  GITHUB_API+"/gists/"+gid, token, {"files": {"order.json": {"content": …}}})`.
- **Timer checkbox "Broadcast live order"** — on: publish on each recorded crossing, **debounced** to
  ~1 post / 2–3 s (D-LIVE-3), plus an optional periodic re-post; off: stop.
- **Broadcast/view settings (in cozer)** — page size / number of splits + dwell times (the `view`
  block, §4) are set here and shipped in every snapshot, so the operator tunes the display without
  touching the viewer. Sensible per-event home; stored with the broadcast config.
- **Never block timing.** Reuse the crashreport **offline-tolerant** pattern: a failed/slow publish is
  swallowed (log + skip), off the Timer's critical path — timing must never stall for the network.
- **What's broadcast** = the Timer's current `(class, heat)`.

## 6. The gist + sharing the URL (owner's question)

**Recommended: one persistent gist, set up once — not per event.**
- On first broadcast cozer **creates a gist** (`POST /gists`) and stores its id in cozer's **user
  config** (persists across events). The gist content is overwritten each heat/event; **the id never
  changes**, so the viewer URL is stable forever.
- cozer's Timer shows the **viewer URL** (copyable, + optional QR) — set the 2–3 screens up **once**;
  they keep working for every future event. (A "new gist" button covers the rare reset.)
- Alternative — **per-event gist** (id stored in the event file): only worth it if you ever run two
  events at once; one operator = one live feed, so the persistent gist is simpler.

**How the viewer reads it (controlled screens, D-LIVE-2):** poll the **gist API**
`GET /gists/{id}` with a **read-only token** every ~2 s → fresh content, well within 5000/hr for a
few screens. (The unauth *raw* gist URL is CDN-cached up to ~1 min — fine as a fallback, too stale for
the tower. This is exactly why a *public* audience needs §8.)

## 7. The viewer

A separate, self-contained branded page (not shipped inside cozer):
- **Look:** broadcast timing tower — see the **published design-preview artifact** (dark marine
  palette, aqua accent, gold leader row, class+phase header, `POS·No.·SURNAME·NAT` rows, COZER
  footer, live timestamp, "unofficial" label, FLIP-animated reordering).
- **Hosting:** for controlled screens, either a tiny **local HTML file** the operator opens, or a
  **GitHub Pages** page (stable URL, takes `?gist=<id>`). Either polls the feed and re-renders.
- **Logo:** COZER logo (owner-supplied) embedded; **no UIM logo** — the class name is the header
  (D-LIVE-4).
- Note: the preview artifact can't be the live viewer (artifact CSP blocks external fetch); it fixes
  the *design*, the hosted page does the fetching.

## 8. Upgrade path (future — public audience)

When a public, sub-second, many-viewer feed is wanted, swap the sink (§3) — no Timer/ordering rework:
- **Serverless KV** (Cloudflare Worker+KV / Deno Deploy / Val.town): cozer POSTs, viewers GET; low
  latency, free, minimal infra.
- **Realtime DB** (Firebase Realtime DB / Supabase Realtime): true websocket push to the viewer,
  scales to a public audience. The real-deal target; needs a service + keys.

## 9. Caveats

- **Unofficial, always.** Label it so on the view; it is the live *running order*, never the §209
  official result (which is the signed/posted sheet). Keeps the two from being confused.
- **Timing is sacred.** The publish path is best-effort and fully off the Timer's critical path.
- **Privacy:** the feed carries boat # / surname / nationality — public race info shown at the venue;
  nothing more. For a genuinely public feed (§8), reconfirm scope.

## 10. Plan (sequenced)

1. **Snapshot + publisher** (`live.py`): `snapshot()` from `ladder()`, unit-tested with a fake
   transport (like the update/crashreport tests). No gist yet.
2. **Gist sink + persistent-id config** + a "Broadcast live order" Timer checkbox (debounced,
   offline-tolerant). Verify one screen updates within a couple of seconds of a crossing.
3. **Viewer**: finalize the design-preview artifact into a hosted page (GitHub Pages or a local
   file) that polls the gist; embed the COZER logo.
4. **(Future)** realtime sink for a public audience (§8).

## Change log
- **2026-07-21** — Plan created; owner decisions D-LIVE-1..5 (gist MVP; controlled screens; event-driven
  cadence; class+phase header replacing the UIM logo, rows + COZER logo + update-time + unofficial
  label; Timer checkbox). Viewer design-preview artifact published. Seeded by `7948e787`.
