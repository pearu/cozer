# cozer live-order server — deployment

Self-hosted transport for the Phase-7 live feed (replaces the GitHub gist). cozer POSTs a snapshot per
channel; viewers GET the latest over HTTPS. Fronted by **Caddy** (auto Let's Encrypt) at
`https://live.cozer.ee/`. See the full runbook in the repo root: `live_cozer_ee-setup.txt` (local only).

**Prerequisites (already done):** `live.cozer.ee` → the public IP; router forwards 80+443 → the
server; nothing else on 80/443.

Files here:
- `server.py` — the live-server (stdlib Python; binds `127.0.0.1:8099`).
- `cozer-live.service` — systemd unit (auto-start on boot, auto-restart, survives logout).
- `Caddyfile` — HTTPS reverse proxy `live.cozer.ee` → `127.0.0.1:8099`.

## Deploy (all `sudo` steps are yours to run on the server)

**1. Free up 80/443** — stop any temporary listener from the port test:
```
# Ctrl-C the `sudo python3 -m http.server` windows, or:
sudo fuser -k 80/tcp 443/tcp   # only if you had test listeners there
```

**2. Shared secret** — generate one and put it in a root-only env file (kept OUT of git):
```
sudo sh -c 'umask 077; printf "PUBLISH_SECRET=%s\nPORT=8099\n" "$(openssl rand -hex 32)" > /etc/cozer-live.env'
sudo cat /etc/cozer-live.env      # copy the PUBLISH_SECRET value — cozer needs the same one
```

**3. The live-server as a systemd service:**
```
sudo cp deploy/live-server/cozer-live.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cozer-live
systemctl status cozer-live --no-pager
curl -s localhost:8099/healthz && echo         # -> ok
```
(If your checkout path or user differ from the defaults in the unit, edit `User`/`ExecStart` first.)

**4. Caddy (HTTPS):**
```
sudo apt install -y caddy
sudo cp deploy/live-server/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
# first request triggers cert issuance; give it a few seconds, then:
curl -sI https://live.cozer.ee/healthz          # -> HTTP/2 200, valid cert
```

**5. Point cozer at the server** (on the operator's machine, in cozer's config):
- `live_server_url` = `https://live.cozer.ee`
- `live_publish_secret` = the `PUBLISH_SECRET` from step 2
- `live_channel` = a name for this event's feed (e.g. `harku2026`)

**6. End-to-end check:**
```
# publish a test snapshot (as cozer would):
curl -s -X POST -H "X-Publish-Secret: <SECRET>" -d '{"order":[],"live":true}' https://live.cozer.ee/publish/test
# read it back (as a viewer would):
curl -s https://live.cozer.ee/live/test.json
```
Then the broadcast viewer points at `https://live.cozer.ee/live/<channel>.json`.

## Operate
```
systemctl status cozer-live caddy
journalctl -u cozer-live -f            # live-server logs
journalctl -u caddy -f                 # Caddy / cert logs
sudo systemctl restart cozer-live      # after pulling an update to server.py
```

## Notes
- **Secret** lives only in `/etc/cozer-live.env` (root, `600`) — never in git.
- **Snapshots** are in memory; a restart drops them but cozer re-publishes on the next tick (self-heals).
- **More services later:** add a subdomain + another localhost port + a Caddy block — no new router/port
  changes (80/443 forwarding is one-time; Caddy routes by hostname).
