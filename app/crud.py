from __future__ import annotations
from sqlalchemy.orm import Session
from . import models, schemas


# Clients
def create_client(db: Session, data: schemas.ClientCreate) -> models.Client:
    obj = models.Client(name=data.name, external_id=data.external_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_clients(db: Session) -> list[models.Client]:
    return db.query(models.Client).all()


# Devices
def create_device(db: Session, data: schemas.DeviceCreate) -> models.Device:
    obj = models.Device(
        client_id=data.client_id,
        name=data.name,
        device_type=data.device_type,
        active=data.active,
        config=data.config,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_devices(db: Session, client_id: int | None = None) -> list[models.Device]:
    q = db.query(models.Device)
    if client_id is not None:
        q = q.filter(models.Device.client_id == client_id)
    return q.all()


def get_device(db: Session, device_id: int) -> models.Device | None:
    return db.query(models.Device).filter(models.Device.id == device_id).first()


def delete_device(db: Session, device_id: int) -> bool:
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device:
        db.delete(device)
        db.commit()
        return True
    return False


def update_device(db: Session, device_id: int, data: dict) -> models.Device | None:
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device:
        for key, value in data.items():
            setattr(device, key, value)
        db.commit()
        db.refresh(device)
        return device
    return None


# Measurements
def create_measurement(db: Session, data: schemas.MeasurementCreate) -> models.Measurement:
    fields: dict = {
        "device_id": data.device_id,
        "metric": data.metric,
        "value": data.value,
        "extra": data.extra,
    }
    if data.timestamp is not None:
        fields["timestamp"] = data.timestamp
    obj = models.Measurement(**fields)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_measurements(
    db: Session,
    device_id: int,
    metric: str | None = None,
    limit: int = 1000,
    since=None,
) -> list[models.Measurement]:
    q = db.query(models.Measurement).filter(models.Measurement.device_id == device_id)
    if metric:
        q = q.filter(models.Measurement.metric == metric)
    if since is not None:
        q = q.filter(models.Measurement.timestamp >= since)
    return q.order_by(models.Measurement.timestamp.desc()).limit(limit).all()


# Alarm rules and events
def create_alarm_rule(db: Session, data: schemas.AlarmRuleCreate) -> models.AlarmRuleModel:
    obj = models.AlarmRuleModel(
        client_id=data.client_id,
        device_id=data.device_id,
        name=data.name,
        metric=data.metric,
        operator=data.operator,
        threshold=data.threshold,
        enabled=data.enabled,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_alarm_rules(db: Session, client_id: int | None = None, device_id: int | None = None):
    q = db.query(models.AlarmRuleModel)
    if client_id is not None:
        q = q.filter(models.AlarmRuleModel.client_id == client_id)
    if device_id is not None:
        q = q.filter(models.AlarmRuleModel.device_id == device_id)
    return q.all()


def create_alarm_event(
    db: Session,
    rule_id: int,
    device_id: int,
    metric: str,
    value: float,
    details: dict | None = None,
):
    obj = models.AlarmEvent(
        rule_id=rule_id,
        device_id=device_id,
        metric=metric,
        value=value,
        details=details,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

