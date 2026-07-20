# Release & in-app update plan

> **Status:** plan (2026-07-21, owner-decided). Sequenced roadmap for the first public release
> and the in-app update mechanism. Owner decisions are recorded in §2; nothing here is
> implemented yet except where a ✅ says so.

## 1. Where we are today

- **Package:** `cozer` wheel, launched via `python -m cozer` (`cozer/__main__.py`). No
  `[project.scripts]` console entry.
- **Version `3.0.0.dev0`**, hard-coded in **three** places that must stay in sync:
  `pyproject.toml`, `cozer/__init__.py`, `installer/construct.yaml` (the latter also pins the wheel
  filename in `extra_files`).
- **Windows installer** (`.github/workflows/windows-installer.yml`, on `push tags: v*` or manual):
  conda **`constructor` + NSIS** → `COZER-<ver>-Windows-x86_64.exe`. It lays down a bundled conda
  env at `C:\cozer` (python 3.13, pyside6, weasyprint, pip) and `post_install.bat` pip-installs the
  cozer wheel shipped inside the installer. **So the Windows "exe" is an installer around a real
  `python.exe` + pip — not a frozen PyInstaller binary.** Launched via `installer/cozer-launch.pyw`.
- **CI** (`ci.yml`): tests on Linux + Windows, coverage badge/comment. Runs on push/PR.
- **In-app GitHub client already exists:** `cozer/app/crashreport.py` has OAuth device-flow,
  `_http(method, url, token, data, transport)`, and `REPO = "pearu/cozer"` — reused below for the
  update check (no new HTTP stack).
- **No git tags, no GitHub Releases yet.** `windows-installer.yml` only uploads an *Actions
  artifact* (needs a login to download) — it does **not** publish a Release.

## 2. Decisions (owner, 2026-07-21)

- **D-REL-1 — Update UX: one adaptive action.** A single **Help ▸ "Check for updates…"** that
  detects the install kind and picks the right action itself (fast wheel update vs full installer),
  rather than two separate "Update"/"Upgrade" menu items. Simplest for a novice operator.
- **D-REL-2 — First release version: `3.0.0rc1`** (release candidate — feature-complete but still
  being battle-tested; bump to `3.0.0` once proven at a real event).
- **D-REL-3 — Push timing: after reviewer sign-off.** Push `main` once `7948e787` finishes the
  posting-metadata review (closes #15 and #19 via their `Fixes` trailers).

## 3. Roadmap (sequenced)

### Phase 0 — prep (not blocked on push; can start now)
- **Single-source the version.** Kill the 3-way drift: a `tools/bump_version.py` (or make
  `construct.yaml` read the version from `cozer.__version__` at build time, and stop pinning the
  wheel filename — glob it). One command sets the version everywhere.
- **In-app update *check* module** `cozer/app/update.py` (read-only): `latest_release()` via
  `crashreport._http` → `GET /repos/pearu/cozer/releases/latest`; a PEP 440 version compare;
  `install_kind()` (source / wheel / windows-installer, e.g. via the `cozer-launch.pyw` marker the
  installer drops in `sys.prefix`); returns a result (current, latest, newer?, release notes,
  assets). Unit-tested with a fake transport (like the crashreport tests). **No apply yet.**
- **Help ▸ "Check for updates…"** menu item that runs the check and shows the result
  (up-to-date / update available + notes + link). Manual only at first.

### Phase 1 — first release (after reviewer sign-off → push)
1. Reviewer signs off → **push `main`** (closes #15, #19).
2. Bump version → **`3.0.0rc1`** (one command, per Phase 0).
3. Add a **Release step to `windows-installer.yml`**: `gh release create v3.0.0rc1` and upload
   **both** the installer `.exe` **and** the wheel as release assets. The Release becomes the single
   public source the app updates from.
4. Tag `v3.0.0rc1` → CI builds the installer + attaches assets → the first live Release.

### Phase 2 — apply the update (Windows only, per scope; needs a live release to test)
The adaptive action, driven by `install_kind()` + what the release provides:
- **Fast (wheel):** download the release wheel → `sys.executable -m pip install -U --no-deps
  <wheel>` → prompt restart. Right when only cozer code changed. Works on the constructor env
  (it has pip) and any pip install.
- **Full (installer):** download + run the new `COZER-*.exe` → replaces the whole bundled env.
  Needed when dependencies change. The NSIS installer handles the replace; cozer quits and the
  installer relaunches.
- **Which to offer:** the release carries a marker (e.g. a `deps-changed` label / a
  `min-installer` field in the release body) so the app knows if the fast path is safe; default to
  the full installer when unsure.
- **Non-Windows:** the check is shown but the action is informational (`pip install -U` / `git
  pull`) — never mutate a dev checkout.

### Phase 3 — optional polish
- **Throttled startup check** (once/day, background, reusing the offline-tolerant Reporter
  pattern) → an unobtrusive "update available" line; manual "Check now" always present.
- **PyPI publish** (would enable a plain `pip install -U cozer` for the wheel path) — decide later;
  not required since the wheel ships as a Release asset.

## 4. Safety / principles
- Never auto-apply; always confirm and show the release notes first.
- Verify the downloaded asset (size / sha from the Release metadata).
- The installer path is inherently safest (same signed CI pipeline); prefer it when unsure.
- `install_kind() == "source"` → informational only; never touch a git working tree.

## Change log
- **2026-07-21** — Plan created; owner decisions D-REL-1..3 recorded (adaptive action; `3.0.0rc1`;
  push after reviewer sign-off).
