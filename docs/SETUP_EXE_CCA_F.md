# Ponte Energy Meter na CCA (exe no F:) — “tipo Vercel” via Tailscale

**Para amanhã na `cca-tecnica`.**  
Objetivo: o Meter roda 24/7 **nessa máquina**, com o `.exe` no SSD **F:**, falando com o Postgres oficial no **F:**. De qualquer lugar (outro PC / celular) você só precisa do **Tailscale** e abre o browser.

```text
Celular / notebook (qualquer lugar)
        │  Tailscale
        ▼
cca-tecnica  EnergyMeterServer.exe  (:8001)
        │  localhost
        ▼
Postgres  F:\storage\postgres\energy_meter\pgdata
```

Isso **não é Vercel na internet pública** (sem abrir porta no roteador). É o mesmo efeito prático na sua rede privada Tailscale: URL fixa, servidor sempre ligado.

## Pré-requisitos na CCA

1. PC ligado 24/7, sem hibernar (`scripts/setup_remote_server.ps1`)
2. Tailscale Connected
3. Postgres oficial no F: (serviço `postgresql-x64-17` rodando)
4. Repo atualizado: `git pull origin main`

## Pasta sugerida no F:

```text
F:\storage\pieng\EnergyMeterServer\
  EnergyMeterServer.exe   (+ pasta _internal / arquivos do dist)
  .env                    ← DATABASE_URL=localhost (mesmo PC!)
  data\                   ← runtime_settings, collector_stats, logs
```

## Passo a passo (amanhã)

### 1) Build do .exe (na CCA ou neste notebook)

```powershell
cd C:\Users\flavi\projeto\pieng-energy-meter
git pull origin main
.\.venv\Scripts\activate
pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe energy_meter.spec
```

Saída: `dist\EnergyMeterServer\` (pasta completa — copiar **tudo**).

### 2) Copiar para o F:

```powershell
New-Item -ItemType Directory -Force -Path 'F:\storage\pieng\EnergyMeterServer'
Copy-Item -Recurse -Force '.\dist\EnergyMeterServer\*' 'F:\storage\pieng\EnergyMeterServer\'
```

### 3) `.env` ao lado do exe (importante)

No `F:\storage\pieng\EnergyMeterServer\.env` (ou working directory que o serviço usar):

```env
DATABASE_URL=postgresql://energy_meter:energy_meter_dev_only@127.0.0.1:5432/energy_meter
POSTGRES_USER=energy_meter
POSTGRES_PASSWORD=energy_meter_dev_only
POSTGRES_DB=energy_meter
TUYA_ACCESS_ID=...
TUYA_ACCESS_SECRET=...
TUYA_API_REGION=us
APP_NAME=Energy Meter Master
API_PREFIX=/api
```

Na CCA use **`127.0.0.1`**, não o IP Tailscale — o banco está na mesma máquina (F:).

`data\runtime_settings.json` (criar se não existir):

```json
{
  "postgres_flush_enabled": false,
  "collectors_enabled": true,
  "collectors_interval_seconds": 180,
  "watchdog_enabled": true,
  "watchdog_stale_minutes": 12
}
```

### 4) Registrar no boot (Admin)

Hoje o `scripts\register_service.ps1` aponta para `dist\` no repo. Opções:

**A)** Ajustar o script para `$exePath = 'F:\storage\pieng\EnergyMeterServer\EnergyMeterServer.exe'` e WorkingDirectory = essa pasta, **ou**

**B)** Rodar o exe uma vez manual para testar:

```powershell
cd F:\storage\pieng\EnergyMeterServer
.\EnergyMeterServer.exe
```

Depois registrar tarefa agendada / serviço apontando para esse caminho (mesmo espírito do `register_service.ps1`).

### 5) Acessar de qualquer lugar

Com Tailscale ligado no cliente:

| Página | URL |
|--------|-----|
| Dashboard | http://cca-tecnica:8001/api/dashboard |
| HOME | http://cca-tecnica:8001/home |
| DB panel | http://cca-tecnica:8001/api/db |
| Docs API | http://cca-tecnica:8001/docs |

IP: `http://100.104.172.12:8001/...`

## Papel de cada máquina

| Máquina | Função |
|---------|--------|
| **cca-tecnica + F:** | Servidor oficial (exe + Postgres) — a “ponte” |
| Notebook / celular | Só cliente (browser + Tailscale) |
| Mini PC no cliente (futuro) | Edge de coleta local → API na CCA |

## Checklist rápido amanhã

- [ ] `git pull` na CCA  
- [ ] Build ou copiar `dist\EnergyMeterServer` → `F:\storage\pieng\...`  
- [ ] `.env` com `DATABASE_URL=...@127.0.0.1:5432/...`  
- [ ] Testar `.\EnergyMeterServer.exe` (dashboard abre em `:8001`)  
- [ ] Registrar tarefa no boot + watchdog  
- [ ] Do celular: Tailscale → `http://cca-tecnica:8001/api/dashboard`  

## Relacionado

- `energy_meter.spec` / `run_server.py` — build PyInstaller  
- `scripts/register_service.ps1` — boot + restart  
- `scripts/watchdog_collectors.ps1` — reinicia se coleta travar  
- `docs/SETUP_POSTGRES_NATIVO_K.md` — Postgres F: oficial  
- `docs/SETUP_REMOTE_SERVER.md` — RDP / keep-awake
