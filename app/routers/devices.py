from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..core.db import get_db
from .. import crud, schemas, models
from ..services.tuya_discover import discover_tuya_devices, role_label


router = APIRouter(prefix="/devices", tags=["devices"])


class TuyaEnrollRequest(BaseModel):
    tuya_device_id: str
    name: str | None = None
    role: str = Field(default="energy_meter")
    client_id: int | None = None
    client_name: str | None = "Casa"
    category: str | None = None
    product_name: str | None = None
    active: bool = True


@router.get("")
def list_devices(client_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    return [schemas.DeviceRead.model_validate(d) for d in crud.list_devices(db, client_id)]


@router.get("/tuya/discover")
def tuya_discover(db: Session = Depends(get_db)):
    """Lista devices do projeto Tuya Cloud e marca os ainda não cadastrados."""
    return discover_tuya_devices(db)


@router.post("/tuya/enroll")
def tuya_enroll(payload: TuyaEnrollRequest, db: Session = Depends(get_db)):
    """Inclui um device Tuya da nuvem no projeto com 1 clique (mesmo access_id)."""
    tid = payload.tuya_device_id.strip()
    if not tid:
        raise HTTPException(status_code=400, detail="tuya_device_id obrigatório")

    # já cadastrado?
    for d in crud.list_devices(db):
        if d.device_type != "tuya":
            continue
        cfg = d.config or {}
        if str(cfg.get("device_id") or cfg.get("tuya_device_id") or "") == tid:
            return {
                "ok": True,
                "already_existed": True,
                "device": schemas.DeviceRead.model_validate(d),
                "message": "Dispositivo já estava no projeto",
            }

    client_id = payload.client_id
    if client_id is None:
        clients = crud.list_clients(db)
        if clients:
            client_id = clients[0].id
        else:
            c = crud.create_client(
                db, schemas.ClientCreate(name=payload.client_name or "Casa")
            )
            client_id = c.id

    name = payload.name or f"Tuya {tid[:8]}"
    role = payload.role or "energy_meter"
    config = {
        "device_id": tid,
        "category": payload.category,
        "product_name": payload.product_name,
        "role": role,
        "role_label": role_label(role),
        "site": "home" if role == "inverter_output" else "office_or_home",
    }

    device = crud.create_device(
        db,
        schemas.DeviceCreate(
            client_id=client_id,
            name=name,
            device_type="tuya",
            active=payload.active,
            config=config,
        ),
    )
    return {
        "ok": True,
        "already_existed": False,
        "device": schemas.DeviceRead.model_validate(device),
        "message": f"Incluído como {role_label(role)}",
    }


@router.post("")
def create_device(payload: schemas.DeviceCreate, db: Session = Depends(get_db)):
    obj = crud.create_device(db, payload)
    return schemas.DeviceRead.model_validate(obj)


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    success = crud.delete_device(db, device_id)
    return {"success": success}


@router.patch("/{device_id}")
def update_device(device_id: int, payload: dict, db: Session = Depends(get_db)):
    device = crud.update_device(db, device_id, payload)
    if device:
        return schemas.DeviceRead.model_validate(device)
    return {"error": "Device not found"}

