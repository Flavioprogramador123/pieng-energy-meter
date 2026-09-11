"""Cliente Tuya Cloud para o módulo HOME."""
from __future__ import annotations

import json
import re
import socket
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any

import tinytuya
from dotenv import load_dotenv

from app.core.config import settings
from home import prefs as home_prefs

# Evita falha de allowlist IPv6 na Tuya (só IPv4)
_orig_getaddrinfo = socket.getaddrinfo


def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _getaddrinfo_ipv4

load_dotenv(override=True)

CATALOG_PATH = Path(__file__).with_name("device_catalog.json")

# Fallbacks se o catálogo não tiver a categoria
LIGHT_CATEGORIES = {"dj", "dd", "fwd", "dc"}
SWITCH_CATEGORIES = {"kg", "tdq", "cz", "pc"}
AC_CATEGORIES = {"infrared_ac", "kt"}
SENSOR_CATEGORIES = {"wsdcg"}
GATEWAY_CATEGORIES = {"wg2"}
IR_HUB_CATEGORIES = {"wnykq"}
LIGHT_NAME_HINTS = ("luz", "light", "lamp", "led", "ilumina")
AC_NAME_HINTS = ("ar", "air", "ac", "clima", "consul", "split")
SHOW_KINDS_DEFAULT = {"light", "ac", "switch", "ir", "sensor", "gateway", "ir_hub", "meter"}
METER_NAME_HINTS = ("meter", "medidor", "solar wifi dual")

# DPs do ar-condicionado virtual (hub IR). Valores vêm como string enum.
AC_MODE_LABELS = {"0": "Refrigerar", "1": "Aquecer", "2": "Automático", "3": "Ventilar", "4": "Desumidificar"}
AC_FAN_LABELS = {"0": "Automático", "1": "Baixa", "2": "Média", "3": "Alta"}


def _matches_word(name: str, hints: tuple[str, ...]) -> bool:
    """Casa hints como palavra inteira (evita falso-positivo tipo 'Solar' ~ 'ar')."""
    return any(re.search(rf"\b{re.escape(h)}\b", name) for h in hints)


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        return {"version": 0, "categories": {}, "devices": {}}
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {"version": 0, "categories": {}, "devices": {}}


def catalog_entry(
    device_id: str | None = None,
    category: str | None = None,
    product: str | None = None,
) -> dict[str, Any]:
    """Merge: category → product (nome Tuya) → device_id. O que se repete fica no product."""
    catalog = load_catalog()
    merged: dict[str, Any] = {}
    cat = (category or "").lower()
    if cat and isinstance(catalog.get("categories"), dict):
        base = catalog["categories"].get(cat)
        if isinstance(base, dict):
            merged.update(base)

    # product template (nome do produto se repete entre aparelhos)
    products = catalog.get("products") if isinstance(catalog.get("products"), dict) else {}
    product_name = (product or "").strip()
    if device_id and isinstance(catalog.get("devices"), dict):
        override_preview = catalog["devices"].get(device_id)
        if isinstance(override_preview, dict) and not product_name:
            product_name = str(override_preview.get("product") or "").strip()
    if product_name and product_name in products and isinstance(products[product_name], dict):
        merged.update(products[product_name])

    if device_id and isinstance(catalog.get("devices"), dict):
        override = catalog["devices"].get(device_id)
        if isinstance(override, dict):
            # se o device aponta product ainda não mergeado, aplica
            prod2 = str(override.get("product") or "").strip()
            if prod2 and prod2 in products and prod2 != product_name and isinstance(products[prod2], dict):
                merged.update(products[prod2])
            merged.update(override)
    return merged


def get_cloud() -> tinytuya.Cloud:
    aid = (settings.tuya_access_id or "").strip()
    asec = (settings.tuya_access_secret or "").strip()
    region = (settings.tuya_api_region or "us").strip()
    if not aid or not asec:
        raise RuntimeError("Credenciais Tuya ausentes no .env (TUYA_ACCESS_ID / TUYA_ACCESS_SECRET)")
    return tinytuya.Cloud(apiRegion=region, apiKey=aid, apiSecret=asec)


def _status_map(status: dict | None) -> dict[str, Any]:
    if not isinstance(status, dict):
        return {}
    result = status.get("result") or []
    if not isinstance(result, list):
        return {}
    out = {}
    for item in result:
        if isinstance(item, dict) and "code" in item:
            out[item["code"]] = item.get("value")
    return out


def _shadow_map(cloud: tinytuya.Cloud, device_id: str) -> dict[str, Any]:
    """Lê DPs via shadow/properties (necessário p/ medidores dual sem Standard Instruction)."""
    try:
        resp = cloud.cloudrequest(f"/v2.0/cloud/thing/{device_id}/shadow/properties")
    except Exception:
        return {}
    if not isinstance(resp, dict) or not resp.get("success"):
        return {}
    props = ((resp.get("result") or {}).get("properties")) or []
    out: dict[str, Any] = {}
    for item in props:
        if isinstance(item, dict) and item.get("code") is not None:
            out[str(item["code"])] = item.get("value")
    return out


