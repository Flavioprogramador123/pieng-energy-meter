from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..core.db import get_db
from .. import crud


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    devices = crud.list_devices(db)
    clients = crud.list_clients(db)
    return request.app.state.templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "devices": devices, "clients": clients},
    )


@router.get("/analytics", response_class=HTMLResponse)
def analytics(request: Request, db: Session = Depends(get_db)):
    devices = crud.list_devices(db)
    return request.app.state.templates.TemplateResponse(
        "analytics.html",
        {"request": request, "devices": devices},
    )


@router.get("/setup", response_class=HTMLResponse)
def device_setup(request: Request):
    """Interface visual para cadastro de dispositivos"""
    return request.app.state.templates.TemplateResponse(
        "device_setup.html",
        {"request": request},
    )



