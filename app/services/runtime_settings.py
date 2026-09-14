"""Configurações runtime persistidas em data/runtime_settings.json.

Permite alterar flush, coleta (pollers) e watchdog pela UI sem editar .env.
Jobs são reescalonados em quente quando possível.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_PATH = Path("data/runtime_settings.json")

_DEFAULTS: dict[str, Any] = {
    "postgres_flush_enabled": False,
    "postgres_flush_interval_minutes": 30,
    "sqlite_cache_max_mb": 200,
    # Coleta (pollers Modbus/Tuya) — máquina de teste: pode desligar pela UI
    "collectors_enabled": True,
    "collectors_interval_seconds": 180,
    # Watchdog externo (scripts/watchdog_collectors.ps1) lê este flag
    "watchdog_enabled": True,
    "watchdog_stale_minutes": 12,
}


def _ensure() -> dict[str, Any]:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _PATH.exists():
        _PATH.write_text(json.dumps(_DEFAULTS, indent=2), encoding="utf-8")
        return dict(_DEFAULTS)
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(_DEFAULTS)
        merged = dict(_DEFAULTS)
        merged.update({k: data[k] for k in _DEFAULTS if k in data})
        # preserva chaves extras antigas sem apagar
        for k, v in data.items():
            if k not in merged:
                merged[k] = v
        return merged
    except Exception:
        return dict(_DEFAULTS)


def get_runtime_settings() -> dict[str, Any]:
    with _LOCK:
        return _ensure()


def update_runtime_settings(**kwargs: Any) -> dict[str, Any]:
    with _LOCK:
        data = _ensure()
        if "postgres_flush_enabled" in kwargs and kwargs["postgres_flush_enabled"] is not None:
            data["postgres_flush_enabled"] = bool(kwargs["postgres_flush_enabled"])
        if "postgres_flush_interval_minutes" in kwargs and kwargs["postgres_flush_interval_minutes"] is not None:
            minutes = int(kwargs["postgres_flush_interval_minutes"])
            data["postgres_flush_interval_minutes"] = max(1, min(24 * 60, minutes))
        if "sqlite_cache_max_mb" in kwargs and kwargs["sqlite_cache_max_mb"] is not None:
            mb = int(kwargs["sqlite_cache_max_mb"])
            data["sqlite_cache_max_mb"] = max(50, min(50_000, mb))
        if "collectors_enabled" in kwargs and kwargs["collectors_enabled"] is not None:
            data["collectors_enabled"] = bool(kwargs["collectors_enabled"])
        if "collectors_interval_seconds" in kwargs and kwargs["collectors_interval_seconds"] is not None:
            sec = int(kwargs["collectors_interval_seconds"])
            data["collectors_interval_seconds"] = max(30, min(3600, sec))
        if "watchdog_enabled" in kwargs and kwargs["watchdog_enabled"] is not None:
            data["watchdog_enabled"] = bool(kwargs["watchdog_enabled"])
        if "watchdog_stale_minutes" in kwargs and kwargs["watchdog_stale_minutes"] is not None:
            stale = int(kwargs["watchdog_stale_minutes"])
            data["watchdog_stale_minutes"] = max(5, min(240, stale))
        _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return dict(data)


def sqlite_db_path() -> Path:
    return Path("data/app.db")


def sqlite_cache_status() -> dict[str, Any]:
    """Tamanho atual do SQLite vs teto de cache (legado)."""
    rt = get_runtime_settings()
    max_mb = float(rt.get("sqlite_cache_max_mb") or 200)
    path = sqlite_db_path()
    size_bytes = path.stat().st_size if path.exists() else 0
    size_mb = size_bytes / (1024 * 1024)
    pct = (size_mb / max_mb * 100.0) if max_mb > 0 else 0.0
    return {
        "path": str(path.resolve()) if path.exists() else str(path),
        "size_bytes": size_bytes,
        "size_mb": round(size_mb, 2),
        "max_mb": max_mb,
        "used_pct": round(pct, 1),
        "over_limit": size_mb >= max_mb,
        "note": (
            "SQLite legado (arquivo arquivado). Banco unico = Postgres no F:."
        ),
    }
