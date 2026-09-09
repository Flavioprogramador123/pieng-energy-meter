from fastapi import APIRouter
from .clients import router as clients_router
from .devices import router as devices_router
from .ingest import router as ingest_router
from .metrics import router as metrics_router
from .alarms import router as alarms_router
from .dashboard import router as dashboard_router
from .db_panel import router as db_panel_router
from ..core.config import settings

try:
    from .storage import router as storage_router
except Exception as exc:  # storage depende de libs opcionais
    storage_router = None
    print(f"Storage router desabilitado: {exc}")


def get_api_router() -> APIRouter:
    api = APIRouter()
    api.include_router(clients_router)
    api.include_router(devices_router)
    api.include_router(ingest_router)
    api.include_router(metrics_router)
    api.include_router(alarms_router)
    api.include_router(dashboard_router)
    api.include_router(db_panel_router)
    if storage_router is not None:
        api.include_router(storage_router)
    return api

