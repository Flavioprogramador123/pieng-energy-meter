# Launcher elevado - sem pausa
$ErrorActionPreference = 'Continue'
$env:PIENG_SETUP_NO_PAUSE = '1'
$log = Join-Path $env:TEMP 'pieng_setup_remote_server_launcher.log'
try {
    "START $(Get-Date -Format o)" | Set-Content $log -Encoding UTF8
    & 'C:\Users\flavi\projeto\pieng-energy-meter\scripts\setup_remote_server.ps1'
    "END exit=$LASTEXITCODE $(Get-Date -Format o)" | Add-Content $log -Encoding UTF8
} catch {
    "ERR: $_" | Add-Content $log -Encoding UTF8
    throw
}
