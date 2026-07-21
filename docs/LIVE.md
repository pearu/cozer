# Live ordering feed — unofficial real-time running order

> **Status: BUILT + LIVE.** The MAINTENANCE_PLAN **Phase 7 / DoD #6** feature: cozer publishes the
> *unofficial* live running order during a race; a chroma-key browser overlay renders it (like the
> on-screen order in motorsport TV). **Transport: a self-hosted server on the owner's box, live at
> `https://live.cozer.ee/` with SSE push (~0.5 s latency) — see §7.** The URL model (path-based,
> `/<event>/feed/<channel>/`) is specified in **`docs/broadcast-urls.md`**. Built jointly by `7948e787`
> (feed / viewer / flags / this doc) and `b76f2173` (Timer / live-server / deploy).
>
> **History:** this started **gist-first** (MVP) — but the gist *raw* path proved **~60 s stale**
> (GitHub refreshes raw content server-side ~1/min; edge cache-busting doesn't defeat it) and the *API*
> path is rate-limited + needs a token in the URL. So the transport moved to the self-hosted server; the
> decoupled sink (§3) made that a drop-in. **The gist path has since been fully removed** (the server is
> the only transport); see the change log.

## 1. What it is

During a heat, as boats cross the lap line the operator records the crossing in the **Timer**; the
running order changes. When broadcasting is on, cozer pushes a small **ordering snapshot** to the live
server; one or a few **viewer screens** (broadcast overlay / venue display) render it. It is explicitly
**unofficial** — distinct from the §209 official signed/posted results.

## 2. Decisions (owner)

> Two early decisions below were later **superseded**, kept here as the record: the **gist transport**
> (D-LIVE-1/2) by the self-hosted server (§7); the **timing-tower layout** (D-LIVE-4/6) by the
> chroma-key overlay (D-LIVE-8).

- **D-LIVE-1 — Transport: GitHub Gist (MVP).** *(superseded — §7.)* Reused the authenticated GitHub
  client; zero new hosting/auth for a first cut.
- **D-LIVE-2 — Audience: a few controlled screens, not public.** *(superseded — the self-hosted server
  is a public, known-link feed.)*
- **D-LIVE-3 — Cadence: event-driven.** Publish when the operator records a crossing (the order
  changed), throttled; a couple of seconds from click to a live update is fine.
- **D-LIVE-4 — View contents.** *(superseded by D-LIVE-8.)* The original "timing-tower" look: class +
  phase header, position · boat# · surname · nationality rows, COZER logo, timestamp, "unofficial".
- **D-LIVE-5 — Timer control + lifecycle:** a **"Broadcast live order"** toggle — publishes **on tick**
  (the current ladder, even pre-start), **updates on crossings**, and publishes a **"stopped"** snapshot
  on **untick** (viewer shows "live stream disabled"). The clickable viewer URL sits next to it (§5).
- **D-LIVE-6 — Large fields.** *(the tower paged; the chroma-key overlay caps at `view.max_rows`, §4.)*
- **D-LIVE-8 — Viewer is a chroma-key overlay (owner).** Top-left, rows-only, uniform `--key` navy
  behind everything (keyed transparent on the video stream); columns NAT-flag · boat# · surname (+ laps
  · gap once started). Reference: the real OSY400 broadcast strip (`Pasted image.png`) — direction, not
  a copy. See §6.

## 3. Architecture — the transport sink

cozer never talks to the transport inline. A small **publisher** computes an ordering snapshot and
hands it to the **sink**:

```
Timer crossing ──▶ order snapshot (from standings()) ──▶ publish (background thread)
                                                          └─▶ live.publish_server()  → self-hosted server (§7)
```

This decoupling is what let the transport move gist → self-hosted server touching **only** the sink and
the viewer's data source — the Timer, the snapshot shape (§4), and the overlay render were unchanged.
`cozer/app/live.py` is Qt-free and headless-testable.

## 4. Data model — the snapshot

Small, stable, viewer-agnostic JSON (the "machine feed"):

```json
{
  "class": "F 500", "phase": "circuit", "heat": "2",
  "updated": "2026-08-15T14:32:05Z", "unofficial": true, "live": true, "started": true,
  "view": {"max_rows": 24, "poll_s": 0.5, "page_size": 10, "top_dwell_s": 20, "page_dwell_s": 6},
  "order": [
    {"pos": 1, "boat": "7",  "surname": "Tamm",  "nat": "EST", "laps": 2, "time": 40.0},
    {"pos": 2, "boat": "14", "surname": "Ozols", "nat": "LAT", "laps": 2, "time": 41.5}
  ]
}
```

- `order` is built from **`timer.standings(rec)`** (leader-first), joined to participants for surname +
  `countries.IOC` nat. It is always the **full** field — the viewer caps it (§6).
- `phase` is the phase kind (`timetrial`/`qualification`/`circuit`/`endurance`); the viewer maps it to a
  display word.
