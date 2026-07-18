# COZER installer (constructor)

Builds a single native installer that bundles a conda base + cozer's runtime
dependencies (Qt/PySide6, WeasyPrint and its native cairo/pango/gdk-pixbuf/
fontconfig stack) so a user can install a working COZER on a clean machine with
no conda/pip knowledge. Uses [`constructor`](https://github.com/conda/constructor),
which ships real conda packages — avoiding the native-dependency fights that
PyInstaller/briefcase have with WeasyPrint.

> **Status: DRAFT.** Authored on Linux. The Windows-specific parts (NSIS build,
> `post_install.bat` echo-quoting, the PowerShell Start-menu shortcut) must be
> validated on a real Windows box or in CI before relying on it. Items marked
> **[verify]** below are the known unknowns.

## Files
- `construct.yaml` — the installer spec (name/version, channels, runtime `specs`,
  `post_install`, the bundled wheel).
- `post_install.bat` — runs after install: pip-installs the bundled cozer wheel,
  writes a `COZER.bat` launcher, and creates a Start-menu shortcut.
- `dist/` — build output: the cozer wheel goes here before running constructor
  (gitignored).

## Source of truth
`construct.yaml`'s `specs` mirror the **runtime subset** of the top-level
`../environment.yml` (the test-only `pytest`/`pytest-cov`/`hypothesis`/`pymupdf`
are omitted). If you add/upgrade a runtime dependency in `environment.yml`, update
`specs` too. **[verify]** whether to auto-generate `specs` from `environment.yml`
to remove the manual sync (a small pre-build script) — deferred for the draft.
Also keep `version:` in sync with `pyproject.toml` / `cozer/__init__.py`.

## Build locally (on Windows)
```bat
conda install -c conda-forge constructor conda-standalone nsis python-build
python -m build --wheel --outdir installer\dist        REM from repo root -> cozer-<ver>-py3-none-any.whl
cd installer
constructor .                                          REM -> COZER-<ver>-Windows-x86_64.exe
```
Then run the `.exe`. It installs the bundled env, adds a **COZER** Start-menu
entry, and `%PREFIX%\COZER.bat` launches `python -m cozer` (which keeps the
fontconfig-cache-segfault workaround from `cozer/__main__.py`).

## Testing in CI — yes, mostly
`.github/workflows/windows-installer.yml` (manual / on `v*` tags) does the full
loop on `windows-latest`:
1. **build** the wheel + run `constructor` to produce the `.exe`;
2. **silent install** it (`installer.exe /S /D=C:\cozer` — NSIS silent flags);
3. **smoke test** offscreen (`QT_QPA_PLATFORM=offscreen`): import cozer + PySide6,
   construct a `QApplication`, and render a PDF with WeasyPrint — this proves the
   bundled env's native deps actually load and work on a clean runner;
4. **upload** the `.exe` as a downloadable artifact.

What CI **can** verify: the installer builds, installs unattended, and the bundled
app imports + renders reports (the main native-dependency risk). What it **can't**:
drive the interactive GUI (no display) — that still needs a real Windows box, which
you'll do. The artifact from step 4 is exactly what you download to test manually.

## Known unknowns to validate on Windows **[verify]**
- `constructor` on `windows-latest` finding NSIS via the `nsis` conda package
  (else `conda install menuinst`/a system NSIS, or `constructor --conda-exe`).
- `post_install.bat`: the `> / >>` echo-quoting for `COZER.bat`, and `%%*` vs `%*`.
- The PowerShell `WScript.Shell` shortcut path + per-user vs all-users Start menu
  (constructor's `menuinst` is the more "native" alternative if this is flaky).
- `extra_files` wheel filename must match `pyproject` version exactly.
- `pythonw.exe` present in the bundled base (it ships with the `python` conda pkg).
