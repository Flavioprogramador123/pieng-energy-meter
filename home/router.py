"""Rotas API + página do módulo HOME."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from home import prefs as home_prefs
from home import tuya_client

router = APIRouter(tags=["home"])
templates = Jinja2Templates(directory="home/templates")


def _log(msg: str) -> None:
    print(f"[HOME] {msg}", flush=True)


class SwitchBody(BaseModel):
    on: bool
    code: str | None = None


class AcPowerBody(BaseModel):
    on: bool


class AcTempBody(BaseModel):
    temp: int = Field(..., ge=16, le=30)


class PrefsBody(BaseModel):
    selected_home_ids: list[int] | None = None
    selected_home_id: int | None = None  # compat
    enabled_device_ids: list[str] | None = None
    skip_offline_status: bool | None = None


@router.get("", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/api/catalog")
def api_catalog():
    """Conhecimento capturado dos devices (JSON versionado em home/device_catalog.json)."""
    try:
        return {"ok": True, "catalog": tuya_client.load_catalog()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/homes")
def api_homes():
    try:
        homes = tuya_client.list_tuya_homes()
        prefs = home_prefs.load_prefs()
        selected_ids = tuya_client.resolve_selected_home_ids(prefs)
        return {
            "ok": True,
            "homes": homes,
            "selected_home_ids": selected_ids,
            "selected_home_id": selected_ids[0] if selected_ids else None,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/api/prefs")
def api_prefs_get():
    prefs = home_prefs.load_prefs()
    selected_ids = tuya_client.resolve_selected_home_ids(prefs)
    return {
        "ok": True,
        "prefs": prefs,
        "selected_home_ids": selected_ids,
        "selected_home_id": selected_ids[0] if selected_ids else None,
    }


@router.put("/api/prefs")
def api_prefs_put(body: PrefsBody):
    try:
        kwargs: dict = {
            "enabled_device_ids": body.enabled_device_ids,
            "skip_offline_status": body.skip_offline_status,
        }
        if body.selected_home_ids is not None:
            kwargs["selected_home_ids"] = body.selected_home_ids
        elif body.selected_home_id is not None:
            kwargs["selected_home_ids"] = [body.selected_home_id]
        saved = home_prefs.save_prefs(**kwargs)
        tuya_client.invalidate_devices_cache()
        return {"ok": True, "prefs": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/devices/inventory")
def api_devices_inventory(home_id: int | None = None):
    """Inventário leve (sem status) — todas as residências, ou uma se home_id informado."""
    try:
        if home_id is None:
            data = tuya_client.inventory_all_homes()
        else:
            data = tuya_client.inventory_home_devices(home_id=home_id)
        return {"ok": True, **data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/api/devices")
def api_devices(include_other: bool = False, refresh: bool = False):
    try:
        payload = tuya_client.list_home_devices(
            include_other=include_other,
            force_refresh=refresh,
        )
        return {"ok": True, **payload}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/api/devices/{device_id}")
def api_device(device_id: str):
    try:
        device = tuya_client.get_home_device(device_id)
        if device:
            return {"ok": True, "device": device}
        raise HTTPException(status_code=404, detail="Device não encontrado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/api/devices/{device_id}/switch")
def api_switch(device_id: str, body: SwitchBody, kind: str | None = None):
    _log(f"SWITCH device={device_id} on={body.on} code={body.code} kind={kind}")
    try:
        # kind opcional (evita listar todos os devices); set_switch já detecta PowerOn/Off
        if (kind or "").lower() == "ac":
            resp = tuya_client.set_ac_power(device_id, body.on)
        else:
            resp = tuya_client.set_switch(device_id, body.on, code=body.code)
        ok = bool(isinstance(resp, dict) and (resp.get("success") is True or "result" in resp))
        _log(f"SWITCH device={device_id} ok={ok} response={resp}")
        tuya_client.invalidate_devices_cache()
        return {"ok": ok, "response": resp}
    except Exception as e:
        _log(f"SWITCH device={device_id} FALHOU: {e}")
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/api/devices/{device_id}/ac/power")
def api_ac_power(device_id: str, body: AcPowerBody):
    _log(f"AC_POWER device={device_id} on={body.on}")
    try:
        resp = tuya_client.set_ac_power(device_id, body.on)
        ok = bool(isinstance(resp, dict) and (resp.get("success") is True or "result" in resp))
        _log(f"AC_POWER device={device_id} ok={ok} response={resp}")
        tuya_client.invalidate_devices_cache()
        return {"ok": ok, "response": resp}
    except Exception as e:
        _log(f"AC_POWER device={device_id} FALHOU: {e}")
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/api/devices/{device_id}/ac/temp")
def api_ac_temp(device_id: str, body: AcTempBody):
    _log(f"AC_TEMP device={device_id} temp={body.temp}")
    try:
        resp = tuya_client.set_ac_temp(device_id, body.temp)
        ok = bool(isinstance(resp, dict) and (resp.get("success") is True or "result" in resp))
        _log(f"AC_TEMP device={device_id} ok={ok} response={resp}")
        return {"ok": ok, "response": resp, "temp": body.temp}
    except Exception as e:
        _log(f"AC_TEMP device={device_id} FALHOU: {e}")
        raise HTTPException(status_code=502, detail=str(e)) from e
