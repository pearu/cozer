# Create the COZER shortcuts (Desktop + Start-menu). Run by post_install.bat after install, and
# re-runnable by hand via make_shortcut.bat if the icons are missing.
#
# It lives in the install prefix, so $PSScriptRoot IS the install location -- COZER works at ANY
# path (e.g. C:\Users\<you>\cozer); it does NOT need to be installed at C:\cozer.
#
# A Desktop icon is created as well as the Start-menu one because the Start menu doesn't always
# index a fresh entry right away, so the Desktop icon is the reliable, visible result. Everything
# is also written to make_shortcut.log in the install folder, so a silent install-time failure
# still leaves a trace we can read.
$prefix = $PSScriptRoot
$log = Join-Path $prefix 'make_shortcut.log'
function Log($m) { Write-Host $m; Add-Content -Path $log -Value $m }

try {
    "COZER shortcut -- install folder: $prefix" | Set-Content -Path $log

    # windowless python if present, else plain python (the shortcut still launches COZER)
    $target = Join-Path $prefix 'pythonw.exe'
    if (-not (Test-Path $target)) { $target = Join-Path $prefix 'python.exe' }
    if (-not (Test-Path $target)) {
        Log "ERROR: neither pythonw.exe nor python.exe is in $prefix -- is this the COZER folder?"
        exit 1
    }
    Log "launcher: $target"

    # quote the .pyw path (single-quoted PS string keeps the double-quotes literal) so a folder
    # with spaces still works
    $arguments = '"' + (Join-Path $prefix 'cozer-launch.pyw') + '"'
    $shell = New-Object -ComObject WScript.Shell

    $dests = @(
        (Join-Path ([Environment]::GetFolderPath('Programs')) 'COZER.lnk'),   # Start menu (All apps)
        (Join-Path ([Environment]::GetFolderPath('Desktop'))  'COZER.lnk')    # Desktop (always visible)
    )
    foreach ($dest in $dests) {
        $sc = $shell.CreateShortcut($dest)
        $sc.TargetPath = $target
        $sc.Arguments = $arguments
        $sc.WorkingDirectory = $prefix
        $sc.Description = 'COZER - competition organizer'
        $sc.Save()
        Log "created: $dest"
    }
    Log "OK"
} catch {
    Log ("ERROR: " + $_.Exception.Message)
    exit 1
}
