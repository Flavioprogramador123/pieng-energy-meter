"""Configurações runtime persistidas em data/runtime_settings.json.

Permite o usuário alterar intervalo de flush SQLite→Postgres pela UI
sem editar .env nem reiniciar o processo (o job é reescalonado).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_PATH = Path("data/runtime_settings.json")

_DEFAULTS: dict[str, Any] = {
    "postgres_flush_enabled": True,
    # Teste no escritório (máquina não dedicada): 30 min reduz I/O no HD K:
    "postgres_flush_interval_minutes": 30,
    # Teto do SQLite hot enquanto o storage está fora (~3 dias c/ ~3 aparelhos)
    "sqlite_cache_max_mb": 200,
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
            if minutes < 1:
                minutes = 1
            if minutes > 24 * 60:
                minutes = 24 * 60
            data["postgres_flush_interval_minutes"] = minutes
        if "sqlite_cache_max_mb" in kwargs and kwargs["sqlite_cache_max_mb"] is not None:
            mb = int(kwargs["sqlite_cache_max_mb"])
            if mb < 50:
                mb = 50
            if mb > 50_000:
                mb = 50_000
            data["sqlite_cache_max_mb"] = mb
        _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return dict(data)


def sqlite_db_path() -> Path:
    return Path("data/app.db")


def sqlite_cache_status() -> dict[str, Any]:
    """Tamanho atual do SQLite vs teto de cache (quando storage está fora)."""
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
            "SQLite é o hot path: se o K:/Postgres ficar fora, os dados ficam aqui "
            "até o flush descarregar. Teto 200 MB ≈ 3 dias com ~3 aparelhos (teste)."
        ),
    }
