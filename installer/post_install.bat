@echo off
rem constructor post-install script (Windows). %PREFIX% = install location.

rem Diagnostics (visible in CI logs) -- helps confirm what the installer exposes about its own
rem directory, for the "cozer wheel next to the installer" offline fallback.
echo [post_install] CD=%CD%
echo [post_install] EXEDIR=%EXEDIR%  INSTALLER_UNPACK_DIR=%INSTALLER_UNPACK_DIR%  PREFIX=%PREFIX%

rem 1) Install cozer into the environment. The installer ships the ENVIRONMENT only; install_cozer.py
rem    fetches the LATEST cozer wheel from GitHub (offline: an adjacent cozer-*.whl, else a clear
rem    message). Forward the installer's own directory so the offline fallback can look there.
if defined EXEDIR set "COZER_INSTALLER_DIR=%EXEDIR%"
"%PREFIX%\python.exe" "%PREFIX%\install_cozer.py"

rem 2) Desktop + Start-menu shortcuts (the Desktop icon is the reliable, visible result). Runs even if
rem    the cozer install above failed, so the operator still gets an icon and -- via cozer-launch.pyw's
rem    startup-error dialog -- a clear message.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PREFIX%\make_shortcut.ps1"

exit /b 0
