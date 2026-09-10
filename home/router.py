"""Rotas API + página do módulo HOME."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

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


@router.get("/api/devices")
def api_devices(include_other: bool = False):
    try:
        devices = tuya_client.list_home_devices(include_other=include_other)
        return {"ok": True, "count": len(devices), "devices": devices}
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