- `updated` is stamped at publish time.
- **`live`** is `true` while broadcasting; a **`false`** snapshot (empty `order`) is published on untick
  so the viewer shows a *"live stream disabled"* state rather than stale positions.
- **`started`** is `true` once any boat has completed ≥1 lap (crossed the first lap-line). The overlay
  shows only NAT/boat/surname before start, then reveals laps + gap once started.
- **`laps`** (completed laps) and **`time`** (cumulative seconds at the last crossing) per order row.
  The overlay shows `laps`, and the **gap** = this boat's `time` minus the boat one place ahead's (or
  `+N L` when a lap down). Absent for a not-yet-started boat.
- **`view`** — the operator-configured display parameters, set *in cozer* and shipped in every snapshot:
  **`max_rows`** (top-N drivers; default 24, `0` ⇒ all), **`poll_s`** (viewer poll interval, seconds),
  and the timing-tower params (`page_size`/dwell, unused by the chroma-key overlay). The viewer obeys
  these and holds no view constants of its own.

## 5. cozer side (publisher + Timer)

- **`cozer/app/live.py`** — `snapshot(eventdata, cl, heat, order, updated, view=None, live=True)` builds
  the §4 feed (`order` = `standings(rec)` dicts or bare ids); `stopped(...)` is the `live:false` untick
  snapshot; **`publish_server(base_url, eventname, channel, secret, snap)`** POSTs to the live server
  (`docs/broadcast-urls.md`). Raise-on-error; the Timer guards it off the timing path.
- **`cozer/app/broadcast.py`** — Qt-free slug/URL helpers shared by the Timer, the Reports settings, and
  `live.py`: `slugify`, `event_name`/`event_channel` (read from the `.coz`), `feed_path`, `viewer_url`.
- **Timer "● Broadcasting" toggle — lifecycle:**
  - **on tick:** publish **immediately** from the current ladder order (pre-start = the field in ladder
    order, so a viewer opened before the start already shows the grid);
  - **on each crossing:** update — throttled ~1 post / **0.5 s** (the server has no rate limit → low
    latency), off the timing path;
  - **on untick:** publish `live.stopped(...)` → the viewer shows "live stream disabled".
  The **clickable/copyable viewer URL** (`<live_server_url>/<eventname>/feed/<channel>/`) sits next to
  the toggle once a broadcast is configured.
- **Where settings live (docs/broadcast-urls.md §3):** the **Reports tab** collects `live_server_url` +
  `live_publish_secret` (→ cozer **config**, per operator) and the event name + channel (→ the **`.coz`**,
  per event). The secret must **never** reach the `.coz` (its content is embedded in bug reports).
- **Never block timing.** The publish runs in a background thread; a failed/slow post is a status note,
  off the Timer's critical path — timing never stalls for the network.

## 6. The viewer

`docs/live-viewer.html`, served by the live server, designed as a **chroma-key video overlay** (D-LIVE-8):
- **Layout:** **top-left**, **driver rows only** — no header/footer/column-header/total rows. Columns
  **NAT (country flag) · boat# · surname**, and once **started** also **laps · gap** (time to the boat one
  place ahead, or `+N L` a lap down). Caps at `view.max_rows` (default 24).
- **Chroma-key:** everything that is **not text or a flag** is one uniform **`--key` navy** (`#0a1a2f`) —
  no gradients, chips, borders, or row shading — so the stream keys that navy transparent, leaving only
  the text + flags.
- **Flags:** **static repo data** — `docs/flags/<IOC>.svg` (206 flags, public-domain from flag-icons),
  keyed by the 3-letter code (no mapping, no runtime CDN); served by the server at `/_flags/<IOC>.svg`.
  A missing/failed flag **falls back to the code text**.
- **Data source:** served at `https://live.cozer.ee/<event>/feed/<channel>/`, it uses **SSE**
  (`EventSource(".../stream")`, sub-second) with a **poll fallback** (`.../data.json`); `?src=<url>`
  polls any feed URL; the bare root shows a neutral landing. (The design-preview artifact can't fetch
  (CSP), so its flags show as codes — it fixes the *design* only.)

## 7. Self-hosted live server (the transport — `https://live.cozer.ee/`)

The owner's own box (fixed IP, fiber) runs a tiny server that holds the latest snapshot per feed and
serves viewers directly — fresh, no rate limit, no token in any URL. **The URL model is specified in
`docs/broadcast-urls.md`**; event name + channel are lowercase slugs, server-owned paths are `_`-prefixed.

