from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class StatsSummary:
    count: int
    mean: float
    std: float
    min: float
    max: float


def compute_summary(series: pd.Series) -> StatsSummary:
    clean = series.dropna()
    if clean.empty:
        return StatsSummary(count=0, mean=0.0, std=0.0, min=0.0, max=0.0)
    
    mean_val = clean.mean()
    std_val = clean.std(ddof=1) if clean.count() > 1 else 0.0
    min_val = clean.min()
    max_val = clean.max()
    
    # Verificar se os valores são válidos (não NaN)
    mean_val = 0.0 if np.isnan(mean_val) else float(mean_val)
    std_val = 0.0 if np.isnan(std_val) else float(std_val)
    min_val = 0.0 if np.isnan(min_val) else float(min_val)
    max_val = 0.0 if np.isnan(max_val) else float(max_val)
    
    return StatsSummary(
        count=int(clean.count()),
        mean=mean_val,
        std=std_val,
        min=min_val,
        max=max_val,
    )


def linear_regression(x: pd.Series, y: pd.Series) -> dict[str, float]:
    mask = ~(x.isna() | y.isna())
    x_vals = x[mask].to_numpy()
    y_vals = y[mask].to_numpy()
    if x_vals.size == 0:
        return {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
    # Ajuste linear simples via polyfit
    slope, intercept = np.polyfit(x_vals, y_vals, 1)
    y_pred = slope * x_vals + intercept
    ss_res = float(np.sum((y_vals - y_pred) ** 2))
    ss_tot = float(np.sum((y_vals - np.mean(y_vals)) ** 2))
    r2 = 0.0 if ss_tot == 0.0 else 1.0 - (ss_res / ss_tot)
    return {"slope": float(slope), "intercept": float(intercept), "r2": float(r2)}


# Limites de especificação (LSL/USL) para métricas elétricas com padrão definido
# (PRODIST Módulo 8 - faixa "adequada" de tensão em 220V nominal; frequência e
# fator de potência conforme referências usuais de qualidade de energia).
# Sem limite conhecido, o Cpk cai para o modo "auto-referenciado" (ver abaixo).
SPEC_LIMITS: dict[str, tuple[float, float]] = {
    "voltage": (209.0, 231.0),
    "voltage_l1": (209.0, 231.0),
    "voltage_l2": (209.0, 231.0),
    "voltage_l3": (209.0, 231.0),
    "voltage_avg": (209.0, 231.0),
    "frequency": (58.8, 61.2),
    "power_factor": (0.92, 1.0),
}


def six_sigma_params(series: pd.Series, metric: str | None = None) -> dict[str, float | bool | str]:
    clean = series.dropna()
    if clean.empty:
        return {"mean": 0.0, "std": 0.0, "cpk": 0.0, "lsl": None, "usl": None, "cpk_real": False}

    mean_val = clean.mean()
    std_val = clean.std(ddof=1) if clean.count() > 1 else 0.0

    # Verificar se os valores são válidos (não NaN)
    mean_val = 0.0 if np.isnan(mean_val) else float(mean_val)
    std_val = 0.0 if np.isnan(std_val) else float(std_val)

    spec = SPEC_LIMITS.get(metric) if metric else None

    if std_val == 0.0:
        return {"mean": mean_val, "std": std_val, "cpk": 0.0, "lsl": spec[0] if spec else None,
                "usl": spec[1] if spec else None, "cpk_real": spec is not None}

    if spec:
        lsl, usl = spec
        cpk = min((usl - mean_val) / (3 * std_val), (mean_val - lsl) / (3 * std_val))
        cpk_real = True
    else:
        # Sem especificação conhecida: usa média +/- 3 sigma como referência
        # (fica sempre próximo de 1.0 - serve só como indicador de dispersão relativa,
        # não é um Cpk de verdade; sinalizado via cpk_real=False para a UI avisar).
        usl = mean_val + 3 * std_val
        lsl = mean_val - 3 * std_val
        cpk = min((usl - mean_val) / (3 * std_val), (mean_val - lsl) / (3 * std_val))
        cpk_real = False

    cpk = 0.0 if np.isnan(cpk) else float(cpk)

    return {
        "mean": mean_val, "std": std_val, "cpk": cpk,
        "lsl": lsl if cpk_real else None, "usl": usl if cpk_real else None,
        "cpk_real": cpk_real,
    }

