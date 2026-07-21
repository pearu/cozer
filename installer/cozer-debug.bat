@echo off
rem ============================================================================
rem  cozer-debug.bat  --  launch COZER so any startup error is VISIBLE
rem
rem  The normal COZER icon starts the app "silently" (pythonw.exe, no console),
rem  so if it fails to open you see nothing. This runs the same launcher with a
rem  console + writes everything to cozer-debug.log, so the error is captured.
rem
rem  Put this file in your COZER folder (the one with python.exe) and
rem  DOUBLE-CLICK it.
rem ============================================================================
setlocal
set "HERE=%~dp0"

if not exist "%HERE%python.exe" (
  echo [X] python.exe ei ole selles kaustas.
  echo     Pane see fail COZERi kausta ^(kus on python.exe^) ja proovi uuesti.
  echo.
  pause
  exit /b 1
)

echo COZERi kaust: %HERE%
echo Kaivitan COZERi... kui aken avaneb, on koik korras.
echo.
"%HERE%python.exe" "%HERE%cozer-launch.pyw" 1> "%HERE%cozer-debug.log" 2>&1
set "RC=%ERRORLEVEL%"

echo ----------------- cozer-debug.log -----------------
type "%HERE%cozer-debug.log"
echo ---------------------------------------------------
echo (valjumiskood: %RC%)
echo.
echo Kui COZER EI avanenud, saada fail cozer-debug.log ^(samast kaustast^)
echo voi pilt sellest aknast Pearule.
echo.
pause
