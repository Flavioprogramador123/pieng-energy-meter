"""Preferências da HOME: residências ativas e quais devices aparecem na grade."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

PREFS_PATH = Path("data/home_prefs.json")
_LOCK = threading.Lock()

DEFAULTS: dict[str, Any] = {
    # Lista de residências que entram na tela principal (None = auto: Minha casa)
    "selected_home_ids": None,
    "enabled_device_ids": None,  # None = auto (show_by_default do catálogo)
    "skip_offline_status": True,
    "cache_ttl_seconds": 25,
}


def _ensure_parent() -> None:
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)


def _as_int_list(value: Any) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    out: list[int] = []
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def load_prefs() -> dict[str, Any]:
    with _LOCK:
        if not PREFS_PATH.exists():
            return dict(DEFAULTS)
        try:
            data = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return dict(DEFAULTS)
        if not isinstance(data, dict):
            return dict(DEFAULTS)
        out = dict(DEFAULTS)
        out.update({k: data[k] for k in DEFAULTS if k in data})

        # Migração: selected_home_id (singular) → selected_home_ids
        if out.get("selected_home_ids") is None and data.get("selected_home_id") not in (None, "", "null"):
            try:
                out["selected_home_ids"] = [int(data["selected_home_id"])]
            except (TypeError, ValueError):
                pass

        ids = out.get("enabled_device_ids")
        if isinstance(ids, list):
            out["enabled_device_ids"] = [str(x) for x in ids]
        homes = _as_int_list(out.get("selected_home_ids"))
        out["selected_home_ids"] = homes
        return out


def save_prefs(**kwargs: Any) -> dict[str, Any]:
    current = load_prefs()
    if "selected_home_ids" in kwargs:
        current["selected_home_ids"] = _as_int_list(kwargs["selected_home_ids"])
    # Compat: aceitar singular e converter
    if "selected_home_id" in kwargs and "selected_home_ids" not in kwargs:
        hid = kwargs["selected_home_id"]
        current["selected_home_ids"] = [int(hid)] if hid not in (None, "", "null") else None
    if "enabled_device_ids" in kwargs:
        ids = kwargs["enabled_device_ids"]
        if ids is None:
            current["enabled_device_ids"] = None
        elif isinstance(ids, list):
            current["enabled_device_ids"] = [str(x) for x in ids]
    if "skip_offline_status" in kwargs and kwargs["skip_offline_status"] is not None:
        current["skip_offline_status"] = bool(kwargs["skip_offline_status"])
    if "cache_ttl_seconds" in kwargs and kwargs["cache_ttl_seconds"] is not None:
        current["cache_ttl_seconds"] = max(0, int(kwargs["cache_ttl_seconds"]))
    _ensure_parent()
    with _LOCK:
        PREFS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return current
