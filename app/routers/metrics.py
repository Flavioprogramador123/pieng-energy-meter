from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..core.db import get_db
from .. import crud, schemas, models
import pandas as pd
from datetime import datetime, timedelta
from ..services.analytics import compute_summary, linear_regression, six_sigma_params
from ..services.flow_split import is_cumulative_energy_metric


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
def list_metrics(
    device_id: int,
    metric: str | None = Query(default=None),
    limit: int = 500,
    period: str | None = Query(default=None),  # 1d, 1w, 1m
    end: str | None = Query(default=None),  # âncora ISO opcional p/ navegar dias/semanas/meses passados
    db: Session = Depends(get_db),
):
    since = None
    until = None
    if period:
        period_map = {
            "1d": timedelta(days=1),
            "1w": timedelta(weeks=1),
            "1m": timedelta(days=30),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
        }
        delta = period_map.get(period)
        if delta:
            end_dt = datetime.fromisoformat(end) if end else datetime.utcnow()
            since = end_dt - delta
            until = end_dt if end else None
            # Para períodos longos, permitir mais pontos
            if period in ("1w", "1m") and limit < 5000:
                limit = 5000

    rows = crud.list_measurements(db, device_id=device_id, metric=metric, limit=limit, since=since, until=until)
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


@router.get("/available")
def available_metrics(device_id: int, period: str | None = Query(default="1w"), db: Session = Depends(get_db)):
    """Lista métricas com dados reais para o device (opcionalmente no período)."""
    since = None
    if period:
        period_map = {
            "1d": timedelta(days=1),
            "1w": timedelta(weeks=1),
            "1m": timedelta(days=30),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
        }
        delta = period_map.get(period)
        if delta:
            since = datetime.utcnow() - delta

    q = db.query(
        models.Measurement.metric,
        func.count(models.Measurement.id),
        func.max(models.Measurement.timestamp),
    ).filter(models.Measurement.device_id == device_id)

    if since is not None:
        q = q.filter(models.Measurement.timestamp >= since)

    rows = q.group_by(models.Measurement.metric).order_by(models.Measurement.metric.asc()).all()
    return [
        {
            "metric": metric,
            "count": int(count),
            "last_timestamp": last_ts.isoformat() if last_ts else None,
        }
        for metric, count, last_ts in rows
    ]


@router.get("/available")
def metrics_available(
    device_id: int,
    period: str = Query(default="1d"),
    db: Session = Depends(get_db)
):
    """Lista as métricas com dados REAIS para o dispositivo no período (para popular o seletor)."""
    period_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1m": timedelta(days=30),
        "1y": timedelta(days=365)
    }
    start = datetime.utcnow() - period_map.get(period, timedelta(days=1))

    rows = (
        db.query(models.Measurement.metric, func.count(models.Measurement.id))
        .filter(models.Measurement.device_id == device_id, models.Measurement.timestamp >= start)
        .group_by(models.Measurement.metric)
        .order_by(func.count(models.Measurement.id).desc())
        .all()
    )

    return [{"metric": metric, "count": count} for metric, count in rows]


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
    six = six_sigma_params(s, metric=metric)
    return {"summary": summary.__dict__, "six_sigma": six}


@router.get("/period_summary")
def metrics_period_summary(
    device_id: int,
    metric: str,
    period: str = Query(default="1d"),
    db: Session = Depends(get_db)
):
    """
    Estatísticas do período selecionado (dia/semana/mês) comparadas com o
    período anterior equivalente (mesma duração, imediatamente antes).
    Também retorna Cpk (real, se a métrica tiver limite de especificação
    conhecido - ver SPEC_LIMITS - ou auto-referenciado caso contrário).
    """
    period_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1m": timedelta(days=30),
        "1y": timedelta(days=365)
    }
    duration = period_map.get(period, timedelta(days=1))
    now = datetime.utcnow()

    def window_stats(start: datetime, end: datetime):
        rows = db.query(models.Measurement.value).filter(
            models.Measurement.device_id == device_id,
            models.Measurement.metric == metric,
            models.Measurement.timestamp >= start,
            models.Measurement.timestamp < end,
        ).all()
        values = pd.Series([r[0] for r in rows])
        summary = compute_summary(values)
        six = six_sigma_params(values, metric=metric)

        is_cumulative = is_cumulative_energy_metric(metric)
        consumption = None
        if is_cumulative and len(values) >= 2:
            consumption = float(values.max() - values.min())

        return {
            "summary": summary.__dict__,
            "six_sigma": six,
            "consumption": consumption,
        }

    current = window_stats(now - duration, now)
    previous = window_stats(now - 2 * duration, now - duration)

    delta_pct = None
    cur_mean = current["summary"]["mean"]
    prev_mean = previous["summary"]["mean"]
    if previous["summary"]["count"] > 0 and prev_mean:
        delta_pct = ((cur_mean - prev_mean) / abs(prev_mean)) * 100

    return {
        "period": period,
        "metric": metric,
        "current": current,
        "previous": previous,
        "delta_pct": delta_pct,
    }


