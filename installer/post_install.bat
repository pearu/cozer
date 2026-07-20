@echo off
rem constructor post-install script (Windows). %PREFIX% = install location.
rem DRAFT: validate on a real Windows box / CI.

rem 1) Install cozer itself into the bundled env, offline, from the shipped wheel
rem    (runtime deps are already present via construct.yaml `specs`, so --no-deps).
rem    Match the wheel by glob so this script is version-independent.
for %%W in ("%PREFIX%\cozer-*.whl") do "%PREFIX%\python.exe" -m pip install --no-deps --no-index "%%W"
del "%PREFIX%\cozer-*.whl"

rem 2) Start-menu shortcut -> pythonw running cozer-launch.pyw (no console window).
rem    cozer-launch.pyw adds <prefix>\Library\bin to the DLL search path so
rem    WeasyPrint/Qt find their native libraries, then runs cozer's main() (which
rem    keeps the fontconfig-cache-segfault workaround). Shortcut creation is in a
rem    real .ps1 (not inline) to avoid cmd<->PowerShell quoting pitfalls.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PREFIX%\make_shortcut.ps1"

exit /b 0