**`deploy/live-server/`** (its `README.md` + the owner's git-ignored `live_cozer_ee-setup.txt` runbook;
owned by `b76f2173`):
- **`server.py`** — stdlib only, binds `127.0.0.1:8099`; snapshots kept **in memory** (a restart drops
  them, cozer re-publishes on the next tick → self-heals). Routes:
  - `POST /_publish/<event>/feed/<channel>` — write the latest snapshot; auth = shared secret in the
    `X-Publish-Secret` header. Body-size-capped + JSON-validated.
  - `GET /<event>/feed/<channel>/data.json` — public read of the latest snapshot (CORS `*`).
  - `GET /<event>/feed/<channel>/stream` — **SSE push** (sub-second); 15 s keepalive; a global
    `MAX_STREAMS` cap returns 503 past it. `GET /<event>/feed/<channel>/` serves the viewer.
  - `GET /_flags/<IOC>.svg`, `GET /_healthz`; the bare root serves the neutral viewer landing.
- **`Caddyfile`** — Caddy fronts it: automatic Let's Encrypt HTTPS for `live.cozer.ee`, reverse-proxy to
  `127.0.0.1:8099`, `flush_interval -1` so SSE isn't buffered. Only Caddy is internet-facing.
- **`cozer-live.service`** — systemd unit (boot-start, `Restart=always`, `NoNewPrivileges`,
  `PrivateTmp`); reads the secret from root-only `/etc/cozer-live.env`.
- **Ports:** router forwards **80 + 443** (one-time); add more services later by hostname (a new Caddy
  block) — no new port changes.

**Why self-host** (vs a managed Cloudflare KV / Firebase / Supabase): the owner already has a fixed-IP
fiber box → full control, no third-party account/limits; and plain KV stores are *eventually consistent*
(~60 s), which would repeat the gist problem — an SSE **push** server avoids it. Trade-off: it's a single
box (owner's home server); there is no fallback transport (the gist path was removed).

## 8. Caveats

- **Unofficial, always.** It is the live *running order*, never the §209 official result (the
  signed/posted sheet). Keeps the two from being confused.
- **Timing is sacred.** The publish path is best-effort and fully off the Timer's critical path.
- **Privacy:** the feed carries boat # / surname / nationality — public race info shown at the venue;
  nothing more.

## 9. Channel directory & per-event pages — superseded

An earlier plan (gist + GitHub **Pages**, a `docs/index.html` directory + a `404.html` SPA router
enumerating per-account gists) is **retired** along with the gist transport and Pages (owner: retire
Pages entirely; `live.cozer.ee` is the sole host). The **path-based server model** (`docs/broadcast-urls.md`)
replaces it: each event/channel has its own URL `/<event>/feed/<channel>/`, and multiple timekeepers use
distinct channels (`a`, `b`) under one event. A **server-side directory** (list the events/channels the
server currently holds) is a possible future if a landing index is wanted.

## 10. Future — corrected results on the channel page (large; plan later)

Owner idea: once Edit-Records corrections are applied, publish the **corrected results** to
`/<event>/<reporttype>/` (event-wide, no channel; `docs/broadcast-urls.md` §5) — the event's home on
`live.cozer.ee` becomes the live feed during the race and static results after. A larger feature
(official-ish result rendering, when/what to publish, the official-vs-unofficial line). **Deferred.**

## Change log
- **2026-07-21** — Plan created; owner decisions D-LIVE-1..5 (gist MVP; controlled screens; event-driven
  cadence; timing-tower view; Timer checkbox). Seeded by `7948e787`.
- **2026-07-21** — Gist MVP built (both sessions): `live.py` backend, Timer broadcast checkbox, the
  viewer, the Timer viewer-URL row; broadcast lifecycle (publish on tick, `stopped` on untick).
- **2026-07-21** — Viewer reworked into a **chroma-key overlay** (D-LIVE-8): top-left, rows-only, uniform
  navy, NAT-flag · boat# · surname (+ laps · gap once started); flags bundled as `docs/flags/<IOC>.svg`;
  feed gained `started`/`laps`/`time`; `max_rows` (top-24) + `poll_s`.
- **2026-07-21** — Empty-page/latency work while still on gist: confirmed the gist *raw* path is ~60 s
  eventually-consistent (unfit for live); the gist *API* path is fresh but rate-limited + needs a token
  in the URL. This motivated the transport move.
- **2026-07-21/22** — **Transport moved off the gist to the self-hosted server** (owner + `b76f2173`),
  live at `https://live.cozer.ee/`: `deploy/live-server/` (SSE + poll + static, secret-authed publish)
  behind Caddy + systemd; `live.publish_server()`; Timer server publishing + 0.5 s throttle; viewer
  `?channel=`/`?src=` + SSE. Then **path-based URLs** (`/<event>/feed/<channel>/`, `docs/broadcast-urls.md`),
  broadcast settings under the Reports tab, one Timer toggle, event name/channel in the `.coz`.
- **2026-07-22** — **Gist transport fully removed** (`7948e787`, owner-directed): dropped
  `live.create_gist`/`update_gist`/`publish` + the Timer/viewer gist paths + `crashreport`'s `gist`
  OAuth scope; retired GitHub Pages (`docs/index.html`, the §9 directory plan). The self-hosted server is
  now the only transport. Docs rewritten to match (this pass); gist §6 + rate-limits §13 removed.
