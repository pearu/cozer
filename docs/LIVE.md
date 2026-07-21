# Live ordering feed — unofficial real-time running order

> **Status: BUILT + LIVE (2026-07-21).** The MAINTENANCE_PLAN **Phase 7 / DoD #6** feature: cozer
> publishes the *unofficial* live running order during a race; a chroma-key browser overlay renders it
> (like the on-screen order in motorsport TV). **Primary transport: a self-hosted server on the owner's
> box, live at `https://live.cozer.ee/` with SSE push (~0.5 s latency) — see §8.** The GitHub gist path
> (§6) is kept as a fallback. Built jointly by `7948e787` (feed / viewer / flags / this doc) and
> `b76f2173` (Timer / live-server / deploy).
>
> **History (why two transports):** this doc was written **gist-first** (MVP, §6) — but the gist *raw*
> path proved **~60 s stale** (GitHub refreshes raw content server-side only ~1/min; edge cache-busting
> doesn't defeat it) and the *API* path is rate-limited + needs a token in the URL. So the transport
> moved to the self-hosted server; the decoupled sink (§3) made that a drop-in — only `live.py`'s sink
> and the viewer's data source changed.

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
- **D-LIVE-5 — Timer control + lifecycle:** a **"Broadcast live order"** checkbox — publishes **on tick**
  (the current ladder, even pre-start), **updates on crossings**, and publishes a **"stopped"** snapshot
  on **untick** (viewer shows "live stream disabled"). The clickable viewer URL sits next to it. See §5.
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
Timer crossing ──▶ order snapshot (from standings()) ──▶ Publisher.emit(snapshot)
                                                          └─▶ ServerSink (PRIMARY — self-hosted, §8)
                                                          └─▶ GistSink   (fallback, §6)
```

This decoupling paid off: moving the transport gist → self-hosted server touched **only** the sink
(`live.py`'s `publish_server` vs `publish`) and the viewer's data source — the Timer, the snapshot
shape (§4), and the overlay render were unchanged. `cozer/app/live.py` mirrors how `update.py` reuses
`crashreport`.

## 4. Data model — the snapshot

Small, stable, viewer-agnostic JSON (the "machine feed"):

```json
{
  "class": "F 500", "phase": "circuit", "heat": "2",
  "updated": "2026-08-15T14:32:05Z", "unofficial": true, "live": true, "started": true,
  "view": {"max_rows": 24, "poll_s": 3, "page_size": 10, "top_dwell_s": 20, "page_dwell_s": 6},
  "order": [
    {"pos": 1, "boat": "7",  "surname": "Tamm",  "nat": "EST", "laps": 2, "time": 40.0},
    {"pos": 2, "boat": "14", "surname": "Ozols", "nat": "LAT", "laps": 2, "time": 41.5}
  ]
}
```

- `order` is built from **`timer.ladder()`** (already computes the live order from crossings —
  timer.py notes it is "what the Phase-7 live feed will publish"), joined to participants for
  surname + `countries.IOC` nat. It is always the **full** field — the viewer pages it (§7).
- `phase` is the phase kind (`timetrial`/`qualification`/`circuit`/`endurance`); the viewer maps it
  to a display word ("Time Trial" / "Qualification" / "Final" / "Endurance").
- `updated` is stamped at publish time.
- **`live`** is `true` while broadcasting; a **`false`** snapshot (empty `order`) is published when the
  operator unticks, so the viewer shows a *"live stream disabled"* state rather than stale positions.
- **`started`** is `true` once any boat has completed ≥1 lap (crossed the first lap-line). The
  broadcast overlay shows only NAT/boat/surname before start, then reveals laps + gap once started.
- **`laps`** (completed laps) and **`time`** (cumulative seconds at the last crossing) per order row —
  from `timer.standings(rec)`. The overlay shows `laps`, and the **gap** = this boat's `time` minus the
  time of the boat one place ahead (or `+N L` when a lap down). Absent for a not-yet-started boat.
- **`view`** carries the **operator-configured display parameters, set *in cozer***: `page_size`
  (rows per screen — the number of splits is ⌈field ÷ page_size⌉), the dwell times
  (`top_dwell_s`, `page_dwell_s`), **`poll_s`** (viewer poll interval, seconds; default 3), and
  **`max_rows`** (show only the top-N drivers; default 24, `0` ⇒ all). The viewer obeys these and
  holds no view constants of its own.

## 5. cozer side (publisher + Timer)

- **`cozer/app/live.py`** (built) — `snapshot(eventdata, cl, heat, order, updated, view=None, live=True)`
  builds the §4 feed (`order` = `standings(rec)` dicts or bare ids); `stopped(...)` is the `live:false`
  untick snapshot. Two sinks: **`publish_server(base_url, channel, secret, snap)`** POSTs to the
  self-hosted server (primary, §8); `publish(token, gist_id, snap)` PATCHes/creates the gist (fallback,
  §6). Both raise-on-error; the Timer guards them off the timing path.
- **Timer checkbox "Broadcast live order" — lifecycle (owner scenario):**
  - **on tick:** publish **immediately** from the current ladder order — pre-start that's the field in
    ladder order, so a viewer opened before the start already shows the grid;
  - **on each crossing:** update — throttled ~1 post / **0.5 s** to the self-hosted server (no rate
    limit → low latency; 2.5 s for the gist fallback), off the timing path;
  - **on untick:** publish `live.stopped(...)` → the viewer shows "live stream disabled".
  The **clickable/copyable viewer URL** sits next to the checkbox (server: `<live_server_url>/?channel=
  <channel>`; gist: `…/live-viewer.html?gist=<id>`).
- **"Broadcast settings…" dialog (Timer)** — sets `live_server_url`, `live_publish_secret`, and
  `live_channel` in cozer's config; with the URL + secret present cozer publishes to the **server**,
  else it falls back to the **gist**. (View params — `max_rows`/`poll_s`/dwell — ride in the `view`
  block, §4, so the operator tunes the display without touching the viewer.)
- **Never block timing.** Reuse the crashreport **offline-tolerant** pattern: a failed/slow publish is
  swallowed (log + skip), off the Timer's critical path — timing must never stall for the network.
- **What's broadcast** = the Timer's current `(class, heat)`.

## 6. The gist + sharing the URL (FALLBACK transport)

> Gist is now the **fallback** (the self-hosted server, §8, is primary). This section is the original
> gist-MVP design, kept for when cozer has no `live_server_url` configured.

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

A separate, self-contained page (`docs/live-viewer.html`, on GitHub Pages), designed as a
**chroma-key video overlay** (owner, D-LIVE-8):
- **Layout:** **top-left**, **driver rows only** — no header/footer/column-header/total rows.
  Columns **NAT (country flag) · boat# · surname**, and once **started** (`started` in the feed) also
  **laps · gap** (time to the boat one place ahead, or `+N L` a lap down).
- **Chroma-key:** everything that is **not text or a flag** is one uniform **`--key` navy**
  (`#0a1a2f`) — no gradients, chips, borders, or row shading — so the stream keys that navy to
  transparent, leaving only the text + flags. (Replaces the earlier "timing tower" chrome.)
- **Flags:** **static repo data** — `docs/flags/<IOC>.svg` (206 flags, one per IOC code, public-domain
  from flag-icons), keyed by the 3-letter code so the viewer needs no mapping and there is **no runtime
  CDN** (works offline / on the venue LAN). A missing or failed flag **falls back to the code text**
  (which is what the artifact preview shows — relative `flags/` doesn't resolve there).
- **Hosting / data source:** primary — served by the self-hosted server at
  `https://live.cozer.ee/?channel=<channel>`, which uses **SSE** (`EventSource("/stream/<channel>")`,
  sub-second) with a **poll fallback** (`/live/<channel>.json`); `?src=<url>` polls any feed URL.
  Fallback — the gist path on GitHub Pages, `…/live-viewer.html?gist=<id>` (`&user=<login>` raw /
  `&token=<pat>` API, §6/§13). The same `docs/live-viewer.html` serves both — only the data-source
  branch differs; the render/flags/paging code is shared. (The design-preview artifact can't fetch
  (CSP) so its flags show as codes — it fixes the *design*.)
- Dropped from this view (vs the tower): class/phase header, COZER footer, timestamp, "unofficial"
  label, podium colors, paging bands — none survive the "rows only + uniform bg" rule. (The channel
  directory §11 still carries the unofficial framing.)

## 8. Self-hosted live server (PRIMARY transport — built, live at `https://live.cozer.ee/`)

The owner's own box (fixed IP, fiber) runs a tiny server that holds the latest snapshot per channel and
serves viewers directly — fresh, no rate limit, no token in any URL. This is the primary transport; it
replaced the gist (whose raw path was ~60 s stale — see the header).

**`deploy/live-server/`** (see its `README.md` + the owner's git-ignored `live_cozer_ee-setup.txt`):
- **`server.py`** — stdlib only, binds `127.0.0.1:8099`; snapshots kept **in memory** (a restart drops
  them, cozer re-publishes on the next tick → self-heals). Endpoints:
  - `POST /publish/<channel>` — operator writes the latest snapshot; auth = shared secret in the
    `X-Publish-Secret` header (`== PUBLISH_SECRET` env). Body-size-capped + JSON-validated.
  - `GET /live/<channel>.json` — public read of the latest snapshot (CORS `*`, `no-store`).
  - `GET /stream/<channel>` — **SSE push**: sends the current snapshot, then each new one the instant
    it's published (sub-second); 15 s keepalive; per-stream queue fed by `publish`.
  - serves the **viewer** (`/`, `/live-viewer.html`) + **flags** (`/flags/<IOC>.svg`) static, so the
    overlay is **same-origin** (no CORS) at `live.cozer.ee`.
- **`Caddyfile`** — Caddy fronts it: automatic Let's Encrypt HTTPS for `live.cozer.ee`, reverse-proxy to
  `127.0.0.1:8099`, `flush_interval -1` so SSE isn't buffered. Only Caddy is internet-facing.
- **`cozer-live.service`** — systemd unit (boot-start, `Restart=always`, `NoNewPrivileges`,
  `PrivateTmp`); reads the secret from root-only `/etc/cozer-live.env`.
- **Ports:** router forwards **80 + 443** (one-time); 80 = cert challenge + redirect, 443 serves all.
  Add more services later by hostname (a new Caddy block) — no new port changes.

**Why self-host over a managed backend** (the earlier "future" options — Cloudflare KV / Firebase /
Supabase): the owner already has a fixed-IP fiber box → full control, no third-party account/limits;
and plain KV stores are *eventually consistent* (~60 s), which would repeat the gist problem — an SSE
**push** server avoids it. Trade-off: it's a single box (owner's home server), so **the gist path (§6)
stays as the documented fallback** if the server is unreachable.

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

## 11. Channel directory & per-event pages (owner-decided 2026-07-21)

Multiple timekeepers broadcast in parallel (UIM ≥2 timekeepers), each from their **own** cozer under
their **own** GitHub account. A directory at `/cozer/` plus per-event pages aggregate their channels.
(`docs/index.html` = the `/cozer/` root directory — landed, `dac2f6e`.)

- **URL scheme — clean paths (owner).** `/cozer/` lists everything; **`/cozer/<event>/`** shows one
  event's channels. Pages is static, so the clean path uses a **`404.html` SPA router**: an unknown
  path serves `docs/404.html`, which reads `location.pathname`, extracts `<event>`, and renders that
  event's directory (reusing the index logic).
- **Discovery — per-own-account, least maintenance (owner).** Timekeepers keep their own GitHub
  accounts; the directory reads a **stable, committed list of timekeeper accounts**
  (`docs/live-config.json`, rarely changes) and auto-lists each account's "cozer live order" gists.
  No shared login, no per-broadcast registry; adding a timekeeper = add their account once.
- **Feed additions (group + disambiguate):**
  - `event` — a slug from the `.cozj` name (the `/cozer/<event>/` key);
  - `event_meta` — `{title, date, venue}` (so a same-slug-different-event is shown distinctly);
  - `station` — a per-timekeeper label (operator / GitHub login) so two stations on the **same** event
    are told apart on the page.
- **Same-name collision — handled gracefully (owner's concern).** Two operators using the same `.cozj`
  name share the `/cozer/<event>/` slug — *intended* for the same event (both stations show, by
  `station`). For genuinely different events colliding on a name, the page still lists both, labelled
  by `event_meta` (date/venue) + `station` — never a wrong merge or a crash; the viewer disambiguates
  by metadata. Policy can discourage name reuse; the system handles it either way.
- **Robustness — sshfs (owner).** Operators run cozer over **sshfs** (latency / "sleeping"): publishing
  stays off the timing path (background thread) and best-effort; config/gist writes may lag but must
  never stall timing. The directory tolerates a channel being briefly stale/unreachable.
- **Split:** feed fields (`event`/`event_meta`/`station`) — `live.py` (7948e787) + the Timer populates
  them (b76f2173); directory + `404.html` router + per-event page — `docs/` (7948e787).

## 12. Future — corrected results on the channel page (large; plan later)

Owner idea: once Edit-Records corrections are applied, publish the **corrected results** on the same
page (alongside / after the live order). A larger feature — official-ish result rendering, deciding
when/what to publish, and the official-vs-unofficial line. **Deferred**: plan once the live MVP has run
at a real event.

- **D-LIVE-8 — Viewer is a chroma-key overlay (owner 2026-07-21).** Top-left, rows-only, uniform
  `--key` navy behind everything (keyed transparent on the video stream); columns NAT-flag · boat# ·
  surname (+ laps · gap once started); flags are static repo data (docs/flags/<IOC>.svg, no CDN) with a code-text fallback. Reference:
  the real OSY400 broadcast strip (`Pasted image.png`) — direction, not a copy. Feed gained
  `started`/`laps`/`time` (§4); Timer passes `standings(rec)` so those flow.

## 13. Rate limits & the broadcast account (2026-07-21)

> **Now that the self-hosted server (§8) is primary, this whole section applies only to the gist
> *fallback*.** The server has **no rate limit**, is always fresh, and needs no token in any URL — it
> sidesteps everything below. Kept for when the gist path is used.

The gist API has two limits: **60 req/hour anonymous** (per IP) and **5,000 req/hour authenticated**
(per account). This decides how viewers fetch and whether a dedicated account is worth it.

- **Viewers use the RAW gist file (`&user=<login>` → `gist.githubusercontent.com/<user>/<id>/raw/...`),
  which is CDN-served and *not rate-limited at all*.** So an **anonymous** viewer is fine — no token
  needed, no 60/hr wall. This is the URL cozer surfaces. Freshness is CDN-bounded (seconds-to-~1 min),
  which is plenty for lap-line crossings. `poll_s` tunes cadence (default 3 s).
- **Do NOT put a token in the surfaced/streamed URL.** A PAT in a URL shown on-screen/on-stream leaks.
  `&token=` (authed API, freshest, 5,000/hr) stays a manual power-user option, not the default.
- **cozer's publishing** is authed (the operator's signed-in account), a `PATCH` per crossing
  debounced to ≤1/2.5 s → a few hundred/hour, a tiny slice of 5,000/hr. Never a problem.
- **Estimate from cozer (recommended):** the gist API returns `X-RateLimit-Remaining` /
  `X-RateLimit-Reset` on every publish response — cozer can surface those directly (accurate, no
  guessing) instead of estimating. With raw-path viewers, the only API consumer is cozer's own
  writes, so "remaining" stays near 5,000 all event.
- **cozer-broadcast-bot account — optional, not needed for limits.** Since reads are raw (unlimited)
  and writes are tiny, the operator's own account suffices. A dedicated bot account's value is
  *identity + directory*: all channels live under one known account, so §11's directory can enumerate
  `gists?per_page=100` for that single account, and operators' personal accounts stay out of it. Cost:
  shared credentials on each timekeeper's machine. **Deferred** — revisit if/when the multi-station
  directory (§11) is built; for the MVP each operator broadcasts under their own account.

## Change log
- **2026-07-21** — Plan created; owner decisions D-LIVE-1..5 (gist MVP; controlled screens; event-driven
  cadence; class+phase header replacing the UIM logo, rows + COZER logo + update-time + unofficial
  label; Timer checkbox). Viewer design-preview artifact published. Seeded by `7948e787`.
- **2026-07-21** — MVP built (both sessions): `live.py` backend (`6cd32a6`), Timer broadcast checkbox
  (`852321a`), `docs/live-viewer.html` (`e7fab81`), Timer viewer-URL row (`e3dbe03`); GitHub Pages
  enabled → viewer at `https://pearu.github.io/cozer/live-viewer.html`.
- **2026-07-21** — **Broadcast lifecycle refined (owner):** publish **on tick** from the current ladder
  (pre-start shows the field), not on first crossing; **on untick** publish a `live:false` "stopped"
  snapshot → viewer shows "disabled". Added `live` field (§4) + `live.stopped()`; viewer renders the
  disabled state. Backend + viewer done (7948e787, 615 green); Timer tick/untick wiring is b76f2173's.
- **2026-07-21** — **Channel directory** landed (`docs/index.html`, `dac2f6e`) — fixes the Pages 404;
  auto-lists an account's cozer-live gists as channels. Owner decisions recorded (§11): clean
  per-event URLs via a `404.html` router; per-own-account discovery via a committed account list;
  feed `event`/`event_meta`/`station` fields; graceful same-name handling; sshfs robustness. §12: the
  corrected-results-on-page feature deferred.
- **2026-07-21** — **Viewer reworked into a chroma-key overlay** (D-LIVE-8): top-left, rows-only,
  uniform navy, NAT-flag · boat# · surname (+ laps · gap once started), flags bundled as docs/flags/<IOC>.svg (no CDN) + code fallback.
  Feed gained `started`/`laps`/`time`; `live.snapshot` accepts `standings()` dicts (back-compat with
  scalar ids); +tests (9 green). Timer to pass `standings(rec)`. Viewer + backend done (7948e787).
- **2026-07-21** — **Empty-page fix + rate-limit design** (§13). Root cause: anonymous gist-API
  polling hit 60/hr. Fix (pushed): viewer polls the **raw** gist file via `&user=<login>` (not
  rate-limited, anonymous-safe, no token-in-URL), never-blanks (status + last-good render), and takes
  its poll interval from **`view.poll_s`** (default 3 s). Recommend cozer surface the URL with
  `&user=<login>` and read `X-RateLimit-*` headers for a live budget readout; a bot account deferred.
- **2026-07-21/22** — **Transport moved off the gist to a self-hosted server** (owner + `b76f2173`),
  live at `https://live.cozer.ee/` (630 green). New `deploy/live-server/` (stdlib `server.py`:
  `POST /publish/<ch>` secret-authed, `GET /live/<ch>.json`, `GET /stream/<ch>` SSE, + serves the
  viewer/flags) behind Caddy (auto-HTTPS) + systemd; `live.publish_server()`; Timer "Broadcast
  settings…" dialog + server-or-gist selection + 500 ms throttle; viewer `?channel=`/`?src=` with SSE +
  poll fallback (gist path kept as fallback). **Doc updated (this pass, `7948e787`):** header/§3/§5/§7,
  §8 rewritten to the self-hosted server (was "future upgrade"), §13 scoped to the gist fallback.
