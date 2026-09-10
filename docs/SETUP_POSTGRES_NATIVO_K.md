# Setup Postgres Nativo no HD K:\STORAGE (escritório)

> **Data:** 2026-09-09  
> **Status:** ✅ Instalado e migrado (teste)  
> **Hot path da app:** continua SQLite (`data/app.db`) — coletor uvicorn **não** foi cortado

## Decisão

Enquanto o mini PC / Fidelco não está pronto e Docker Desktop **não** está instalado nesta máquina:

| Caminho | Uso |
|---------|-----|
| **Postgres nativo 17** (serviço Windows) | Teste no escritório, dados no HD `K:` |
| **`docker-compose.yml`** | Mantido para o futuro (mini PC / Docker) — **não apagar** |
| **SQLite** | Coleta ao vivo (hot cache no NVMe) |

## O que foi instalado

- **Produto:** PostgreSQL 17.11 (EDB Windows x64)
- **Serviço:** `postgresql-x64-17` (Automatic / Running)
- **Data directory:** `K:\storage\postgres\energy_meter\pgdata`
- **Porta:** `5432` (localhost)
- **Superuser:** `postgres` / senha de teste `energy_meter_dev_only`
- **App role/DB:** `energy_meter` / `energy_meter` / mesma senha de teste

> Senha é só para ambiente de teste local. Trocar antes de qualquer exposição na rede.

## Layout no K:

```
K:\storage\
  postgres\
    energy_meter\pgdata\     ← Postgres NATIVO (em uso)
    energy_meter_docker\     ← reservado ao Docker (compose, porta 5433)
    pieng_saas\              ← futuro portal pieng_postgres
  backups\energy_meter\
  cache\                     ← buffer opcional (hot = SQLite no NVMe; teto 200 MB)
  dados\
```

## Migração executada (dados REAIS)

```bat
cd /d E:\Projetos\pieng-energy-meter
.\.venv\Scripts\pip install "psycopg2-binary>=2.9.12"
.\.venv\Scripts\python migrate_sqlite_to_postgres.py "postgresql://energy_meter:energy_meter_dev_only@localhost:5432/energy_meter"
```

Resultado em 2026-09-09:

| Tabela | Registros |
|--------|-----------|
| clients | 4 |
| devices | 1 (`medidorCASA`, id=5, tuya, active) |
| measurements | 2641 |
| alarm_rules | 0 |
| alarm_events | 0 |

Reexecutável (idempotente via `merge`).

## Validar

```bat
set PGPASSWORD=energy_meter_dev_only
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U energy_meter -h localhost -d energy_meter -c "SELECT count(*) FROM measurements;"
```

## Painel Banco / Storage (UI)

URL (sessão atual): http://127.0.0.1:8001/api/db  
(Alternativa: `:8000` se esse for o processo vivo.)

- Status do Postgres no `K:`, contagens SQLite × Postgres, preview de tabelas
- **Flush automático**: ligado/desligado + intervalo em minutos
- **Teto do cache SQLite** (MB) + uso atual; alerta visual se passar do teto
- Hot path continua SQLite; flush só espelha para o HD

Arquivos: `app/routers/db_panel.py`, `app/services/postgres_mirror.py`, `app/services/runtime_settings.py`, `data/runtime_settings.json`

### Valores de teste (escritório, 2026-09-09)

| Parâmetro | Valor | Motivo |
|-----------|-------|--------|
| `postgres_flush_interval_minutes` | **30** | Menos I/O no HD USB; máquina não dedicada |
| `sqlite_cache_max_mb` | **200** | ~3 dias com ~3 aparelhos (~15 MB/dia/device trifásico) |

Alterar pela UI → salva em `data/runtime_settings.json` e reescalona o job `postgres_flush` sem editar `.env`.

## O que NÃO é “trocar DATABASE_URL”

`DATABASE_URL` define de onde a **app inteira** lê/grava (Dashboard, pollers, API).

| Situação | O que acontece |
|----------|----------------|
| Hoje (correto) | App usa **SQLite**. Flush copia para Postgres no K: de tempos em tempos. |
| Se trocar DATABASE_URL p/ Postgres | App passa a depender do HD USB a cada 30s. Mais risco se o USB oscilar. |

Por isso o passo “trocar DATABASE_URL” ficou para depois da validação — **não é necessário** para o espelho funcionar.

## Política HD + cache (combinado com o usuário)

- HD mecânico USB: melhor **ficar ligado** do que ciclar spin-up/spin-down
- Hot = SQLite no NVMe (poll ~30s); teto de teste **200 MB**
- Espelho no `K:` = Postgres; flush a cada **30 min** (teste)
- Se `K:` cair: dados continuam no SQLite até o flush voltar a funcionar
- Não desligar o HD só para “economizar” entre flushes

## Docker (preservado)

Arquivo: `docker-compose.yml`

- Volume: `K:/storage/postgres/energy_meter_docker`
- Porta host: **5433** → 5432 container (para não brigar com o nativo na 5432)
- Quando Docker existir: `docker compose up -d` e migrar de novo se necessário

## Backup sugerido

```bat
set PGPASSWORD=energy_meter_dev_only
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U energy_meter -h localhost -d energy_meter -F c -f K:\storage\backups\energy_meter\energy_meter_%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%.dump
```

## Acesso remoto (Tailscale)

O dono da política do cluster é o repo **`pieng_postgres`** (`REMOTE_ACCESS.md`).

| Item | Valor (2026-09-10) |
|------|---------------------|
| Servidor | `cca-tecnica` — Tailscale **100.104.172.12** (cluster ativo) |
| Segundo ADMINISTRADOR | `administrator` — **100.126.2.58** (acesso depois; teste remoto adiado) |
| `pg_hba` | localhost + `100.64.0.0/10` |
| Firewall | `PIENG-PostgreSQL-Tailscale-5432` |
| DBs | `energy_meter`, `pieng_saas` |

Os dois hosts Tailscale são classe **ADMINISTRADOR**. Validação `psql` a partir do
segundo fica para quando houver acesso físico/remoto a ele.

Neste PC o espelho do Energy Meter usa `localhost`. Em outra máquina:

```env
POSTGRES_MIRROR_URL=postgresql://energy_meter:SENHA@100.104.172.12:5432/energy_meter
```

Não abrir `5432` no roteador. Não trocar o hot path SQLite sem validação.

## Relacionado

- `CHANGELOG.md` — relato da sessão
- `.claude/session_context.json` — estado estruturado
- `SETUP_FIDELCO.md` — alvo futuro (mini PC / servidor)
- Projeto `pieng_postgres` — dono do cluster central (`REMOTE_ACCESS.md`, `scripts/postgres/`)
