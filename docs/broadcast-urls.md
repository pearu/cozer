# COZER live broadcast — URL model & settings (spec)

Agreed design (owner + `b76f2173`, 2026‑07‑22) for the path‑based live broadcast on the self‑hosted
server (`https://live.cozer.ee/`). Supersedes the flat `?channel=…` scheme. Implemented in
`deploy/live-server/server.py`, `docs/live-viewer.html`, `cozer/app/live.py`, `cozer/app/timer.py`,
and the Reports tab. See `docs/LIVE.md` for the broader live‑feature architecture.

## 1. URL model

```
https://live.cozer.ee/<eventname>/<reporttype>/<channel>/
```

- **`<eventname>`** — a short, memorable *broadcast name* chosen by the organizers (not derived from
  the free‑text title/venue/date). Default = the current **month+year digits**, e.g. `0726` (July
  2026). Two events in one month share the default → organizers pick a name.
- **`<reporttype>`** — the kind of output. **`feed`** = the live running order (what ships now). Other
  report‑type slugs (`results`, `participants`, …) are **reserved for the future** (publishing actual
  reports). `feed` is a reserved report‑type name.
- **`<channel>`** — a per‑operator sub‑identifier for the **feed** (two timekeepers on one event use
  `a` and `b`). Default = **`a`**. **Reports are event‑wide and omit the channel** (`/0726/results/`).

Examples: `…/0726/feed/a/` (live feed, channel a) · `…/0726/results/` (future report, no channel).

### Reserved server paths (never an event)
Server‑owned paths are **`_`‑prefixed** so they can never collide with an `<eventname>`:
- `GET /_healthz`
- `GET /_flags/<IOC>.svg` — the bundled flag SVGs (shared, absolute path; the viewer loads
  `/_flags/EST.svg`, which works at any depth like `/0726/feed/a/`).
- `POST /_publish/<eventname>/feed/<channel>` — publish a snapshot (secret‑authed).

### Slug rules (validated in cozer AND the server)
`<eventname>` and `<channel>`: `^[a-z0-9][a-z0-9-]*$` (lowercase letters/digits/hyphens, must start
alphanumeric). This automatically excludes a leading `_` (no clash with `/_…`) and dots/uppercase
(no clash with `/favicon.ico`, `/robots.txt`, `/.well-known/…`). Max ~63 chars. `<reporttype>` is a
similar slug; `feed` is reserved.

## 2. Feed endpoints (under the feed path)
A feed's own data lives **under its path** (not reserved):
- `GET /<eventname>/feed/`                    → the **channel switcher** (HTML): a header of buttons for
  the event's live channels; picking one shows that channel's overlay below. Channels are discovered
  from what has been published (see `index.json`), so channels from **different cozer instances** on the
  same event name appear automatically — no registration.
- `GET /<eventname>/feed/index.json`          → the event's live channels: `{event, channels:[{channel,
  age_s}]}`, derived from the store (`age_s` = seconds since that channel's last publish). No auth.
- `GET /<eventname>/feed/<channel>/`         → the viewer overlay (HTML)
- `GET /<eventname>/feed/<channel>/data.json` → the latest snapshot (public, read‑only, CORS `*`)
- `GET /<eventname>/feed/<channel>/stream`    → Server‑Sent Events (sub‑second push)
- `POST /_publish/<eventname>/feed/<channel>` → publish (needs `X-Publish-Secret`)

Internal store key = `<eventname>/feed/<channel>`.

## 3. Where settings are stored (the split)
| Setting | Stored in | Why |
|---|---|---|
| `eventname`, `channel` | **the event (.coz)** | per‑event; travels with the file; different `.coz` → different URL → **no multi‑instance clash** |
| which reports to publish (future) | the event (.coz) | per‑event output selection |
| `live_server_url` | **cozer config** (per operator) | infra, not per‑event |
| `live_publish_secret` | **cozer config — NEVER the .coz** | the .coz is embedded verbatim in bug reports; a secret there would leak |

## 4. UI
- **Reports tab** collects all `live.cozer.ee` settings (broadcast + reports are both *outputs*):
  server URL + publish secret (→ config, secret masked), event name + channel (→ event), and — later —
  which reports to publish. This is where the operator sets *what* gets published and *where*.
- **Timer tab** keeps **one toggle button** ("● Broadcasting" when on) to control the live feed during
  the race. It is **inert until broadcast is configured** (server URL + secret + event name present).
  - **ON** → publish the current order immediately; update on each lap‑line crossing; show nothing (an
    empty grid) until the first crossing.
  - **OFF** → publish a `live:false` snapshot → the viewer shows **“LIVE STREAM DISABLED”** + the COZER
    wordmark.

## 5. Future (deferred, not built)
After the race, the operator selects reports under the Reports tab to publish to
`/<eventname>/<reporttype>/` (event‑wide, no channel) — reusing the same authenticated upload. The
`<eventname>` becomes the event's home on `live.cozer.ee`: the live feed during, static results after.

## 6. Migration from `?channel=`
The current flat scheme (`/?channel=<ch>`, `/live/<ch>.json`, `/stream/<ch>`, `/publish/<ch>`) is
replaced by the path model above. Single deployment + single operator, so a clean cut (no dual‑support
needed). The gist transport has since been removed — the self‑hosted server is the only transport.
