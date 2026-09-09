"""Descoberta de dispositivos Tuya Cloud ainda não cadastrados no Energy Meter.

Mesmo access_id/secret/projeto Tuya → lista na nuvem e compara com device_id
já salvos em Device.config. Sugere papel (rede vs saída do inversor).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Device
from app.services.tuya_poller import get_tuya_client


ENERGY_CATEGORIES = {
    "tdq",  # disjuntor trifásico com medição
    "cz",   # tomada com medição
    "dlq",  # breaker
    "kg",   # switch/energy variants
    "wk",   # some meters
}


def _registered_tuya_ids(db: Session) -> set[str]:
    ids: set[str] = set()
    for d in db.query(Device).filter(Device.device_type == "tuya").all():
        cfg = d.config or {}
        tid = cfg.get("device_id") or cfg.get("tuya_device_id")
        if tid:
            ids.add(str(tid))
    return ids


def _seed_device_id(db: Session) -> str | None:
    """TinyTuya às vezes precisa de um device_id seed no Cloud()."""
    for d in db.query(Device).filter(Device.device_type == "tuya", Device.active == True).all():  # noqa: E712
        cfg = d.config or {}
        tid = cfg.get("device_id") or cfg.get("tuya_device_id")
        if tid:
            return str(tid)
    return None


def suggest_role(cloud_device: dict[str, Any]) -> str:
    """Sugere papel no projeto energético."""
    name = str(cloud_device.get("name") or cloud_device.get("custom_name") or "").lower()
    category = str(cloud_device.get("category") or cloud_device.get("category_code") or "").lower()
    product = str(cloud_device.get("product_name") or cloud_device.get("model") or "").lower()
    blob = f"{name} {category} {product}"

    if any(k in blob for k in ("inversor", "inverter", "gerador", "solar_out", "pv ", "pv_", "string")):
        return "inverter_output"
    if category == "tdq" or any(k in blob for k in ("disjuntor", "entrada", "rede", "ponto de entrega", "grid")):
        return "grid_point"
    if category in ENERGY_CATEGORIES or "meter" in blob or "medidor" in blob or "energia" in blob:
        return "energy_meter"
    return "unknown"


def role_label(role: str) -> str:
    return {
        "grid_point": "Ponto de entrega / rede (consumo × injeção líquida)",
        "inverter_output": "Saída do inversor (corrente realmente gerada/injetada)",
        "energy_meter": "Medidor de energia genérico",
        "unknown": "Dispositivo Tuya (revisar papel)",
    }.get(role, role)


def discover_tuya_devices(db: Session) -> dict[str, Any]:
    seed = _seed_device_id(db)
    cloud = get_tuya_client(api_device_id=seed)
    if not cloud:
        return {
            "ok": False,
            "error": "Credenciais Tuya ausentes ou tinytuya indisponível (.env TUYA_*)",
            "devices": [],
            "registered_count": 0,
            "new_count": 0,
        }

    try:
        raw = cloud.getdevices()
    except Exception as e:
        return {
            "ok": False,
            "error": f"Falha ao listar dispositivos na nuvem Tuya: {e}",
            "devices": [],
            "registered_count": 0,
            "new_count": 0,
        }

    # tinytuya pode devolver list ou dict com result
    if isinstance(raw, dict):
        items = raw.get("result") or raw.get("devices") or []
        if isinstance(items, dict):
            items = items.get("list") or items.get("devices") or []
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    registered = _registered_tuya_ids(db)
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        tid = str(item.get("id") or item.get("device_id") or "")
        if not tid:
            continue
        role = suggest_role(item)
        already = tid in registered
        out.append(
            {
                "tuya_device_id": tid,
                "name": item.get("name") or item.get("custom_name") or tid,
                "category": item.get("category") or item.get("category_code"),
                "product_name": item.get("product_name") or item.get("model"),
                "online": item.get("online"),
                "already_registered": already,
                "suggested_role": role,
                "suggested_role_label": role_label(role),
                "is_energy_candidate": role in ("grid_point", "inverter_output", "energy_meter")
                or str(item.get("category") or "").lower() in ENERGY_CATEGORIES,
            }
        )

    new_ones = [d for d in out if not d["already_registered"]]
    return {
        "ok": True,
        "error": None,
        "devices": out,
        "registered_count": sum(1 for d in out if d["already_registered"]),
        "new_count": len(new_ones),
        "energy_new_count": sum(1 for d in new_ones if d["is_energy_candidate"]),
        "hint": (
            "Novos medidores no mesmo projeto Tuya aparecem aqui. "
            "Use 'Incluir no projeto' — especialmente o medidor na saída do inversor "
            "(papel inverter_output) quando chegar em casa."
        ),
    }
