@echo off
rem constructor post-install script (Windows). %PREFIX% = install location.
rem DRAFT: validate on a real Windows box / CI (the .bat echo-quoting and the
rem PowerShell shortcut creation are the fiddly parts).

rem 1) Install cozer itself into the bundled env, offline, from the shipped wheel
rem    (runtime deps are already present via construct.yaml `specs`, so --no-deps).
"%PREFIX%\python.exe" -m pip install --no-deps --no-index "%PREFIX%\cozer-3.0.0.dev0-py3-none-any.whl"
del "%PREFIX%\cozer-3.0.0.dev0-py3-none-any.whl"

rem 2) Launcher: run the GUI with the bundled pythonw (no console window).
rem    `python -m cozer` keeps the fontconfig-cache-segfault workaround
rem    (cozer/__main__.py._ensure_fontconfig).
> "%PREFIX%\COZER.bat" echo @echo off
>> "%PREFIX%\COZER.bat" echo "%PREFIX%\pythonw.exe" -m cozer %%*

rem 3) Start-menu shortcut -> the bundled pythonw running `python -m cozer`.
set "SMDIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%SMDIR%\COZER.lnk');" ^
  "$s.TargetPath = '%PREFIX%\pythonw.exe';" ^
  "$s.Arguments = '-m cozer';" ^
  "$s.WorkingDirectory = '%PREFIX%';" ^
  "$s.Description = 'COZER - competition organizer';" ^
  "$s.Save()"

exit /b 0
