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

### Phase 0 — prep (not blocked on push) — ✅ DONE
- ✅ **Single-source the version** (`e87439f`). `cozer/__init__.py` `__version__` is the one source:
  `pyproject.toml` reads it via `dynamic=["version"]`; `post_install.bat` globs `cozer-*.whl`;
  `tools/bump_version.py` sets the remaining `construct.yaml` literals (version + wheel name) in one
  guarded command. (Was a 4-way drift: pyproject / `__init__` / construct.yaml / post_install.bat.)
- ✅ **In-app update *check* module** `cozer/app/update.py` (`3ab772c`, read-only): `latest_release()`
  via `crashreport._http` → `releases/latest`; PEP 440 compare (`packaging`, or a pre-release-aware
  fallback); `install_kind()` (source / wheel / windows-installer via the `cozer-launch.pyw` marker);
  `check()` → `{current, kind, latest, available}`. Fake-transport unit tests.
- ✅ **Help ▸ "Check for updates…"** (`3ab772c`): reports up-to-date / offline / update-available
  (release notes + link to the release page). Manual; the apply is Phase 2.

### Phase 1 — first release — ✅ DONE (2026-07-21)
1. ✅ **Pushed `main`** (`46bc089`, 63 commits) → **#15 and #19 auto-closed**.
2. ✅ **Bumped to `3.0.0rc1`** (`tools/bump_version.py`).
3. ✅ **Release step added to `windows-installer.yml`** (`gh release create` on a `v*` tag, uploads
   the `.exe` + wheel with `contents: write`).
4. ✅ **Tagged `v3.0.0rc1`** → the installer workflow built + **published Release `v3.0.0rc1`** with
   both assets (`cozer-3.0.0rc1-py3-none-any.whl`, `COZER-3.0.0rc1-Windows-x86_64.exe`). Verified:
   `releases/latest` returns it (not a prerelease) and `update.check()` sees it end-to-end.

### Phase 2 — apply the update — ✅ DONE (2026-07-21, `189e718`)
`update.recommend(check_result)` picks the action from `install_kind()`; the update-available
dialog's **"Update now"** button dispatches `_apply_update`:
- **`pip` (a plain pip install AND the Windows constructor install):** `pip install -U --no-deps
  <release wheel>` in-app — small, behind the scenes, no browser. cozer's wheel is pure Python with
  **no** runtime deps, so this replaces only cozer's own code (pyside6/weasyprint untouched) →
  restart prompt. The Windows install is a real env with pip, so it gets the same fast update as a
  pip install (owner call, 2026-07-21 — previously the Windows path opened the full installer).
- **`installer` (Windows, fallback):** if the release has no wheel, or the fast update fails / the
  bundled libraries changed, download + run the full installer (via **Open release page**).
- **`source` (a checkout):** informational only (`git pull` / `pip install -U .`) — never mutate a
  working tree.

**Install-guide direct link (release convention).** `docs/install-windows.md` + `.et.md` link to
`releases/latest/download/COZER-Setup-Windows.exe` — a **stable, version-independent** URL. So the
release workflow uploads the installer under that stable name (`cp` before `gh release upload`),
and the docs need **no per-release edit**. (The wheel keeps its versioned name; `update.py` finds
either asset by suffix.) Live from **`v3.0.0rc2`**: the direct link `releases/latest/download/
COZER-Setup-Windows.exe` resolves (302 → the rc2 asset). `v3.0.0rc1` (versioned asset) is
superseded.

### Phase 3 — polish
- ✅ **Startup update check** (owner-refined: startup-only, non-blocking). Checks once **when COZER
  is opened** — not a periodic timer — in a **background thread**, so no internet or a slow
  connection never blocks or delays opening COZER. A newer release is noted **unobtrusively** in the
  Log (and the status bar); silent when up to date or offline. Manual **Help ▸ Check for updates…**
  is unchanged. Skipped under tests via `COZER_NO_UPDATE_CHECK`.
- **PyPI publish** (would enable a plain `pip install -U cozer` for the wheel path) — deferred; not
  required since the wheel ships as a Release asset.

## 4. Safety / principles
- Never auto-apply; always confirm and show the release notes first.
- Verify the downloaded asset (size / sha from the Release metadata).
- The installer path is inherently safest (same signed CI pipeline); prefer it when unsure.
- `install_kind() == "source"` → informational only; never touch a git working tree.

## Change log
- **2026-07-21** — Plan created; owner decisions D-REL-1..3 recorded (adaptive action; `3.0.0rc1`;
  push after reviewer sign-off).
- **2026-07-21** — **Phase 0 done** (`3ab772c`, `e87439f`): version single-sourced; `update.py`
  check core + Help ▸ "Check for updates…" (status only). 604 green. Reviewer signed off on the
  posting-metadata work (86th coord msg) → **Phase 1 push is now unblocked** (owner to trigger).
