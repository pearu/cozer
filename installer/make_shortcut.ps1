# Create the COZER Start-menu shortcut. Run by post_install.bat after install.
# Lives in the install prefix, so $PSScriptRoot == the install location.
$ErrorActionPreference = 'Stop'
$prefix = $PSScriptRoot
$programs = [Environment]::GetFolderPath('Programs')
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut((Join-Path $programs 'COZER.lnk'))
$sc.TargetPath = Join-Path $prefix 'pythonw.exe'           # windowless python
# quote the .pyw path (single-quoted PS string keeps the double-quotes literal),
# so an install dir with spaces still works
$sc.Arguments = '"' + (Join-Path $prefix 'cozer-launch.pyw') + '"'
$sc.WorkingDirectory = $prefix
$sc.Description = 'COZER - competition organizer'
$sc.Save()
