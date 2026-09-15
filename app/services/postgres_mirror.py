"""Postgres (banco único no F:) — status, leitura de tabelas e flush legado.

Desde 2026-09-11 a app usa Postgres (DATABASE_URL) como banco único.
Data dir vivo: F:\\storage\\postgres\\energy_meter\\pgdata (K: = backup).
O flush SQLite→Postgres só roda se DATABASE_URL ainda for sqlite (legado).
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.db import Base, SessionLocal
from app import models

TABLE_ORDER = [
    models.Client,
    models.Device,
    models.Measurement,
    models.AlarmRuleModel,
    models.AlarmEvent,
]

_STATUS_LOCK = threading.Lock()
_LAST_STATUS: dict[str, Any] = {
    "ok": None,
    "last_run_at": None,
    "last_error": None,
    "copied": {},
    "duration_ms": None,
}


def mirror_url() -> str:
    """URL do Postgres (localhost). Override via POSTGRES_MIRROR_URL no .env."""
    if getattr(settings, "postgres_mirror_url", None):
        return settings.postgres_mirror_url  # type: ignore[return-value]
    user = settings.postgres_user or "energy_meter"
    password = settings.postgres_password or "energy_meter_dev_only"
    db = settings.postgres_db or "energy_meter"
    return f"postgresql://{user}:{password}@localhost:5432/{db}"


def get_mirror_engine():
    return create_engine(mirror_url(), pool_pre_ping=True)


def get_last_flush_status() -> dict[str, Any]:
    with _STATUS_LOCK:
        return dict(_LAST_STATUS)


def _set_status(**kwargs: Any) -> None:
    with _STATUS_LOCK:
        _LAST_STATUS.update(kwargs)


def probe_mirror() -> dict[str, Any]:
    """Testa conexão e devolve contagens das tabelas no Postgres."""
    url = mirror_url()
    safe = url.split("@")[-1] if "@" in url else url
    try:
        engine = get_mirror_engine()
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
            data_dir = None
            try:
                data_dir = conn.execute(text("SHOW data_directory")).scalar()
            except Exception:
                conn.rollback()
                data_dir = "(sem permissao para ler data_directory)"
            counts = {}
            for model in TABLE_ORDER:
                try:
                    counts[model.__tablename__] = conn.execute(
                        text(f"SELECT count(*) FROM {model.__tablename__}")
                    ).scalar()
                except Exception:
                    counts[model.__tablename__] = None
        return {
            "ok": True,
            "url_host": safe,
            "version": str(version).split("\n")[0] if version else None,
            "data_directory": data_dir,
            "counts": counts,
            "error": None,
        }
    except Exception as e:
        return {
            "ok": False,
            "url_host": safe,
            "version": None,
            "data_directory": None,
            "counts": {},
            "error": str(e).splitlines()[0],
        }


def sqlite_counts() -> dict[str, int]:
    db = SessionLocal()
    try:
        out: dict[str, int] = {}
        for model in TABLE_ORDER:
            out[model.__tablename__] = db.query(model).count()
        return out
    finally:
        db.close()


def list_table_rows(table: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    allowed = {m.__tablename__: m for m in TABLE_ORDER}
    if table not in allowed:
        raise ValueError(f"Tabela inválida: {table}")
    model = allowed[table]
    engine = get_mirror_engine()
    MirrorSession = sessionmaker(bind=engine)
    db = MirrorSession()
    try:
        total = db.query(model).count()
        # order by id desc when available
        q = db.query(model)
        if hasattr(model, "id"):
            q = q.order_by(model.id.desc())
        rows = q.offset(offset).limit(limit).all()
        cols = [c.key for c in inspect(model).mapper.column_attrs]
        data = []
        for row in rows:
            item = {}
            for c in cols:
                val = getattr(row, c)
                if isinstance(val, datetime):
                    item[c] = val.isoformat()
                else:
                    item[c] = val
            data.append(item)
        return {"table": table, "total": total, "limit": limit, "offset": offset, "columns": cols, "rows": data}
    finally:
        db.close()


def flush_sqlite_to_postgres() -> dict[str, Any]:
    """Copia incrementalmente do SQLite para o Postgres (legado).

    No-op se DATABASE_URL já for Postgres (banco único no F:).
    """
    started = datetime.now(timezone.utc)
    copied: dict[str, int] = {}
    if not str(settings.database_url).startswith("sqlite"):
        result = {
            "ok": True,
            "last_run_at": started.isoformat(),
            "last_error": None,
            "copied": {},
            "duration_ms": 0,
            "skipped": "DATABASE_URL ja e Postgres (banco unico no F:) — flush desnecessario",
        }
        _set_status(**result)
        print(f"[postgres_mirror] {result['skipped']}")
        return result
    try:
        postgres_engine = get_mirror_engine()
        Base.metadata.create_all(bind=postgres_engine)

        SqliteSession = SessionLocal
        PostgresSession = sessionmaker(bind=postgres_engine)
        sqlite_db = SqliteSession()
        postgres_db = PostgresSession()
        try:
            for model in TABLE_ORDER:
                table = model.__tablename__
                n = 0

                # Clients/Devices: upsert por id (mesmo se já existir no espelho)
                if model in (models.Client, models.Device, models.AlarmRuleModel, models.AlarmEvent):
                    max_pg = postgres_db.query(model.id).order_by(model.id.desc()).limit(1).scalar()
                    q = sqlite_db.query(model).order_by(model.id)
                    if max_pg is not None and model not in (models.Client, models.Device):
                        q = q.filter(model.id > max_pg)
                    rows = q.all() if model not in (models.Client, models.Device) else sqlite_db.query(model).order_by(model.id).all()
                    for row in rows:
                        data = {c.key: getattr(row, c.key) for c in inspect(model).mapper.column_attrs}
                        try:
                            with postgres_db.begin_nested():
                                postgres_db.merge(model(**data))
                            n += 1
                        except Exception:
                            continue
                    postgres_db.commit()
                    copied[table] = n
                    continue

                # Measurements: NÃO usar id (sequências divergem entre PCs).
                # Sobe por timestamp + chave natural (device_id, metric, timestamp).
                if model is models.Measurement:
                    from sqlalchemy import func

                    max_ts = postgres_db.query(func.max(models.Measurement.timestamp)).scalar()
                    q = sqlite_db.query(models.Measurement).order_by(models.Measurement.timestamp)
                    if max_ts is not None:
                        q = q.filter(models.Measurement.timestamp >= max_ts)
                    rows = q.all()
                    existing: set[tuple] = set()
                    if rows and max_ts is not None:
                        # carrega chaves já no espelho nesta janela (1 query, evita N+1)
                        end_ts = max(r.timestamp for r in rows)
                        for d_id, metric, ts in (
                            postgres_db.query(
                                models.Measurement.device_id,
                                models.Measurement.metric,
                                models.Measurement.timestamp,
                            )
                            .filter(
                                models.Measurement.timestamp >= max_ts,
                                models.Measurement.timestamp <= end_ts,
                            )
                            .all()
                        ):
                            existing.add((d_id, metric, ts))
                    for row in rows:
                        key = (row.device_id, row.metric, row.timestamp)
                        if key in existing:
                            continue
                        data = {
                            c.key: getattr(row, c.key)
                            for c in inspect(models.Measurement).mapper.column_attrs
                            if c.key != "id"
                        }
                        try:
                            with postgres_db.begin_nested():
                                postgres_db.add(models.Measurement(**data))
                            existing.add(key)
                            n += 1
                        except Exception:
                            continue
                    postgres_db.commit()
                    copied[table] = n
                    continue

                postgres_db.commit()
                copied[table] = n

            # sequences
            for model in TABLE_ORDER:
                table = model.__tablename__
                with postgres_engine.begin() as conn:
                    conn.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
                        f"(SELECT MAX(id) IS NOT NULL FROM {table}))"
                    ))
        finally:
            sqlite_db.close()
            postgres_db.close()

        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        result = {
            "ok": True,
            "last_run_at": started.isoformat(),
            "last_error": None,
            "copied": copied,
            "duration_ms": elapsed,
        }
        _set_status(**result)
        print(f"[postgres_mirror] flush OK copied={copied} {elapsed}ms")
        return result
    except Exception as e:
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        result = {
            "ok": False,
            "last_run_at": started.isoformat(),
            "last_error": str(e).splitlines()[0],
            "copied": copied,
            "duration_ms": elapsed,
        }
        _set_status(**result)
        print(f"[postgres_mirror] flush FALHOU: {result['last_error']}")
        return result
