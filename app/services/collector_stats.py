"""Estatísticas leves de coleta (último sucesso + contagem do dia).

Usado pelo dashboard (status ao vivo) e pelo painel /api/db.
A contagem do dia zera automaticamente quando a data local muda (00:00).
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_LOCK = threading.Lock()
_PATH = Path("data/collector_stats.json")
_TZ = ZoneInfo("America/Sao_Paulo")


def _today_local() -> str:
    return datetime.now(_TZ).date().isoformat()


def _load() -> dict[str, Any]:
    if not _PATH.exists():
        return {"day": _today_local(), "poll_cycles_today": 0, "points_today": 0, "last_success_at": None}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid")
        return data
    except Exception:
        return {"day": _today_local(), "poll_cycles_today": 0, "points_today": 0, "last_success_at": None}


def _save(data: dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def note_poll_success(*, points: int = 0) -> dict[str, Any]:
    """Registra um ciclo de poll bem-sucedido (chamar após gravar medições)."""
    with _LOCK:
        data = _load()
        today = _today_local()
        if data.get("day") != today:
            data = {"day": today, "poll_cycles_today": 0, "points_today": 0, "last_success_at": None}
        data["poll_cycles_today"] = int(data.get("poll_cycles_today") or 0) + 1
        data["points_today"] = int(data.get("points_today") or 0) + max(0, int(points))
        data["last_success_at"] = datetime.now(_TZ).isoformat(timespec="seconds")
        _save(data)
        return dict(data)


def get_collector_stats() -> dict[str, Any]:
    """Snapshot para UI. Contagem do dia zera à meia-noite local."""
    with _LOCK:
        data = _load()
        today = _today_local()
        if data.get("day") != today:
            data = {"day": today, "poll_cycles_today": 0, "points_today": 0, "last_success_at": None}
            _save(data)
        return {
            "day": data.get("day"),
            "timezone": "America/Sao_Paulo",
            "poll_cycles_today": int(data.get("poll_cycles_today") or 0),
            "points_today": int(data.get("points_today") or 0),
            "last_success_at": data.get("last_success_at"),
        }
