# Watchdog dos pollers do Energy Meter.
# Detecta o caso "processo vivo mas coleta parada" (falha vista em 2026-09-11->14)
# e reinicia o EnergyMeterServer.exe.
#
# Uso:
#   .\scripts\watchdog_collectors.ps1
#
# Registrado junto com register_service.ps1 (tarefa a cada 5 min).

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$exePath     = Join-Path $projectRoot "dist\EnergyMeterServer\EnergyMeterServer.exe"
$lockPath    = Join-Path $projectRoot "data\.scheduler.lock"
$logPath     = Join-Path $projectRoot "data\watchdog.log"
$psql        = "C:\Program Files\PostgreSQL\17\bin\psql.exe"

# Se a ultima medicao for mais velha que isto -> reinicia (pode vir do runtime_settings.json)
$maxStaleMinutes = 12
$healthUrl = "http://127.0.0.1:8001/"
$runtimePath = Join-Path $projectRoot "data\runtime_settings.json"

function Get-RuntimeFlags {
    $flags = @{
        watchdog_enabled = $true
        collectors_enabled = $true
        watchdog_stale_minutes = 12
    }
    if (-not (Test-Path $runtimePath)) { return $flags }
    try {
        $j = Get-Content $runtimePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -ne $j.watchdog_enabled) { $flags.watchdog_enabled = [bool]$j.watchdog_enabled }
        if ($null -ne $j.collectors_enabled) { $flags.collectors_enabled = [bool]$j.collectors_enabled }
        if ($null -ne $j.watchdog_stale_minutes) { $flags.watchdog_stale_minutes = [int]$j.watchdog_stale_minutes }
    } catch {
        Write-Log ("WARN: nao li runtime_settings.json: {0}" -f $_.Exception.Message)
    }
    return $flags
}

function Write-Log {
    param([string]$Msg)
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $Msg
    Add-Content -Path $logPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-LastMeasurementAgeMinutes {
    if (-not (Test-Path $psql)) {
        throw "psql nao encontrado em $psql"
    }
    if (-not $env:PGPASSWORD) {
        $envFile = Join-Path $projectRoot ".env"
        if (Test-Path $envFile) {
            $line = Get-Content $envFile | Where-Object { $_ -match '^\s*POSTGRES_PASSWORD\s*=' } | Select-Object -First 1
            if ($line) {
                $env:PGPASSWORD = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
            }
        }
        if (-not $env:PGPASSWORD) { $env:PGPASSWORD = "energy_meter_dev_only" }
    }
    $sql = "SELECT COALESCE(ROUND(EXTRACT(EPOCH FROM (NOW() - MAX(timestamp)))/60.0, 1), 99999) FROM measurements;"
    $out = & $psql -U energy_meter -d energy_meter -h localhost -t -A -c $sql 2>&1
    if ($LASTEXITCODE -ne 0) { throw "psql falhou: $out" }
    return [double](($out | Out-String).Trim())
}

function Start-MeterIfMissing {
    $procs = @(Get-Process -Name "EnergyMeterServer" -ErrorAction SilentlyContinue)
    if ($procs.Count -eq 0) {
        Write-Log "EnergyMeterServer ausente - iniciando..."
        if (-not (Test-Path $exePath)) { throw "EXE nao encontrado: $exePath" }
        Start-Process -FilePath $exePath -WorkingDirectory $projectRoot
        Start-Sleep -Seconds 8
    }
}

function Restart-MeterServer {
    param([string]$Reason)
    Write-Log "REINICIO: $Reason"
    Get-Process -Name "EnergyMeterServer" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    if (Test-Path $lockPath) {
        Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path $exePath)) { throw "EXE nao encontrado: $exePath" }
    Start-Process -FilePath $exePath -WorkingDirectory $projectRoot
    Start-Sleep -Seconds 10
    try {
        $code = (Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5).StatusCode
        Write-Log "API apos reinicio: HTTP $code"
    } catch {
        Write-Log ("API ainda nao respondeu apos reinicio: {0}" -f $_.Exception.Message)
    }
}

# --- main ---
$failed = $false
try {
    $flags = Get-RuntimeFlags
    if (-not $flags.watchdog_enabled) {
        Write-Log "Watchdog DESLIGADO na UI (runtime_settings) - saindo sem acao"
        exit 0
    }
    if (-not $flags.collectors_enabled) {
        Write-Log "Coleta DESLIGADA na UI - watchdog nao reinicia (esperado sem dados novos)"
        exit 0
    }
    $maxStaleMinutes = [Math]::Max(5, [int]$flags.watchdog_stale_minutes)

    Start-MeterIfMissing

    $age = Get-LastMeasurementAgeMinutes
    Write-Log ("Ultima medicao ha {0} min (limite {1})" -f $age, $maxStaleMinutes)

    if ($age -gt $maxStaleMinutes) {
        Restart-MeterServer -Reason ("coleta estagnada ha {0} min (> {1})" -f $age, $maxStaleMinutes)
    } else {
        Write-Log "OK - pollers aparentam ativos"
    }
} catch {
    Write-Log ("ERRO: {0}" -f $_.Exception.Message)
    $failed = $true
}

if ($failed) { exit 1 }
