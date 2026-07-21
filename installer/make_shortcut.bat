@echo off
rem Double-click this to (re)create the COZER Desktop + Start-menu icons.
rem
rem Keep this file in your COZER folder -- the one that contains python.exe
rem (e.g. C:\Users\<you>\cozer). COZER can live at ANY path; it does NOT need
rem to be at C:\cozer.
rem
rem Unlike "Run with PowerShell", this keeps the window open so you can read the
rem result, and it always runs even if PowerShell script-running is restricted.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_shortcut.ps1"
echo.
echo If you see "created:" lines above, COZER is ready -- look for the "COZER"
echo icon on your Desktop (and in the Start menu under All apps).
echo.
echo If you see an error instead, please send a photo of this window to Pearu.
echo.
pause
