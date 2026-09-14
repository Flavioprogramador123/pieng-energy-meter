# Registra o Energy Meter (EnergyMeterServer.exe) + watchdog dos pollers
# como Tarefas Agendadas do Windows (SYSTEM, desde o boot).
#
# Camadas de resiliencia:
#   1) PIENG-EnergyMeter-Server  — sobe o .exe no boot; reinicia se o processo CAIR
#   2) PIENG-EnergyMeter-Watchdog — a cada 5 min checa se ha medicacao recente;
#      se a coleta estiver "travada" (processo vivo sem dados novos), mata e sobe de novo
#
# Uso (PowerShell como Administrador):
#   .\scripts\register_service.ps1
#
# Depois de qualquer novo build (pyinstaller energy_meter.spec), rode de novo
# este script (o caminho do .exe nao muda).

$ErrorActionPreference = "Stop"

$taskName     = "PIENG-EnergyMeter-Server"
$watchdogName = "PIENG-EnergyMeter-Watchdog"
$projectRoot  = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$exePath      = Join-Path $projectRoot "dist\EnergyMeterServer\EnergyMeterServer.exe"
$watchdogPath = Join-Path $PSScriptRoot "watchdog_collectors.ps1"

if (-not (Test-Path $exePath)) {
    throw "Nao encontrei $exePath - rode antes: .venv\Scripts\pyinstaller.exe energy_meter.spec"
}
if (-not (Test-Path $watchdogPath)) {
    throw "Nao encontrei $watchdogPath"
}

foreach ($name in @($taskName, $watchdogName)) {
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
        Write-Host "Removendo tarefa existente '$name'..."
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
    }
}

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# --- 1) Servidor (boot + restart se processo sair) ---
$action = New-ScheduledTaskAction -Execute $exePath -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Energy Meter (FastAPI + pollers Modbus/Tuya a cada 3 min)." | Out-Null

# --- 2) Watchdog (a cada 5 min) — pega o caso "vivo mas travado" ---
$wdAction = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogPath`"" `
    -WorkingDirectory $projectRoot
# Trigger a cada 5 min. Duration ~10 anos (Task Scheduler nao aceita TimeSpan.MaxValue).
$wdTrigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$wdSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $watchdogName -Action $wdAction -Trigger $wdTrigger `
    -Settings $wdSettings -Principal $principal `
    -Description "Watchdog: reinicia Energy Meter se a coleta ficar >12 min sem dados novos." | Out-Null

Write-Host "Tarefas registradas. Iniciando servidor e 1a checagem do watchdog..."
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 5
Start-ScheduledTask -TaskName $watchdogName
Start-Sleep -Seconds 3
Get-ScheduledTask -TaskName $taskName, $watchdogName | Select-Object TaskName, State
