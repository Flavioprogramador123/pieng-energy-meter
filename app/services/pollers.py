from __future__ import annotations
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..core.db import SessionLocal
from .. import crud, schemas, models
from ..connectors.modbus import ModbusRTUClient, ModbusTCPClient
from ..connectors.pzem004t import read_pzem004t_metrics
from ..connectors.eastron_sdm630 import read_sdm630_metrics
from . import firebase_sync

# Configurar logger de auditoria
logger = logging.getLogger("pieng.audit")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler("data/audit.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)


def poll_modbus_devices():
    """Poller para dispositivos Modbus RTU (serial)."""
    db: Session = SessionLocal()
    total_points = 0
    try:
        devices = crud.list_devices(db)
        for d in devices:
            if d.device_type != "modbus" or not d.active:
                continue
            cfg = d.config or {}
            try:
                saved_metrics: dict = {}
                with ModbusRTUClient(
                    port=cfg.get("port", "COM3"),
                    slave_id=int(cfg.get("slave_id", 1)),
                    baudrate=int(cfg.get("baudrate", 9600)),
                    timeout=float(cfg.get("timeout", 0.5)),
                ) as client:
                    if cfg.get("driver") == "pzem004t":
                        values = read_pzem004t_metrics(client, base_address=int(cfg.get("base", 0)))
                        for k in ["voltage", "current", "power", "energy_wh"]:
                            if k in values:
                                crud.create_measurement(db, schemas.MeasurementCreate(device_id=d.id, metric=k, value=float(values[k])))
                                saved_metrics[k] = float(values[k])
                    elif cfg.get("driver") == "sdm630":
                        values = read_sdm630_metrics(client, base_address=int(cfg.get("base", 0)))
                        for k, v in values.items():
                            if not k.startswith("_") and isinstance(v, (int, float)):
                                crud.create_measurement(db, schemas.MeasurementCreate(device_id=d.id, metric=k, value=float(v)))
                                saved_metrics[k] = float(v)
                    else:
                        # leitura genérica de regs
                        regs = client.read_input_registers(address=int(cfg.get("base", 0)), count=int(cfg.get("count", 4)))
                        metrics = cfg.get("metrics", ["voltage", "current", "power", "energy_wh"])
                        for idx, val in enumerate(regs):
                            metric = metrics[idx] if idx < len(metrics) else f"reg_{idx}"
                            crud.create_measurement(db, schemas.MeasurementCreate(device_id=d.id, metric=metric, value=float(val)))
                            saved_metrics[metric] = float(val)
                firebase_sync.push_reading(d.id, d.name, "modbus", saved_metrics)
                total_points += len(saved_metrics)
            except Exception as e:
                logger.error(f"POLL_RTU_ERROR | device_id={d.id} | name={d.name} | error={str(e)}")
                print(f"Erro ao ler dispositivo Modbus RTU {d.id} ({d.name}): {e}")
                continue
        db.commit()
        if total_points > 0:
            from .collector_stats import note_poll_success
            note_poll_success(points=total_points)
    finally:
        db.close()


def poll_modbus_tcp_devices():
    """Poller para dispositivos Modbus TCP (Elfin-EW11A, conversores RS485-WiFi, etc)."""
    db: Session = SessionLocal()
    total_points = 0
    try:
        devices = crud.list_devices(db)
        for d in devices:
            if d.device_type != "modbus_tcp" or not d.active:
                continue
            cfg = d.config or {}
            try:
                saved_metrics: dict = {}
                with ModbusTCPClient(
                    host=cfg.get("host", "192.168.1.100"),
                    port=int(cfg.get("port", 502)),
                    slave_id=int(cfg.get("slave_id", 1)),
                    timeout=float(cfg.get("timeout", 3.0)),
                ) as client:
                    if cfg.get("driver") == "pzem004t":
                        values = read_pzem004t_metrics(client, base_address=int(cfg.get("base", 0)))
                        logger.info(f"POLL_TCP | device_id={d.id} | driver=pzem004t | host={cfg.get('host')}:{cfg.get('port')} | metrics={len(values)}")
                        for k in ["voltage", "current", "power", "energy_wh"]:
                            if k in values:
                                crud.create_measurement(db, schemas.MeasurementCreate(device_id=d.id, metric=k, value=float(values[k])))
                                saved_metrics[k] = float(values[k])
                    elif cfg.get("driver") == "sdm630":
                        values = read_sdm630_metrics(client, base_address=int(cfg.get("base", 0)))
                        metrics_count = sum(1 for k in values.keys() if not k.startswith("_"))
                        logger.info(f"POLL_TCP | device_id={d.id} | driver=sdm630 | host={cfg.get('host')}:{cfg.get('port')} | metrics={metrics_count}")
                        for k, v in values.items():
                            if not k.startswith("_") and isinstance(v, (int, float)):
                                crud.create_measurement(db, schemas.MeasurementCreate(device_id=d.id, metric=k, value=float(v)))
                                saved_metrics[k] = float(v)
                    else:
                        # leitura genérica de regs
                        regs = client.read_input_registers(address=int(cfg.get("base", 0)), count=int(cfg.get("count", 4)))
                        logger.info(f"POLL_TCP | device_id={d.id} | driver=generic | host={cfg.get('host')}:{cfg.get('port')} | registers={len(regs)}")
                        metrics = cfg.get("metrics", ["voltage", "current", "power", "energy_wh"])
                        for idx, val in enumerate(regs):
                            metric = metrics[idx] if idx < len(metrics) else f"reg_{idx}"
                            crud.create_measurement(db, schemas.MeasurementCreate(device_id=d.id, metric=metric, value=float(val)))
                            saved_metrics[metric] = float(val)
                firebase_sync.push_reading(d.id, d.name, "modbus_tcp", saved_metrics)
                total_points += len(saved_metrics)
            except Exception as e:
                logger.error(f"POLL_TCP_ERROR | device_id={d.id} | name={d.name} | host={cfg.get('host')} | error={str(e)}")
                print(f"Erro ao ler dispositivo Modbus TCP {d.id} ({d.name}): {e}")
                continue
        db.commit()
        if total_points > 0:
            from .collector_stats import note_poll_success
            note_poll_success(points=total_points)
    finally:
        db.close()

