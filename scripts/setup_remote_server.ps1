#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Prepara este PC como servidor temporario acessivel via Tailscale + RDP.

.DESCRIPTION
  - Nunca suspende / hiberna (AC e bateria)
  - Desliga apenas o monitor (padrao: 10 min AC / 5 min bateria)
  - Ativa Area de Trabalho Remota (RDP) + regra de firewall
  - Mostra IP Tailscale e nome do PC para conectar da outra maquina

.EXAMPLE
  No PowerShell (Admin), com path completa (nesta ordem):
    Set-ExecutionPolicy -Scope Process Bypass -Force
    & 'C:\Users\flavi\projeto\pieng-energy-meter\scripts\setup_remote_server.ps1'
#>

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Msg)
    Write-Host ''
    Write-Host "==> $Msg" -ForegroundColor Cyan
}

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host 'ERRO: execute este script como Administrador.' -ForegroundColor Red
    Write-Host "Use: & 'C:\Users\flavi\projeto\pieng-energy-meter\scripts\setup_remote_server.ps1'" -ForegroundColor Yellow
    exit 1
}

Write-Host 'PIENG - setup servidor remoto (energia + RDP + Tailscale)' -ForegroundColor Green
Write-Host ("PC: {0} | Usuario: {1}" -f $env:COMPUTERNAME, $env:USERNAME)

# --- Energia ---
Write-Step -Msg 'Configurando energia (sem sono/hibernacao, so apaga tela)'

$highPerf = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
powercfg /SETACTIVE $highPerf 2>$null

powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-ac 0
powercfg /change hibernate-timeout-dc 0
powercfg /change monitor-timeout-ac 10
powercfg /change monitor-timeout-dc 5

powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP HYBRIDSLEEP 0
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP HYBRIDSLEEP 0
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1

# Adaptador wireless: desempenho maximo (evita economia que corta VPN)
powercfg /SETACVALUEINDEX SCHEME_CURRENT 19cbb8fa-5279-450e-9fac-8a3d5edaa50b 12bbebe6-58d6-4636-95bb-3217ef867c1a 0 2>$null
powercfg /SETDCVALUEINDEX SCHEME_CURRENT 19cbb8fa-5279-450e-9fac-8a3d5edaa50b 12bbebe6-58d6-4636-95bb-3217ef867c1a 0 2>$null

powercfg /hibernate off 2>$null
powercfg /SETACTIVE SCHEME_CURRENT

Write-Host '  Sono AC/DC: Nunca' -ForegroundColor Green
Write-Host '  Monitor AC: 10 min | DC: 5 min' -ForegroundColor Green

# --- RDP ---
Write-Step -Msg 'Ativando Area de Trabalho Remota'

Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name 'fDenyTSConnections' -Value 0
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name 'UserAuthentication' -Value 1

Enable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue

$rdpRule = Get-NetFirewallRule -DisplayName 'PIENG-RDP-3389' -ErrorAction SilentlyContinue
if (-not $rdpRule) {
    New-NetFirewallRule -DisplayName 'PIENG-RDP-3389' -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null
}

$deny = (Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server').fDenyTSConnections
if ($deny -eq 0) {
    Write-Host '  RDP: ATIVO' -ForegroundColor Green
} else {
    Write-Host ("  RDP: FALHOU (fDenyTSConnections={0})" -f $deny) -ForegroundColor Red
}

# --- Tailscale ---
Write-Step -Msg 'IP Tailscale (conectar da outra maquina)'

$tsIp = $null
if (Get-Command tailscale -ErrorAction SilentlyContinue) {
    $raw = tailscale ip -4 2>$null | Select-Object -First 1
    if ($raw) { $tsIp = $raw.ToString().Trim() }
}
if (-not $tsIp) {
    $tsIp = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -like '100.*' } |
        Select-Object -First 1 -ExpandProperty IPAddress
}

if ($tsIp) {
    Write-Host ("  Tailscale IP: {0}" -f $tsIp) -ForegroundColor Green
} else {
    Write-Host '  Tailscale nao encontrado / desconectado. Abra o app e conecte.' -ForegroundColor Yellow
    $tsIp = '(conectar Tailscale e anotar o IP 100.x)'
}

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ' PRONTO - da outra maquina (mstsc):' -ForegroundColor Cyan
Write-Host ("   Computador: {0}" -f $tsIp) -ForegroundColor White
Write-Host ("   Usuario:    {0}\{1}" -f $env:USERDOMAIN, $env:USERNAME) -ForegroundColor White
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Lembretes:' -ForegroundColor Yellow
Write-Host '  - Deixe este PC ligado na tomada (sem hibernar).'
Write-Host '  - Tailscale Connected nos dois lados.'
Write-Host '  - Energy Meter (uvicorn) precisa estar rodando se for usar o dashboard.'
Write-Host ''
Write-Host 'Pressione Enter para fechar...'
Read-Host | Out-Null
