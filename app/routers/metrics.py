from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..core.db import get_db
from .. import crud, schemas, models
import pandas as pd
from datetime import datetime, timedelta
from ..services.analytics import compute_summary, linear_regression, six_sigma_params


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
def list_metrics(device_id: int, metric: str | None = Query(default=None), limit: int = 500, db: Session = Depends(get_db)):
    rows = crud.list_measurements(db, device_id=device_id, metric=metric, limit=limit)
    # Retornar como dict diretamente para evitar problemas de serialização JSON
    return [
        {
            "id": r.id,
            "device_id": r.device_id,
            "timestamp": r.timestamp.isoformat(),
            "metric": r.metric,
            "value": r.value,
            "extra": r.extra if isinstance(r.extra, dict) else {}
        }
        for r in rows
    ]


@router.get("/timerange")
def metrics_timerange(
    device_id: int,
    metric: str,
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
    period: str = Query(default="1h"),  # 1h, 6h, 1d, 1w, 1m, 1y
    db: Session = Depends(get_db)
):
    """Retorna métricas agregadas por período de tempo."""
    # Calcular datas baseado no período se não fornecidas
    if not end_date:
        end = datetime.utcnow()
    else:
        end = datetime.fromisoformat(end_date)

    if not start_date:
        period_map = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "1d": timedelta(days=1),
            "1w": timedelta(weeks=1),
            "1m": timedelta(days=30),
            "1y": timedelta(days=365)
        }
        start = end - period_map.get(period, timedelta(days=1))
    else:
        start = datetime.fromisoformat(start_date)

    # Buscar measurements no intervalo
    q = db.query(models.Measurement).filter(
        models.Measurement.device_id == device_id,
        models.Measurement.metric == metric,
        models.Measurement.timestamp >= start,
        models.Measurement.timestamp <= end
    ).order_by(models.Measurement.timestamp.asc())

    rows = q.all()

    if not rows:
        return {"data": [], "period": period, "start": start.isoformat(), "end": end.isoformat()}

    # Converter para DataFrame para agregação
    df = pd.DataFrame([
        {"timestamp": r.timestamp, "value": r.value}
        for r in rows
    ])

    # Determinar frequência de resample baseado no período
    resample_freq = {
        "1h": "1min",
        "6h": "5min",
        "1d": "15min",
        "1w": "1H",
        "1m": "6H",
        "1y": "1D"
    }.get(period, "1H")

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Agregar dados
    aggregated = df.resample(resample_freq).agg({
        'value': ['mean', 'min', 'max', 'count']
    }).reset_index()

    aggregated.columns = ['timestamp', 'mean', 'min', 'max', 'count']

    result = []
    for _, row in aggregated.iterrows():
        if row['count'] > 0:
            result.append({
                "timestamp": row['timestamp'].isoformat(),
                "mean": float(row['mean']),
                "min": float(row['min']),
                "max": float(row['max']),
                "count": int(row['count'])
            })

    return {
        "data": result,
        "period": period,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "resample_freq": resample_freq
    }


