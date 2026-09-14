# Setup Postgres Nativo — cluster PIENG (escritório)

> Nome histórico do arquivo: `SETUP_POSTGRES_NATIVO_K.md` (antes o data dir era só no K:).

> **Atualizado:** 2026-09-11  
> **Status:** ✅ Banco **único** = Postgres  
> **Data dir vivo:** `F:\storage\postgres\energy_meter\pgdata` (SSD `STORAGE_PRINCIPAL`)  
> **Backup:** `K:\storage\…` (HDD)  
> SQLite local arquivado em `data/app.db.archived_*` (não usar)  
> Registro completo do host: `pieng_postgres/REGISTRO.md`

## Decisão (2026-09-11)

| Caminho | Uso |
|---------|-----|
| **Postgres nativo 17** em **F:** (SSD) | **Único banco** da app (coleta + Dashboard + API) |
| **K:** (HDD) | Backup / cópia fria / dumps |
| **`docker-compose.yml`** | Mantido para o futuro — **não apagar** |
| **SQLite** | **Legado** — arquivo arquivado; flush desligado |

Manter `F:` e o PC ligados 24h (`scripts/setup_remote_server.ps1` / keep-awake do `pieng_postgres`).

## O que está instalado

- **Produto:** PostgreSQL 17.11 (EDB Windows x64)
- **Serviço:** `postgresql-x64-17` (Automatic / Running)
- **Data directory:** `F:\storage\postgres\energy_meter\pgdata`
- **Porta:** `5432`
- **App role/DB:** `energy_meter` / `energy_meter`
- **Host:** `cca-tecnica` / Tailscale `100.104.172.12`

> Senha de teste local. Rotacionar antes de produção.

## Layout

```
F:\storage\                         # PRINCIPAL (SSD)
  postgres\
    energy_meter\pgdata\            # cluster vivo
    energy_meter_docker\
    pieng_saas\
  backups\
  cache\
  dados\

K:\storage\                         # BACKUP (HDD)
  postgres\energy_meter\pgdata\     # cópia fria (não apontar o serviço aqui)
  backups\energy_meter\
```

## `.env` da app

```env
DATABASE_URL=postgresql://energy_meter:energy_meter_dev_only@localhost:5432/energy_meter
```

Outro PC via Tailscale:

```env
DATABASE_URL=postgresql://energy_meter:SENHA@100.104.172.12:5432/energy_meter
```

`data/runtime_settings.json`: `postgres_flush_enabled: false`.

## Migração / cutover (já feito)

1. Flush final SQLite → Postgres (contagens iguais)
2. `DATABASE_URL` apontado para Postgres
3. `app.db` renomeado para `data/app.db.archived_YYYYMMDD`
4. Flush legado vira no-op quando `DATABASE_URL` não é sqlite

Script histórico (idempotente):

```bat
cd /d E:\Projetos\pieng-energy-meter
.\.venv\Scripts\python migrate_sqlite_to_postgres.py "postgresql://energy_meter:energy_meter_dev_only@localhost:5432/energy_meter"
```

## Validar

```bat
set PGPASSWORD=energy_meter_dev_only
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U energy_meter -h localhost -d energy_meter -c "SELECT count(*) FROM measurements;"
```

Painel: http://127.0.0.1:8001/api/db — deve mostrar `hot_path: postgres_k`.

## Política HD

- Disco **principal** = SSD `F:` ligado 24h
- Disco **backup** = HDD `K:` (dumps / cópia fria)
- Sem SQLite paralelo — se `F:` cair, a coleta para
- Remoto: somente Tailscale (`pieng_postgres` → `REGISTRO.md` + `REMOTE_ACCESS.md`)
- Não abrir `5432` no roteador

## Docker (preservado)

Arquivo: `docker-compose.yml`

- Volume Docker (reservado): `F:/storage/postgres/energy_meter_docker` (ou K: backup)
- Porta host: **5433** → 5432 container

## Backup sugerido

```bat
set PGPASSWORD=energy_meter_dev_only
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U energy_meter -h localhost -d energy_meter -F c -f K:\storage\backups\energy_meter\energy_meter_%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%.dump
```

## Relacionado

- `pieng_postgres` — `REMOTE_ACCESS.md`, `scripts/postgres/`, `scripts/host/`
- `CHANGELOG.md`, `.claude/session_context.json`
- `SETUP_FIDELCO.md` — alvo futuro (mini PC / servidor)
