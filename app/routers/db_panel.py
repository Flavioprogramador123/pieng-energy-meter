"""Painel do espelho Postgres (HD K:) + configurações de flush."""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.services import postgres_mirror
from app.services.runtime_settings import (
    get_runtime_settings,
    update_runtime_settings,
    sqlite_cache_status,
)

router = APIRouter(tags=["db-panel"])


class FlushSettingsUpdate(BaseModel):
    postgres_flush_enabled: bool | None = None
    postgres_flush_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    sqlite_cache_max_mb: int | None = Field(default=None, ge=50, le=50000)


@router.get("/db", response_class=HTMLResponse)
def db_panel_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        "db_panel.html",
        {"request": request, "active_page": "db"},
    )


@router.get("/db/status")
def db_status(request: Request):
    mirror = postgres_mirror.probe_mirror()
    sqlite = {}
    try:
        sqlite = postgres_mirror.sqlite_counts()
    except Exception as e:
        sqlite = {"error": str(e).splitlines()[0]}
    runtime = get_runtime_settings()
    return {
        "is_scheduler_owner": getattr(request.app.state, "is_scheduler_owner", None),
        "scheduler_owner_note": (
            "Esta instância é dona dos pollers/flush (coleta hardware + escreve no K:)."
            if getattr(request.app.state, "is_scheduler_owner", False)
            else "Esta instância NÃO coleta nem faz flush — outro processo já é o dono "
                 "(data/.scheduler.lock). Serve API/Dashboard lendo o mesmo SQLite."
        ),
        "hot_path": "sqlite",
        "hot_explanation": (
            "A coleta e o Dashboard usam o SQLite no NVMe (rápido). "
            "O Postgres no HD K: é um ESPELHO — cópia periódica (flush). "
            "Trocar DATABASE_URL faria a app falar só com o Postgres; "
            "isso ainda NÃO foi feito de propósito."
        ),
        "mirror": mirror,
        "sqlite_counts": sqlite,
        "sqlite_cache": sqlite_cache_status(),
        "flush": {
            **runtime,
            "last": postgres_mirror.get_last_flush_status(),
        },
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
    )
    # reescalona o job se o app expôs o helper
    reschedule = getattr(request.app.state, "reschedule_postgres_flush", None)
    if callable(reschedule):
        reschedule()
    return {"ok": True, "settings": data}


@router.post("/db/flush")
def run_flush_now():
    return postgres_mirror.flush_sqlite_to_postgres()
