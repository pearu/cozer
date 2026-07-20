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
- **`pip` (a plain pip install — the owner's path):** `pip install -U <release wheel>` in-app
  (small; cozer's wheel declares no runtime deps, so only cozer's code is replaced) → restart prompt.
- **`installer` (Windows constructor install — novice operators):** open the installer `.exe`
  download in the browser (the OS fetches the ~276 MB bundle); run it to upgrade.
- **`source` (a checkout):** informational only (`git pull` / `pip install -U .`) — never mutate a
  working tree.
- **Deferred:** the *fast-wheel-on-Windows* optimization (small update on the constructor env
  instead of the full installer) — needs a deps-changed signal in the release to be safe; the full
  installer is always correct, and Windows operators update rarely (between events), so this is fine.

**Install-guide direct link (release convention).** `docs/install-windows.md` + `.et.md` link to
`releases/latest/download/COZER-Setup-Windows.exe` — a **stable, version-independent** URL. So the
release workflow uploads the installer under that stable name (`cp` before `gh release upload`),
and the docs need **no per-release edit**. (The wheel keeps its versioned name; `update.py` finds
either asset by suffix.) NB: `v3.0.0rc1` was published with the *versioned* asset name before this
fix, so that direct link 404s until rc1 is re-released (re-tag) or the next release lands.

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