@router.get("/solar_summary")
def solar_summary(
    device_id: int,
    period: str = Query(default="1d"),
    db: Session = Depends(get_db),
):
    """
    Resumo Rede × Solar no período (dados REAIS).

    Premissa: potência/corrente negativas = injeção solar (export).
    - Energia injetada/consumida: delta dos acumuladores energy_exported_* /
      energy_imported_* quando existirem; senão integração de power_export/import.
    - Pico de injeção: máximo de power_export_total (W) + timestamp.
    """
    period_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1m": timedelta(days=30),
    }
    end = datetime.utcnow()
    start = end - period_map.get(period, timedelta(days=1))

    def series(metric: str):
        rows = (
            db.query(models.Measurement)
            .filter(
                models.Measurement.device_id == device_id,
                models.Measurement.metric == metric,
                models.Measurement.timestamp >= start,
                models.Measurement.timestamp <= end,
            )
            .order_by(models.Measurement.timestamp.asc())
            .all()
        )
        return rows

    def energy_delta_kwh(metric: str) -> float | None:
        rows = series(metric)
        if len(rows) < 2:
            return None
        # acumulador: último − primeiro (mais robusto que max−min se houver reset)
        delta = float(rows[-1].value) - float(rows[0].value)
        if delta < 0:
            # possível reset do medidor — usa max−min como fallback
            vals = [float(r.value) for r in rows]
            delta = max(vals) - min(vals)
        return delta

    def integrate_power_kwh(metric: str) -> float | None:
        rows = series(metric)
        if len(rows) < 2:
            return None
        wh = 0.0
        for a, b in zip(rows, rows[1:]):
            dt_h = (b.timestamp - a.timestamp).total_seconds() / 3600.0
            if dt_h <= 0:
                continue
            # potência média entre amostras (W) → Wh
            wh += ((float(a.value) + float(b.value)) / 2.0) * dt_h
        return wh / 1000.0

    def peak_power(metric: str) -> dict | None:
        rows = series(metric)
        if not rows:
            return None
        best = max(rows, key=lambda r: float(r.value))
        return {
            "watts": float(best.value),
            "kw": float(best.value) / 1000.0,
            "timestamp": best.timestamp.isoformat(),
            "metric": metric,
            "samples": len(rows),
        }

    # Preferência: acumuladores do hardware (Tuya reverse/forward)
    injected = energy_delta_kwh("energy_exported_total")
    consumed = energy_delta_kwh("energy_imported_total")
    injected_source = "energy_exported_total" if injected is not None else None
    consumed_source = "energy_imported_total" if consumed is not None else None

    if injected is None:
        injected = integrate_power_kwh("power_export_total")
        if injected is not None:
            injected_source = "power_export_total_integrated"
    if consumed is None:
        consumed = integrate_power_kwh("power_import_total")
        if consumed is not None:
            consumed_source = "power_import_total_integrated"

    # Se ainda não há split gravado, tenta a partir de power_total líquido
    # (amostras negativas = injeção) — só quando não existirem métricas export.
    if injected is None and consumed is None:
        rows = series("power_total")
        if len(rows) >= 2:
            wh_exp = 0.0
            wh_imp = 0.0
            for a, b in zip(rows, rows[1:]):
                dt_h = (b.timestamp - a.timestamp).total_seconds() / 3600.0
                if dt_h <= 0:
                    continue
                pa, pb = float(a.value), float(b.value)
                mid = (pa + pb) / 2.0
                if mid < 0:
                    wh_exp += abs(mid) * dt_h
                else:
                    wh_imp += mid * dt_h
            injected = wh_exp / 1000.0
            consumed = wh_imp / 1000.0
            injected_source = "power_total_signed_integrated"
            consumed_source = "power_total_signed_integrated"

    peak_inj = peak_power("power_export_total")
    peak_grid = peak_power("power_import_total")

    # Fallback de pico via power_total (mais negativo = maior injeção)
    if peak_inj is None:
        rows = series("power_total")
        if rows:
            best = min(rows, key=lambda r: float(r.value))
            if float(best.value) < 0:
                peak_inj = {
                    "watts": abs(float(best.value)),
                    "kw": abs(float(best.value)) / 1000.0,
                    "timestamp": best.timestamp.isoformat(),
                    "metric": "power_total_abs_min",
                    "samples": len(rows),
                }
    if peak_grid is None:
        rows = series("power_total")
        if rows:
            best = max(rows, key=lambda r: float(r.value))
            if float(best.value) > 0:
                peak_grid = {
                    "watts": float(best.value),
                    "kw": float(best.value) / 1000.0,
                    "timestamp": best.timestamp.isoformat(),
                    "metric": "power_total_max",
                    "samples": len(rows),
                }

    phases = {}
    for ph in ("l1", "l2", "l3"):
        p = peak_power(f"power_export_{ph}")
        if p:
            phases[ph] = p

    has_data = any(v is not None for v in (injected, consumed, peak_inj, peak_grid))

    return {
        "ok": has_data,
        "premise": "Corrente/potência negativas = injeção solar (export para a rede).",
        "period": period,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "energy_injected_kwh": injected,
        "energy_consumed_kwh": consumed,
        "energy_net_kwh": (
            None
            if injected is None or consumed is None
            else float(consumed) - float(injected)
        ),
        "energy_injected_source": injected_source,
        "energy_consumed_source": consumed_source,
        "peak_injection": peak_inj,
        "peak_grid_draw": peak_grid,
        "peak_injection_by_phase": phases,
    }


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