@router.get("/demand")
def demand_analysis(
    device_id: int,
    period: str = Query(default="1d"),  # 1d, 1w, 1m
    metric: str = Query(default="power"),  # power, power_total, power_l1, etc
    db: Session = Depends(get_db)
):
    """Análise de demanda: pico, fora-ponta, média diária."""
    end = datetime.utcnow()
    period_map = {
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1m": timedelta(days=30)
    }
    start = end - period_map.get(period, timedelta(days=1))

    # Buscar potência no período (aceita power, power_total, power_l1, etc)
    q = db.query(models.Measurement).filter(
        models.Measurement.device_id == device_id,
        models.Measurement.metric == metric,
        models.Measurement.timestamp >= start,
        models.Measurement.timestamp <= end
    ).order_by(models.Measurement.timestamp.asc())

    rows = q.all()
    if not rows:
        return {"error": f"Sem dados de {metric} no período"}

    df = pd.DataFrame([
        {"timestamp": r.timestamp, "power": r.value}
        for r in rows
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour

    # Classificação horária (pode ajustar conforme tarifa local)
    # Ponta: 18h-21h (horário de pico)
    # Fora-ponta: resto do dia
    df['tariff'] = df['hour'].apply(lambda h: 'peak' if 18 <= h < 21 else 'off_peak')

    # Cálculo de demandas
    peak_data = df[df['tariff'] == 'peak']
    off_peak_data = df[df['tariff'] == 'off_peak']

    result = {
        "period": period,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "peak": {
            "max": float(peak_data['power'].max()) if len(peak_data) > 0 else 0,
            "mean": float(peak_data['power'].mean()) if len(peak_data) > 0 else 0,
            "samples": len(peak_data)
        },
        "off_peak": {
            "max": float(off_peak_data['power'].max()) if len(off_peak_data) > 0 else 0,
            "mean": float(off_peak_data['power'].mean()) if len(off_peak_data) > 0 else 0,
            "samples": len(off_peak_data)
        },
        "overall": {
            "max": float(df['power'].max()),
            "mean": float(df['power'].mean()),
            "min": float(df['power'].min())
        },
        "hourly_average": []
    }

    # Média por hora do dia
    hourly = df.groupby('hour')['power'].mean().reset_index()
    for _, row in hourly.iterrows():
        result["hourly_average"].append({
            "hour": int(row['hour']),
            "power": float(row['power'])
        })

    return result


@router.get("/summary")
def metrics_summary(device_id: int, metric: str, limit: int = 1000, db: Session = Depends(get_db)):
    rows = crud.list_measurements(db, device_id=device_id, metric=metric, limit=limit)
    s = pd.Series([r.value for r in rows][::-1])  # ordem cronológica
    summary = compute_summary(s)
    six = six_sigma_params(s)
    return {"summary": summary.__dict__, "six_sigma": six}


@router.get("/linreg")
def metrics_linreg(device_id: int, x_metric: str, y_metric: str, limit: int = 1000, db: Session = Depends(get_db)):
    xs = crud.list_measurements(db, device_id=device_id, metric=x_metric, limit=limit)
    ys = crud.list_measurements(db, device_id=device_id, metric=y_metric, limit=limit)
    # alinhar por ordem temporal (assumindo mesmo sampling)
    xs_vals = [r.value for r in xs][::-1]
    ys_vals = [r.value for r in ys][::-1]
    n = min(len(xs_vals), len(ys_vals))
    res = linear_regression(pd.Series(xs_vals[-n:]), pd.Series(ys_vals[-n:])) if n > 0 else {"slope":0.0,"intercept":0.0,"r2":0.0}
    return res


@router.get("/calculated")
def calculated_metrics(device_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """Retorna métricas calculadas baseadas nas entradas do PZEM-004T."""
    voltage_data = crud.list_measurements(db, device_id=device_id, metric="voltage", limit=limit)
    current_data = crud.list_measurements(db, device_id=device_id, metric="current", limit=limit)
    power_data = crud.list_measurements(db, device_id=device_id, metric="power", limit=limit)
    energy_data = crud.list_measurements(db, device_id=device_id, metric="energy_wh", limit=limit)

    if not voltage_data or not current_data or not power_data:
        return {"error": "Dados insuficientes"}

    # Últimas leituras
    latest_voltage = voltage_data[0].value if voltage_data else 0.0
    latest_current = current_data[0].value if current_data else 0.0
    latest_power = power_data[0].value if power_data else 0.0
    latest_energy_wh = energy_data[0].value if energy_data else 0.0

    # Cálculos
    apparent_power = latest_voltage * latest_current  # VA
    power_factor = (latest_power / apparent_power) if apparent_power > 0 else 0.0
    energy_kwh = latest_energy_wh / 1000.0

    # Custo estimado (R$ 0,65/kWh - ajustar conforme tarifa)
    cost_per_kwh = 0.65
    estimated_cost = energy_kwh * cost_per_kwh

    # Médias das últimas leituras
    avg_voltage = sum(r.value for r in voltage_data) / len(voltage_data) if voltage_data else 0.0
    avg_current = sum(r.value for r in current_data) / len(current_data) if current_data else 0.0
    avg_power = sum(r.value for r in power_data) / len(power_data) if power_data else 0.0

    return {
        "latest": {
            "voltage": latest_voltage,
            "current": latest_current,
            "power": latest_power,
            "energy_wh": latest_energy_wh,
            "energy_kwh": energy_kwh,
            "apparent_power_va": round(apparent_power, 2),
            "power_factor": round(power_factor, 3),
            "estimated_cost_brl": round(estimated_cost, 2)
        },
        "averages": {
            "voltage": round(avg_voltage, 2),
            "current": round(avg_current, 3),
            "power": round(avg_power, 2)
        }
    }