- **2026-07-21** — **Phase 1 done**: pushed `main` (63 commits; #15/#19 closed), bumped to
  `3.0.0rc1`, added the `gh release create` step to the installer workflow, tagged `v3.0.0rc1` →
  **Release published** with the installer `.exe` + wheel. `releases/latest` + `update.check()`
  verified end-to-end. Phase 2 (adaptive apply) is now testable against a live release.
- **2026-07-21** — **Phase 2 done** (`189e718`): adaptive "Update now" apply — pip-U the wheel
  (pip installs), open the installer download (Windows), or informational (source). Also fixed the
  release to upload the installer under the **stable** name `COZER-Setup-Windows.exe` so the install
  guides' `releases/latest/download/…` direct link works with no per-release doc edits. 607 green.
- **2026-07-21** — **`v3.0.0rc2` cut**: pushed the §10-G qualification fix + Phase 2 + the
  stable-asset workflow fix, bumped to `3.0.0rc2`, tagged → Release live with the **stable**
  `COZER-Setup-Windows.exe` (+ wheel). Verified: `releases/latest` = rc2, the install-guide direct
  link resolves (302), `update.check()`/`recommend()` see rc2 end-to-end. CI green on main.
- **2026-07-21** — **`v3.0.0rc3` cut**: adds the fast in-app update on the Windows install (pip
  behind the scenes, no exe download) + jargon-free update dialogs (operators never see "pip").
  Verified: `releases/latest` = rc3, direct link resolves, and `recommend()` for a Windows install
  now returns the fast wheel update.
- **2026-07-21** — **Phase 3 startup check done** (owner: startup-only, non-blocking). MainWindow
  fires one background update check on open (`_start_update_check` → thread → `_update_ready`
  signal → `_on_update_check_result` logs an unobtrusive notice if newer). No timer; no blocking on
  no/slow internet. Disabled in tests (`COZER_NO_UPDATE_CHECK`, set in conftest). 608 green.
- **2026-07-21** — **`v3.0.0rc4` cut** — Windows-install hardening from the first tester (issue #22)
  plus two broadcast fixes (#20/#21). Windows install now works with **zero manual steps**:
  - **Launcher `pythonw.exe` fixes** (`10c5ac7`, `1c87f9e`): the icon "did nothing" because
    `pythonw` has no console → `sys.stdout/stderr` were `None` → cozer's first startup write killed
    the process; now redirected to a log. And GitHub sign-in failed with
    `CERTIFICATE_VERIFY_FAILED` → set `SSL_CERT_FILE` to the env's CA bundle (+ `ca-certificates` in
    specs). Plus a startup-error dialog (`6269949`) so any future silent crash is visible.
  - **Shortcut hardening** (`c458849`, `b0677e4`): create a **Desktop** icon (not just Start-menu),
    log to `make_shortcut.log`, and ship `make_shortcut.bat` + `cozer-debug.bat` for self-service.
  - **Broadcast** (`b7518a3`, `2c70a27`): build/publish off the GUI thread (no freeze on tick), and
    request the `gist` OAuth scope so the live feed can publish.
  617 green.
- **2026-07-21** — **`v3.0.0rc5` cut** — Timer **Race drop-down widened** so long multi-class labels
  are readable instead of elided ("Race...00 1") (issue #22, `ae4e1ef`). A **wheel-only** change
  (the installer is unchanged from rc4); delivered to existing installs via in-app Update. 618 green.
- **2026-07-21** — **Wheel-only release pipeline — DONE** (built + validated). Releasing is now split:
  - **`release.yml`** — every `v*` tag builds a **wheel-only** release on **ubuntu** (~seconds; pure-
    Python wheel) → `releases/latest`, what the in-app updater reads. Validated: the wheel builds on a
    bare runner. No Windows runner, no installer rebuild per cozer release.
  - **`installer.yml`** — on-demand (manual dispatch or an `installer-*` tag) builds the installer →
    a **fixed `windows-installer` prerelease** (stable URL
    `releases/download/windows-installer/COZER-Setup-Windows.exe`). Validated: release created, link
    resolves (302), and `releases/latest` stays the wheel (the prerelease never shadows it).
  - **Two version lines** (`tools/bump_version.py`): `bump_version.py <v>` = cozer wheel/code version
    (`__init__` + bundled-wheel filename); `--installer <YYYY.MM>` = date-based installer version
    (`construct.yaml version:`, now `2026.07`). Docs + `update.py` + `main.py` installer links point at
    the fixed `windows-installer` release. `windows-installer.yml` removed. 619 green.
  - **Still deferred (needs Windows testing):** the **environment-only installer** that self-updates
    to the latest wheel on install/first run (offline → adjacent-wheel fallback, else fail gracefully)
    and the **versioned install dir** `cozer-<installer-version>` (constructor `default_prefix`) — the
    two owner ideas below. The pipeline above is the foundation they build on.
  - **Design details (owner-decided; the env-only + versioned-dir parts are deferred):** a
    **wheel-only-by-default** release pipeline — rebuild the Windows
    installer only when its *environment* changes (Python/PySide6/WeasyPrint/ca-certificates or the
    launcher/shortcut files), with a **separate date-based installer version** (e.g. `2026.07`) and
    the installer download **decoupled** from `releases/latest` (a fixed `windows-installer` release/
    tag) so wheel-only releases don't break the fresh-install link. Owner idea to fold in: installer
    = **cozer-environment only**, self-updating to the latest cozer wheel on install/first run.
    **Offline first-run (owner-decided):** if there's no internet, use a cozer wheel sitting in the
    same directory as the installer if present, otherwise fail gracefully with a clear message.
  - **Re-install / upgrade (owner-decided):** constructor does NOT cleanly overwrite an existing
    install — it errors "File or directory already exists" and expects an empty target (constructor
    #804; the NSIS GUI exposes no in-place overwrite). So install into a **versioned directory**
    `cozer-<installer-version>` (e.g. `cozer-2026.07`, set via constructor `default_prefix`): each
    installer version lands in a fresh dir (never collides), versions coexist, and the fixed-name
    Desktop/Start shortcut (`COZER.lnk`) is repointed to the newest by `post_install`. Old env dirs
    can be deleted at leisure. (Windows-only.)