def _device_status_map(
    cloud: tinytuya.Cloud,
    device_id: str,
    entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = entry or {}
    prefer_shadow = str(entry.get("status_source") or "").lower() == "shadow"
    if prefer_shadow:
        shadow = _shadow_map(cloud, device_id)
        if shadow:
            return shadow
    st = cloud.getstatus(device_id)
    smap = _status_map(st if isinstance(st, dict) else None)
    if smap:
        return smap
    # Fallback automático: getstatus vazio → tenta shadow
    return _shadow_map(cloud, device_id)


def classify_device(name: str, category: str, device_id: str | None = None, product: str | None = None) -> str:
    entry = catalog_entry(device_id, category, product)
    if entry.get("kind"):
        return str(entry["kind"])

    cat = (category or "").lower()
    n = (name or "").lower()
    if cat in AC_CATEGORIES or _matches_word(n, AC_NAME_HINTS):
        return "ac"
    if _matches_word(n, METER_NAME_HINTS) or "dual meter" in n:
        return "meter"
    if cat in SENSOR_CATEGORIES:
        return "sensor"
    if cat in GATEWAY_CATEGORIES:
        return "gateway"
    if cat in IR_HUB_CATEGORIES:
        return "ir_hub"
    if cat in LIGHT_CATEGORIES or _matches_word(n, LIGHT_NAME_HINTS):
        return "light"
    if cat in SWITCH_CATEGORIES:
        if _matches_word(n, LIGHT_NAME_HINTS):
            return "light"
        return "switch"
    if cat.startswith("infrared_"):
        return "ir"
    return "other"


def switch_code_for(status: dict[str, Any], kind: str) -> str | None:
    if "switch_led" in status:
        return "switch_led"
    for code in ("switch_1", "switch", "led_switch"):
        if code in status:
            return code
    if kind == "light":
        return "switch_led"
    return "switch_1"


def switch_channels_for(
    status: dict[str, Any],
    kind: str,
    entry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Retorna circuitos booleanos controláveis. Sensor/gateway/meter usam regras próprias."""
    entry = entry or {}
    if kind in {"sensor", "gateway", "ir_hub", "meter"}:
        return []

    preferred = entry.get("channels")
    if isinstance(preferred, list) and preferred:
        channels = []
        for item in preferred:
            if not isinstance(item, dict) or not item.get("code"):
                continue
            code = str(item["code"])
            channels.append(
                {
                    "code": code,
                    "label": item.get("label") or code,
                    "on": bool(status[code]) if isinstance(status.get(code), bool) else status.get(code),
                }
            )
        if channels:
            return channels

    codes = [
        code
        for code, value in status.items()
        if isinstance(value, bool)
        and (
            code in {"switch_led", "led_switch"}
            or re.fullmatch(r"switch_\d+", code)
            or (code == "switch" and kind in {"light", "switch"})
        )
    ]

    def sort_key(code: str) -> tuple[int, int | str]:
        match = re.fullmatch(r"switch_(\d+)", code)
        if match:
            return (0, int(match.group(1)))
        return (1, code)

    codes.sort(key=sort_key)
    if not codes:
        fallback = switch_code_for(status, kind)
        return [{"code": fallback, "label": "Controle", "on": status.get(fallback)}]

    channels = []
    for code in codes:
        match = re.fullmatch(r"switch_(\d+)", code)
        if match:
            label = f"Tecla {match.group(1)}"
        elif kind == "light":
            label = "Luz"
        else:
            label = "Controle"
        channels.append({"code": code, "label": label, "on": bool(status[code])})
    return channels


def _scaled_value(raw: Any, scale: int = 0) -> float | int | None:
    if raw is None:
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if scale and scale > 0:
        number = number / (10**scale)
        return round(number, scale)
    if number.is_integer():
        return int(number)
    return number


def _build_readings(status: dict[str, Any], entry: dict[str, Any], kind: str) -> dict[str, Any]:
    readings: dict[str, Any] = {}
    metrics = entry.get("metrics") or {}
    if isinstance(metrics, dict):
        for key, spec in metrics.items():
            if not isinstance(spec, dict):
                continue
            code = spec.get("code") or key
            readings[key] = {
                "code": code,
                "value": _scaled_value(status.get(code), int(spec.get("scale") or 0)),
                "unit": spec.get("unit") or "",
                "raw": status.get(code),
            }

    if kind == "sensor" and not readings:
        readings = {
            "temperature": {
                "code": "va_temperature",
                "value": _scaled_value(status.get("va_temperature"), 1),
                "unit": "°C",
                "raw": status.get("va_temperature"),
            },
            "humidity": {
                "code": "va_humidity",
                "value": _scaled_value(status.get("va_humidity"), 1),
                "unit": "%",
                "raw": status.get("va_humidity"),
            },
            "battery": {
                "code": "battery_percentage",
                "value": _scaled_value(status.get("battery_percentage"), 0),
                "unit": "%",
                "raw": status.get("battery_percentage"),
            },
        }

    if kind == "gateway":
        readings.setdefault(
            "master_state",
            {"code": "master_state", "value": status.get("master_state"), "unit": "", "raw": status.get("master_state")},
        )
        readings.setdefault(
            "alarm_active",
            {"code": "alarm_active", "value": status.get("alarm_active") or "", "unit": "", "raw": status.get("alarm_active")},
        )

    if kind == "meter":
        for code in ("direction_a", "direction_b"):
            if code in status and code not in readings:
                readings[code] = {"code": code, "value": status.get(code), "unit": "", "raw": status.get(code)}

    return readings


def _remote_keys(entry: dict[str, Any]) -> dict[str, Any]:
    remote = entry.get("remote")
    keys = remote.get("keys") if isinstance(remote, dict) else None
    return keys if isinstance(keys, dict) else {}


def power_keys_for(entry: dict[str, Any]) -> tuple[str, str, bool]:
    """Retorna (tecla_ligar, tecla_desligar, is_toggle) do controle IR."""
    keys = _remote_keys(entry)
    on_key = keys.get("power_on")
    off_key = keys.get("power_off")
    if on_key and off_key:
        return str(on_key), str(off_key), False
    toggle = keys.get("power")
    if toggle:
        return str(toggle), str(toggle), True
    return "PowerOn", "PowerOff", False


def _ac_readings(status: dict[str, Any]) -> dict[str, Any]:
    """Estado do ar lido dos DPs do device virtual (mode/fan vêm como enum string)."""
    mode = status.get("mode")
    fan = status.get("fan")
    readings: dict[str, Any] = {}
    if mode is not None:
        readings["mode"] = {
            "code": "mode",
            "value": AC_MODE_LABELS.get(str(mode), str(mode)),
            "unit": "",
            "raw": mode,
        }
    if fan is not None:
        readings["fan"] = {
            "code": "fan",
            "value": AC_FAN_LABELS.get(str(fan), str(fan)),
            "unit": "",
            "raw": fan,
        }
    if isinstance(status.get("swing"), bool):
        readings["swing"] = {
            "code": "swing",
            "value": "Ligado" if status["swing"] else "Desligado",
            "unit": "",
            "raw": status["swing"],
        }
    return readings


def _safe_controls(status: dict[str, Any], entry: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    forbidden = set(entry.get("forbidden") or [])
    controls: list[dict[str, Any]] = []

    for item in entry.get("safe_controls") or []:
        if not isinstance(item, dict) or not item.get("code"):
            continue
        code = str(item["code"])
        if code in forbidden:
            continue
        controls.append(
            {
                "code": code,
                "label": item.get("label") or code,
                "type": item.get("type") or "boolean",
                "on": bool(status[code]) if isinstance(status.get(code), bool) else status.get(code),
            }
        )

    optional = entry.get("optional_switch")
    if kind == "sensor" and isinstance(optional, dict) and optional.get("code"):
        code = str(optional["code"])
        if code not in forbidden:
            controls.append(
                {
                    "code": code,
                    "label": optional.get("label") or "Recurso",
                    "type": "boolean",
                    "on": bool(status[code]) if isinstance(status.get(code), bool) else status.get(code),
                }
            )

    return controls


def _build_home_device(
    cloud: tinytuya.Cloud,
    device: dict[str, Any],
    *,
    skip_status: bool = False,
) -> dict[str, Any] | None:
    device_id = device.get("id")
    if not device_id:
        return None
    name = (device.get("name") or "").strip() or device_id
    category = device.get("category") or ""
    product_name = (device.get("product_name") or "").strip() or None
    entry = catalog_entry(device_id, category, product_name)
    # product do catálogo pode sobrescrever o nome técnico
    product_name = entry.get("product") or product_name or device.get("product_name")
    kind = classify_device(name, category, device_id, product_name)
    card = entry.get("card") or kind
    smap: dict[str, Any] = {} if skip_status else _device_status_map(cloud, device_id, entry)
    channels = switch_channels_for(smap, kind, entry)
    sw_code = channels[0]["code"] if channels else switch_code_for(smap, kind)
    on = None
    if channels and isinstance(channels[0].get("on"), bool):
        on = channels[0]["on"]
    elif "power" in smap:
        on = bool(smap["power"])

    raw_temp = next(
        (
            smap[code]
            for code in ("temperature", "temp", "T", "temp_set", "temp_current")
            if smap.get(code) is not None
        ),
        None,
    )
    try:
        temp = int(float(raw_temp)) if raw_temp is not None else None
    except (TypeError, ValueError):
        temp = None

    readings = _build_readings(smap, entry, kind)

    power_mode = None
    if kind in {"ac", "ir"} or entry.get("control") == "ir_hub":
        _, _, is_toggle = power_keys_for(entry)
        power_mode = "toggle" if is_toggle else "onoff"

    if kind == "ac":
        # O device virtual do hub IR guarda o estado em switch_power/temperature
        if isinstance(smap.get("switch_power"), bool):
            on = smap["switch_power"]
        channels = []
        readings = {**_ac_readings(smap), **readings}
    elif kind == "ir":
        # Controle IR puro: sem realimentação de estado (via infravermelho)
        channels = []

    if kind == "sensor" and readings.get("temperature", {}).get("value") is not None and temp is None:
        try:
            temp = int(round(float(readings["temperature"]["value"])))
        except (TypeError, ValueError):
            pass

    online = device.get("online")
    if online is None and entry.get("status") == "offline":
        online = False

    return {
        "id": device_id,
        "name": entry.get("name") or name,
        "category": category,
        "category_label": entry.get("label") or category,
        "kind": kind,
        "card": card,
        "product": product_name,
        "online": online,
        "on": on,
        "temp": temp,
        "power_mode": power_mode,
        "switch_code": None if kind in {"ac", "ir"} else sw_code,
        "channels": channels,
        "readings": readings,
        "controls": _safe_controls(smap, entry, kind),
        "forbidden": entry.get("forbidden") or [],
        "control": entry.get("control"),
        "gateway_id": device.get("gateway_id") or entry.get("gateway_id"),
        "home_id": device.get("home_id"),
        "catalog": {
            "label": entry.get("label"),
            "notes": entry.get("notes"),
            "validated": entry.get("validated"),
        },
        "status": smap,
    }


def _cloud_devices(cloud: tinytuya.Cloud, *, enrich_online: bool = True) -> list[dict[str, Any]]:
    raw = cloud.getdevices()
    items = raw if isinstance(raw, list) else (raw or {}).get("result") or []
    devices = [item for item in items if isinstance(item, dict)]
    if enrich_online:
        return _enrich_online_flags(cloud, devices)
    return devices


def _enrich_online_flags(cloud: tinytuya.Cloud, devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """getdevices não traz online; batch /v2.0/cloud/thing/batch preenche is_online."""
    ids = [str(d.get("id")) for d in devices if d.get("id")]
    online_map: dict[str, bool] = {}
    chunk_size = 20
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        if not chunk:
            continue
        try:
            resp = cloud.cloudrequest(
                "/v2.0/cloud/thing/batch",
                query={"device_ids": ",".join(chunk)},
            )
        except Exception:
            continue
        rows = (resp or {}).get("result") if isinstance(resp, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("id") is not None:
                online_map[str(row["id"])] = bool(row.get("is_online"))

    for device in devices:
        did = str(device.get("id") or "")
        if did in online_map:
            device["online"] = online_map[did]
        elif "online" not in device:
            device["online"] = None
        # Controles virtuais IR: disponibilidade segue o hub físico
        gateway_id = device.get("gateway_id")
        if not gateway_id:
            entry = catalog_entry(did, device.get("category"), device.get("product_name"))
            gateway_id = entry.get("gateway_id")
            if gateway_id:
                device["gateway_id"] = gateway_id
        if gateway_id and str(gateway_id) in online_map:
            if device.get("online") is not True:
                device["online"] = online_map[str(gateway_id)]
    return devices


def _find_device_meta(cloud: tinytuya.Cloud, device_id: str) -> dict[str, Any] | None:
    for device in _cloud_devices(cloud, enrich_online=False):
        if device.get("id") == device_id:
            return device
    return None


# ---- Residências (homes/spaces) + cache da grade ----

_LIST_CACHE: dict[str, Any] = {"key": None, "at": 0.0, "payload": None}
_LIST_LOCK = threading.Lock()


def invalidate_devices_cache() -> None:
    with _LIST_LOCK:
        _LIST_CACHE["key"] = None
        _LIST_CACHE["at"] = 0.0
        _LIST_CACHE["payload"] = None


_HOMES_CACHE: dict[str, Any] = {"at": 0.0, "homes": None}
_HOMES_TTL = 120.0


def list_tuya_homes(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """Lista residências da conta via space child + detalhe + contagem de devices."""
    now = time.time()
    if not force_refresh and _HOMES_CACHE["homes"] is not None and (now - float(_HOMES_CACHE["at"] or 0)) < _HOMES_TTL:
        return list(_HOMES_CACHE["homes"])

    cloud = get_cloud()
    space = cloud.cloudrequest("/v2.0/cloud/space/child")
    ids = ((space or {}).get("result") or {}).get("data") or []
    homes: list[dict[str, Any]] = []
    for sid in ids:
        try:
            sid_int = int(sid)
        except (TypeError, ValueError):
            continue
        name = str(sid_int)
        try:
            detail = cloud.cloudrequest(f"/v2.0/cloud/space/{sid_int}")
            if isinstance(detail, dict) and isinstance(detail.get("result"), dict):
                name = detail["result"].get("name") or name
        except Exception:
            pass
        count = 0
        try:
            devices = cloud.cloudrequest(f"/v1.0/homes/{sid_int}/devices")
            if isinstance(devices, dict) and isinstance(devices.get("result"), list):
                count = len(devices["result"])
        except Exception:
            pass
        homes.append({"id": sid_int, "name": name, "device_count": count})
    homes.sort(key=lambda h: h["name"].lower())
    _HOMES_CACHE["at"] = now
    _HOMES_CACHE["homes"] = homes
    return list(homes)


def _pick_default_home_id(homes: list[dict[str, Any]]) -> int | None:
    if not homes:
        return None
    for h in homes:
        n = (h.get("name") or "").lower()
        if "minha casa" in n or n.strip() in {"casa", "home"}:
            return int(h["id"])
    return int(max(homes, key=lambda x: x.get("device_count") or 0)["id"])


def resolve_selected_home_ids(prefs: dict[str, Any] | None = None) -> list[int]:
    """Residências que entram na tela principal (pode ser várias)."""
    p = prefs or home_prefs.load_prefs()
    raw = p.get("selected_home_ids")
    if isinstance(raw, list) and raw:
        out: list[int] = []
        for item in raw:
            try:
                out.append(int(item))
            except (TypeError, ValueError):
                continue
        if out:
            return out

    homes = list_tuya_homes()
    picked = _pick_default_home_id(homes)
    if picked is None:
        return []
    try:
        home_prefs.save_prefs(selected_home_ids=[picked])
    except Exception:
        pass
    return [picked]


def resolve_selected_home_id(prefs: dict[str, Any] | None = None) -> int | None:
    """Compat: primeira residência selecionada."""
    ids = resolve_selected_home_ids(prefs)
    return ids[0] if ids else None


def _devices_for_home(cloud: tinytuya.Cloud, home_id: int) -> list[dict[str, Any]]:
    """Devices de uma residência. A API já traz `online` — evita batch em toda a conta."""
    resp = cloud.cloudrequest(f"/v1.0/homes/{home_id}/devices")
    items = (resp or {}).get("result") if isinstance(resp, dict) else None
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        row = dict(item)
        row["home_id"] = home_id
        if "online" in row:
            row["online"] = bool(row["online"])
        out.append(row)
    return out


def _should_show_device(
    raw: dict[str, Any],
    *,
    include_other: bool,
    enabled_ids: set[str] | None,
) -> bool:
    name = (raw.get("name") or "").strip()
    category = raw.get("category") or ""
    device_id = str(raw.get("id") or "")
    product_name = (raw.get("product_name") or "").strip() or None
    kind = classify_device(name, category, device_id, product_name)
    entry = catalog_entry(device_id, category, product_name)

    if enabled_ids is not None:
        return device_id in enabled_ids

    show = entry.get("show_by_default")
    if show is None:
        show = kind in SHOW_KINDS_DEFAULT
    if not include_other and not show and kind == "other":
        return False
    if not include_other and not show:
        return False
    return True


def _inventory_device_row(
    raw: dict[str, Any],
    *,
    enabled_set: set[str] | None,
    home_selected: bool,
) -> dict[str, Any]:
    did = str(raw.get("id"))
    name = (raw.get("name") or "").strip() or did
    category = raw.get("category") or ""
    product_name = (raw.get("product_name") or "").strip() or None
    kind = classify_device(name, category, did, product_name)
    entry = catalog_entry(did, category, product_name)
    auto_show = entry.get("show_by_default")
    if auto_show is None:
        auto_show = kind in SHOW_KINDS_DEFAULT
    if enabled_set is not None:
        enabled_flag = did in enabled_set
    else:
        enabled_flag = bool(auto_show) and home_selected
    return {
        "id": did,
        "name": entry.get("name") or name,
        "kind": kind,
        "category": category,
        "product": product_name or entry.get("product"),
        "online": raw.get("online"),
        "enabled": enabled_flag,
        "auto_show": bool(auto_show),
        "home_id": raw.get("home_id"),
    }


def inventory_all_homes() -> dict[str, Any]:
    """Inventário completo: todas as residências + devices (leve, sem status)."""
    cloud = get_cloud()
    prefs = home_prefs.load_prefs()
    selected_ids = set(resolve_selected_home_ids(prefs))
    enabled = prefs.get("enabled_device_ids")
    enabled_set = set(enabled) if isinstance(enabled, list) else None

    homes_out: list[dict[str, Any]] = []
    for home in list_tuya_homes():
        hid = int(home["id"])
        home_selected = hid in selected_ids
        devices = [
            _inventory_device_row(raw, enabled_set=enabled_set, home_selected=home_selected)
            for raw in _devices_for_home(cloud, hid)
        ]
        devices.sort(key=lambda x: (0 if x["enabled"] else 1, x["name"].lower()))
        homes_out.append(
            {
                "id": hid,
                "name": home.get("name") or str(hid),
                "device_count": len(devices),
                "selected": home_selected,
                "devices": devices,
            }
        )
    return {
        "selected_home_ids": sorted(selected_ids),
        "homes": homes_out,
    }


def inventory_home_devices(home_id: int | None = None) -> dict[str, Any]:
    """Compat: inventário de uma residência (ou todas se home_id=None)."""
    if home_id is None:
        return inventory_all_homes()
    all_data = inventory_all_homes()
    for home in all_data.get("homes") or []:
        if int(home["id"]) == int(home_id):
            return {"home_id": int(home_id), "devices": home.get("devices") or [], "homes": all_data["homes"]}
    return {"home_id": int(home_id), "devices": [], "homes": all_data.get("homes") or []}


def get_home_device(device_id: str) -> dict[str, Any] | None:
    """Atualiza estado de um device; reaproveita metadados do catálogo quando possível."""
    cloud = get_cloud()
    meta = _find_device_meta(cloud, device_id)
    entry = catalog_entry(device_id)
    if not meta:
        meta = {
            "id": device_id,
            "name": entry.get("name") or device_id,
            "category": entry.get("category") or "",
            "product_name": entry.get("product"),
            "gateway_id": entry.get("gateway_id"),
        }
    elif entry.get("category") and not meta.get("category"):
        meta = {**meta, "category": entry["category"]}
    # online pontual (+ hub IR herda disponibilidade do gateway)
    try:
        thing = cloud.cloudrequest(f"/v2.0/cloud/thing/{device_id}")
        if isinstance(thing, dict) and isinstance(thing.get("result"), dict):
            result = thing["result"]
            online = bool(result.get("is_online"))
            gateway_id = result.get("gateway_id") or meta.get("gateway_id") or entry.get("gateway_id")
            if not online and gateway_id:
                hub = cloud.cloudrequest(f"/v2.0/cloud/thing/{gateway_id}")
                if isinstance(hub, dict) and isinstance(hub.get("result"), dict):
                    online = bool(hub["result"].get("is_online"))
            meta = {**meta, "online": online, "gateway_id": gateway_id or meta.get("gateway_id")}
    except Exception:
        pass
    return _build_home_device(cloud, meta)


def list_home_devices(
    include_other: bool = False,
    *,
    home_id: int | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Grade da HOME: residências selecionadas + devices habilitados."""
    prefs = home_prefs.load_prefs()
    ttl = int(prefs.get("cache_ttl_seconds") or 0)
    skip_offline = bool(prefs.get("skip_offline_status", True))
    if home_id is not None:
        home_ids = [int(home_id)]
    else:
        home_ids = resolve_selected_home_ids(prefs)
    enabled = prefs.get("enabled_device_ids")
    enabled_set = set(str(x) for x in enabled) if isinstance(enabled, list) else None

    cache_key = (
        f"{sorted(home_ids)}|{include_other}|"
        f"{sorted(enabled_set) if enabled_set is not None else 'auto'}|{skip_offline}"
    )
    now = time.time()
    if not force_refresh and ttl > 0:
        with _LIST_LOCK:
            if _LIST_CACHE["key"] == cache_key and (now - float(_LIST_CACHE["at"] or 0)) < ttl:
                cached = _LIST_CACHE["payload"]
                if isinstance(cached, dict):
                    out = dict(cached)
                    out["cached"] = True
                    return out

    t0 = time.perf_counter()
    cloud = get_cloud()

    pool_raw: list[dict[str, Any]] = []
    home_names: list[str] = []
    if home_ids:
        for hid in home_ids:
            pool_raw.extend(_devices_for_home(cloud, hid))
            try:
                detail = cloud.cloudrequest(f"/v2.0/cloud/space/{hid}")
                if isinstance(detail, dict) and isinstance(detail.get("result"), dict):
                    nm = detail["result"].get("name")
                    if nm:
                        home_names.append(str(nm))
            except Exception:
                home_names.append(str(hid))
    else:
        pool_raw = _cloud_devices(cloud, enrich_online=True)

    visible = [
        raw for raw in pool_raw
        if _should_show_device(raw, include_other=include_other, enabled_ids=enabled_set)
    ]

    def build(raw: dict[str, Any]) -> dict[str, Any] | None:
        try:
            offline = raw.get("online") is False
            return _build_home_device(cloud, raw, skip_status=(skip_offline and offline))
        except Exception:
            return None

    devices: list[dict[str, Any]] = []
    if visible:
        with ThreadPoolExecutor(max_workers=8) as pool:
            devices = [d for d in pool.map(build, visible) if d]

    order = {
        "sensor": 0,
        "meter": 1,
        "light": 2,
        "ac": 3,
        "switch": 4,
        "gateway": 5,
        "ir_hub": 6,
        "ir": 7,
        "other": 9,
    }
    devices.sort(key=lambda x: (order.get(x["kind"], 9), x["name"].lower()))
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    if not home_names:
        home_name = None
    elif len(home_names) == 1:
        home_name = home_names[0]
    else:
        home_name = " · ".join(home_names)

    payload = {
        "devices": devices,
        "home_id": home_ids[0] if len(home_ids) == 1 else None,
        "home_ids": home_ids,
        "home_name": home_name,
        "count": len(devices),
        "scanned": len(pool_raw),
        "elapsed_ms": elapsed_ms,
        "cached": False,
        "skip_offline_status": skip_offline,
    }
    if ttl > 0:
        with _LIST_LOCK:
            _LIST_CACHE["key"] = cache_key
            _LIST_CACHE["at"] = now
            _LIST_CACHE["payload"] = payload
    return payload


def send_commands(device_id: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    cloud = get_cloud()
    # Bloqueia códigos perigosos conhecidos
    entry = catalog_entry(device_id)
    forbidden = set(entry.get("forbidden") or ["factory_reset"])
    for cmd in commands:
        if isinstance(cmd, dict) and cmd.get("code") in forbidden:
            return {"success": False, "msg": f"Código bloqueado por segurança: {cmd.get('code')}"}
    resp = cloud.sendcommand(device_id, {"commands": commands})
    return resp if isinstance(resp, dict) else {"raw": resp}


def _resolve_ir_remote(cloud: tinytuya.Cloud, device_id: str) -> dict[str, Any] | None:
    """Resolve o hub IR físico e o remote virtual vinculados ao controle."""
    entry = catalog_entry(device_id)
    meta = _find_device_meta(cloud, device_id)
    if not meta and not entry.get("gateway_id"):
        return None
    infrared_id = (meta or {}).get("gateway_id") or entry.get("gateway_id")
    if not infrared_id:
        return None

    cached_remote = entry.get("remote") if isinstance(entry.get("remote"), dict) else {}
    remotes = cloud.cloudrequest(f"/v2.0/infrareds/{infrared_id}/remotes")
    if not isinstance(remotes, dict) or not remotes.get("success"):
        return {
            "infrared_id": infrared_id,
            "remote_id": device_id,
            "category_id": cached_remote.get("category_id")
            or (5 if "ac" in str((meta or {}).get("category") or entry.get("category") or "").lower() else None),
            "remote_index": cached_remote.get("remote_index"),
            "error": remotes,
        }

    for remote in remotes.get("result") or []:
        if not isinstance(remote, dict):
            continue
        if remote.get("remote_id") == device_id:
            return {
                "infrared_id": infrared_id,
                "remote_id": device_id,
                "category_id": remote.get("category_id") or cached_remote.get("category_id"),
                "remote_index": remote.get("remote_index") or cached_remote.get("remote_index"),
                "brand_name": remote.get("brand_name") or cached_remote.get("brand_name"),
                "remote_name": remote.get("remote_name"),
            }
    return {
        "infrared_id": infrared_id,
        "remote_id": device_id,
        "category_id": cached_remote.get("category_id")
        or (5 if "ac" in str((meta or {}).get("category") or "").lower() else None),
        "remote_index": cached_remote.get("remote_index"),
    }


def send_ir_key(device_id: str, key: str) -> dict[str, Any]:
    """Envia comando padrão pelo hub IR físico (necessário para ar/TV)."""
    cloud = get_cloud()
    remote = _resolve_ir_remote(cloud, device_id)
    if not remote or not remote.get("infrared_id"):
        return {"success": False, "msg": "Hub IR / remote não encontrado", "remote": remote}

    body: dict[str, Any] = {"key": key}
    if remote.get("category_id") is not None:
        body["category_id"] = remote["category_id"]
    if remote.get("remote_index") is not None:
        body["remote_index"] = remote["remote_index"]

    url = f"/v2.0/infrareds/{remote['infrared_id']}/remotes/{remote['remote_id']}/command"
    resp = cloud.cloudrequest(url, action="POST", post=body)
    if isinstance(resp, dict):
        resp = {**resp, "ir": {"url": url, "body": body, "remote": remote}}
        return resp
    return {"raw": resp, "ir": {"url": url, "body": body, "remote": remote}}


def set_switch(device_id: str, on: bool, code: str | None = None) -> dict[str, Any]:
    cloud = get_cloud()
    entry = catalog_entry(device_id)
    if code and code in set(entry.get("forbidden") or ["factory_reset"]):
        return {"success": False, "msg": f"Código bloqueado por segurança: {code}"}

    # Recusa comando se offline (exceto IR virtual, que depende do hub)
    try:
        thing = cloud.cloudrequest(f"/v2.0/cloud/thing/{device_id}")
        result = (thing or {}).get("result") if isinstance(thing, dict) else None
        if isinstance(result, dict) and result.get("is_online") is False and not result.get("gateway_id") and not entry.get("gateway_id"):
            return {"success": False, "msg": "Dispositivo offline", "online": False}
    except Exception:
        pass

    st = _status_map(cloud.getstatus(device_id))
    funcs = cloud.getfunctions(device_id)
    func_codes: set[str] = set()
    if isinstance(funcs, dict):
        for f in ((funcs.get("result") or {}).get("functions") or []):
            if isinstance(f, dict) and f.get("code"):
                func_codes.add(str(f["code"]))

    meta = _find_device_meta(cloud, device_id) or {}
    category = str(meta.get("category") or entry.get("category") or "")
    if entry.get("control") == "ir_hub" or (
        meta.get("gateway_id")
        and (
            category.startswith("infrared_")
            or ("PowerOn" in func_codes and "PowerOff" in func_codes)
        )
    ):
        on_key, off_key, _toggle = power_keys_for(entry)
        return send_ir_key(device_id, on_key if on else off_key)

    if "PowerOn" in func_codes and "PowerOff" in func_codes and not code:
        cmd = "PowerOn" if on else "PowerOff"
        return send_commands(device_id, [{"code": cmd, "value": cmd}])

    use_code = code or switch_code_for(st, "light") or "switch_1"
    return send_commands(device_id, [{"code": use_code, "value": bool(on)}])


def set_ac_power(device_id: str, on: bool) -> dict[str, Any]:
    # Preferência: API IR do hub físico (é ela que emite o infravermelho de verdade).
    entry = catalog_entry(device_id)
    on_key, off_key, _toggle = power_keys_for(entry)
    resp = send_ir_key(device_id, on_key if on else off_key)
    if isinstance(resp, dict) and resp.get("success"):
        return resp
    # Fallback: DP do device virtual
    resp2 = send_commands(device_id, [{"code": "switch_power", "value": bool(on)}])
    if isinstance(resp2, dict) and resp2.get("success"):
        return resp2
    cmd = "PowerOn" if on else "PowerOff"
    resp3 = send_commands(device_id, [{"code": cmd, "value": cmd}])
    if isinstance(resp3, dict) and resp3.get("success"):
        return resp3
    return resp if isinstance(resp, dict) else resp3


def set_ac_temp(device_id: str, temp: int) -> dict[str, Any]:
    temp = max(16, min(30, int(temp)))
    # Chaves padrão IR: T16..T30
    resp = send_ir_key(device_id, f"T{temp}")
    if isinstance(resp, dict) and resp.get("success"):
        return resp
    # Fallback: DP temperature do device virtual (o hub converte em IR)
    for code in ("temperature", "temp", "temp_set", "T"):
        alt = send_commands(device_id, [{"code": code, "value": temp}])
        if isinstance(alt, dict) and alt.get("success"):
            return alt
    return resp if isinstance(resp, dict) else {"success": False, "msg": "Nenhum código de temperatura aceito"}


def set_ac_setting(device_id: str, setting: str, value: str | bool | int) -> dict[str, Any]:
    """Ajusta modo (M0-M4), vento (F0-F3) ou swing do ar via hub IR / DP virtual."""
    setting = (setting or "").strip().lower()
    entry = catalog_entry(device_id)
    keys = _remote_keys(entry)

    if setting == "mode":
        idx = str(value)
        if idx not in AC_MODE_LABELS:
            return {"success": False, "msg": f"Modo inválido: {value}"}
        prefix = str(keys.get("mode") or "M")
        ir_key = f"{prefix}{idx}"
        resp = send_ir_key(device_id, ir_key)
        if isinstance(resp, dict) and resp.get("success"):
            return {**resp, "setting": setting, "value": idx, "label": AC_MODE_LABELS[idx]}
        alt = send_commands(device_id, [{"code": "mode", "value": idx}])
        if isinstance(alt, dict) and alt.get("success"):
            return {**alt, "setting": setting, "value": idx, "label": AC_MODE_LABELS[idx]}
        return resp if isinstance(resp, dict) else {"success": False, "msg": "Modo não aceito"}

    if setting == "fan":
        idx = str(value)
        if idx not in AC_FAN_LABELS:
            return {"success": False, "msg": f"Vento inválido: {value}"}
        prefix = str(keys.get("fan") or "F")
        ir_key = f"{prefix}{idx}"
        resp = send_ir_key(device_id, ir_key)
        if isinstance(resp, dict) and resp.get("success"):
            return {**resp, "setting": setting, "value": idx, "label": AC_FAN_LABELS[idx]}
        alt = send_commands(device_id, [{"code": "fan", "value": idx}])
        if isinstance(alt, dict) and alt.get("success"):
            return {**alt, "setting": setting, "value": idx, "label": AC_FAN_LABELS[idx]}
        return resp if isinstance(resp, dict) else {"success": False, "msg": "Vento não aceito"}

    if setting == "swing":
        on = value if isinstance(value, bool) else str(value).lower() in {"1", "true", "on", "ligado"}
        # Alguns remotes têm tecla Swing; a maioria usa DP booleano no virtual
        resp = send_ir_key(device_id, "Swing")
        if isinstance(resp, dict) and resp.get("success"):
            return {**resp, "setting": setting, "value": on}
        alt = send_commands(device_id, [{"code": "swing", "value": on}])
        if isinstance(alt, dict) and alt.get("success"):
            return {**alt, "setting": setting, "value": on}
        return resp if isinstance(resp, dict) else {"success": False, "msg": "Swing não aceito"}

    return {"success": False, "msg": f"Ajuste desconhecido: {setting}"}
