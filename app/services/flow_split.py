"""Separação consumo (rede) × injeção (solar).

PREMISSA DO PROJETO (dados reais do medidor):
- Potência negativa e/ou corrente negativa = injeção de usina solar na rede
  (export). Positivo = consumo da rede (import).
- Métricas `power_*` / `current_*` líquidas permanecem; além delas gravamos
  `power_import_*`, `power_export_*`, `current_import_*`, `current_export_*`.
"""
from __future__ import annotations

from typing import Any


def apply_import_export_split(metrics: dict[str, Any]) -> dict[str, Any]:
    """Deriva import/export a partir do sinal de potência (preferencial) ou corrente."""
    for phase in ("l1", "l2", "l3"):
        p = metrics.get(f"power_{phase}")
        c = metrics.get(f"current_{phase}")
        if p is None and c is None:
            continue

        p_val = float(p) if p is not None else 0.0
        c_raw = float(c) if c is not None else 0.0
        c_mag = abs(c_raw)

        # Premissa: negativo = injeção (solar → rede)
        if p is not None:
            exporting = p_val < 0
        else:
            exporting = c_raw < 0

        metrics[f"power_import_{phase}"] = max(p_val, 0.0)
        metrics[f"power_export_{phase}"] = max(-p_val, 0.0)
        metrics[f"current_import_{phase}"] = c_mag if not exporting else 0.0
        metrics[f"current_export_{phase}"] = c_mag if exporting else 0.0

    if "power_total" in metrics:
        pt = float(metrics["power_total"])
        metrics["power_import_total"] = max(pt, 0.0)
        metrics["power_export_total"] = max(-pt, 0.0)

        has_phase = any(f"power_import_{p}" in metrics for p in ("l1", "l2", "l3"))
        if has_phase:
            metrics["current_import_total"] = sum(
                float(metrics.get(f"current_import_{p}", 0.0)) for p in ("l1", "l2", "l3")
            )
            metrics["current_export_total"] = sum(
                float(metrics.get(f"current_export_{p}", 0.0)) for p in ("l1", "l2", "l3")
            )
        elif "current_total" in metrics:
            ct = abs(float(metrics["current_total"]))
            metrics["current_import_total"] = ct if pt >= 0 else 0.0
            metrics["current_export_total"] = ct if pt < 0 else 0.0

    return metrics


def is_cumulative_energy_metric(metric: str) -> bool:
    """Métricas acumuladas de energia (delta no período = energia do período)."""
    if metric in ("energy_wh", "energy_kwh"):
        return True
    prefixes = (
        "energy_imported_",
        "energy_exported_",
        "energy_import_",
        "energy_export_",
    )
    return any(metric.startswith(p) for p in prefixes)
