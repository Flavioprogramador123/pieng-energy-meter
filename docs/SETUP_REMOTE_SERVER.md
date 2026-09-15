# Setup servidor remoto (Tailscale + RDP)

Script: `scripts/setup_remote_server.ps1`  
Uso: preparar um PC Windows para ficar acessivel via Tailscale (sem hibernar; so apaga a tela) e com Area de Trabalho Remota (RDP) ativa.

## Na outra maquina (ex.: CCA) — fazer o pull

No PowerShell (pode ser normal):

```powershell
cd C:\Users\flavi\projeto\pieng-energy-meter
git pull origin main
```

Se o repositorio ainda nao existir nessa maquina:

```powershell
cd C:\Users\flavi\projeto
git clone https://github.com/Flavioprogramador123/pieng-energy-meter.git
cd pieng-energy-meter
```

## Rodar o script (Administrador)

PowerShell **como Administrador**, nesta ordem:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
& 'C:\Users\flavi\projeto\pieng-energy-meter\scripts\setup_remote_server.ps1'
```

O script:

1. Desliga sono / hibernacao (AC e bateria)
2. Apaga so o monitor (10 min AC / 5 min bateria)
3. Ativa RDP + firewall (porta 3389)
4. Mostra o IP / nome Tailscale para conectar

## Conectar com nome (MagicDNS)

Ja existe DNS do Tailscale. Exemplos da rede atual:

| Maquina | Nome curto | Nome completo |
|---------|------------|---------------|
| Notebook servidor | `administrator` | `administrator.tail8bc257.ts.net` |
| CCA | `cca-tecnica` | `cca-tecnica.tail8bc257.ts.net` |

No `mstsc` (Conexao de Area de Trabalho Remota):

```text
cca-tecnica
```

ou o IP `100.x` que o script imprimir.

## Se der erro 0x204

- Tailscale Connected nos dois PCs
- Rode este script **na maquina que sera acessada** (destino do RDP)
- Confirme ping: `ping cca-tecnica` ou `ping 100.104.172.12`

## Ponte Meter 24/7 (exe no F: da CCA)

Amanhã: colocar `EnergyMeterServer.exe` em `F:\storage\pieng\` para servir
dashboard/API via Tailscale de qualquer lugar (efeito “Vercel” privado).

Guia completo: [`docs/SETUP_EXE_CCA_F.md`](SETUP_EXE_CCA_F.md)

## Nomes MagicDNS

Painel: https://login.tailscale.com/admin/machines
