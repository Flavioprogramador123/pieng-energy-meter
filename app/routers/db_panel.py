"""Painel do Postgres (banco único no F:) + coleta/watchdog/flush."""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.services import postgres_mirror
from app.services.runtime_settings import (
    get_runtime_settings,
    update_runtime_settings,
    sqlite_cache_status,
)
from app.services.collector_stats import get_collector_stats
from app.core.db import SessionLocal

router = APIRouter(tags=["db-panel"])


class FlushSettingsUpdate(BaseModel):
    postgres_flush_enabled: bool | None = None
    postgres_flush_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    sqlite_cache_max_mb: int | None = Field(default=None, ge=50, le=50000)
    collectors_enabled: bool | None = None
    collectors_interval_seconds: int | None = Field(default=None, ge=30, le=3600)
    watchdog_enabled: bool | None = None
    watchdog_stale_minutes: int | None = Field(default=None, ge=5, le=240)


@router.get("/db", response_class=HTMLResponse)
def db_panel_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        "db_panel.html",
        {"request": request, "active_page": "db"},
    )


def _db_last_and_today():
    """Última medição no banco + pontos gravados hoje (America/Sao_Paulo)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.core.config import settings

    db = SessionLocal()
    try:
        using_sqlite = str(settings.database_url).startswith("sqlite")
        if using_sqlite:
            # SQLite: sem FILTER / AT TIME ZONE — calcula o início do dia em Python
            start = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            # timestamps no SQLite costumam ser naive no fuso local de coleta
            start_naive = start.replace(tzinfo=None)
            row = db.execute(
                text(
                    """
                    SELECT
                      MAX(timestamp) AS last_at,
                      SUM(CASE WHEN timestamp >= :start THEN 1 ELSE 0 END) AS points_today
                    FROM measurements
                    """
                ),
                {"start": start_naive.isoformat(sep=" ")},
            ).mappings().first()
        else:
            row = db.execute(
                text(
                    """
                    SELECT
                      MAX(timestamp) AS last_at,
                      COUNT(*) FILTER (
                        WHERE timestamp >= (
                          (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')::date
                          AT TIME ZONE 'America/Sao_Paulo'
                        )
                      ) AS points_today
                    FROM measurements
                    """
                )
            ).mappings().first()
        last_at = row["last_at"] if row else None
        if last_at is not None and hasattr(last_at, "isoformat"):
            last_iso = last_at.isoformat()
        elif last_at is not None:
            last_iso = str(last_at)
        else:
            last_iso = None
        return {
            "last_measurement_at": last_iso,
            "db_points_today": int(row["points_today"] or 0) if row else 0,
        }
    except Exception as e:
        return {"last_measurement_at": None, "db_points_today": 0, "error": str(e).splitlines()[0]}
    finally:
        db.close()


@router.get("/db/status")
def db_status(request: Request):
    from app.core.config import settings

    using_sqlite = str(settings.database_url).startswith("sqlite")
    mirror = postgres_mirror.probe_mirror()
    sqlite = {}
    if using_sqlite:
        try:
            sqlite = postgres_mirror.sqlite_counts()
        except Exception as e:
            sqlite = {"error": str(e).splitlines()[0]}
    else:
        sqlite = {"archived": True, "note": "SQLite nao e mais o hot path (arquivo em data/app.db.archived_*)"}
    runtime = get_runtime_settings()
    live = _db_last_and_today()
    stats = get_collector_stats()
    return {
        "is_scheduler_owner": getattr(request.app.state, "is_scheduler_owner", None),
        "scheduler_owner_note": (
            "Esta instância é dona dos pollers (coleta → Postgres no F:)."
            if getattr(request.app.state, "is_scheduler_owner", False)
            else "Esta instância NÃO coleta — outro processo já é o dono "
                 "(data/.scheduler.lock). Serve API/Dashboard no mesmo Postgres."
        ),
        "hot_path": "sqlite" if using_sqlite else "postgres_f",
        "hot_explanation": (
            "A coleta e o Dashboard usam o SQLite no NVMe; Postgres é espelho (legado)."
            if using_sqlite
            else "Banco único: PostgreSQL no SSD F: (F:\\storage\\postgres\\energy_meter\\pgdata). "
                 "Máquina de TESTE — use os controles de Coleta/Watchdog abaixo."
        ),
        "mirror": mirror,
        "sqlite_counts": sqlite,
        "sqlite_cache": sqlite_cache_status(),
        "collectors": {
            "enabled": bool(runtime.get("collectors_enabled", True)),
            "interval_seconds": int(runtime.get("collectors_interval_seconds") or 180),
            "watchdog_enabled": bool(runtime.get("watchdog_enabled", True)),
            "watchdog_stale_minutes": int(runtime.get("watchdog_stale_minutes") or 12),
            "stats": stats,
            **live,
        },
        "flush": {
            **runtime,
            "last": postgres_mirror.get_last_flush_status(),
        },
    }


@router.get("/db/collector-live")
def collector_live():
    """Leve: última coleta + contadores do dia (para o badge do dashboard)."""
    rt = get_runtime_settings()
    stats = get_collector_stats()
    live = _db_last_and_today()
    last = stats.get("last_success_at") or live.get("last_measurement_at")
    return {
        "collectors_enabled": bool(rt.get("collectors_enabled", True)),
        "interval_seconds": int(rt.get("collectors_interval_seconds") or 180),
        "last_collection_at": last,
        "poll_cycles_today": int(stats.get("poll_cycles_today") or 0),
        "points_today": int(live.get("db_points_today") or stats.get("points_today") or 0),
        "day": stats.get("day"),
        "timezone": "America/Sao_Paulo",
    }


@router.get("/db/tables/{table}")
def db_table_rows(table: str, limit: int = 50, offset: int = 0):
    try:
        return postgres_mirror.list_table_rows(table, limit=min(limit, 200), offset=max(offset, 0))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e).splitlines()[0])


@router.get("/db/settings")
def get_settings():
    return get_runtime_settings()


@router.patch("/db/settings")
def patch_settings(body: FlushSettingsUpdate, request: Request):
    data = update_runtime_settings(
        postgres_flush_enabled=body.postgres_flush_enabled,
        postgres_flush_interval_minutes=body.postgres_flush_interval_minutes,
        sqlite_cache_max_mb=body.sqlite_cache_max_mb,
        collectors_enabled=body.collectors_enabled,
        collectors_interval_seconds=body.collectors_interval_seconds,
        watchdog_enabled=body.watchdog_enabled,
        watchdog_stale_minutes=body.watchdog_stale_minutes,
    )
    reschedule = getattr(request.app.state, "reschedule_postgres_flush", None)
    if callable(reschedule):
        reschedule()
    reschedule_c = getattr(request.app.state, "reschedule_collectors", None)
    if callable(reschedule_c):
        reschedule_c()
    return {"ok": True, "settings": data}


@router.post("/db/flush")
def run_flush_now():
    return postgres_mirror.flush_sqlite_to_postgres()
