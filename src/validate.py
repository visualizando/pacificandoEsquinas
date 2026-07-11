"""Validación híbrida (sección 7 del spec).

Reporta la correlación Spearman entre el índice compuesto y los siniestros
reales, y por separado la correlación del índice **geométrico puro** (sin el
eje crash_history) contra esos mismos siniestros — esa segunda métrica es la
que blinda el proyecto: muestra que la geometría predice la siniestralidad en
vez de asumirla. Si no hay dataset de siniestros en el scope, se reporta
`status: "skipped"` con el motivo, en vez de fallar.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

import scoring
from config import Config
from geo_utils import AxisResult
from ingest import IngestResult

GEOMETRY_AXES = {
    "crossing_length", "n_branches", "acute_angle", "roadway_width", "no_refuge", "speed_limit",
}


def _geometric_only_index(geometry: AxisResult, config: Config) -> pd.Series:
    flat_weights = config.flat_weights()
    available = [
        axis for axis in GEOMETRY_AXES
        if axis in geometry.values.columns and geometry.values[axis].notna().any()
    ]
    if not available:
        return pd.Series(dtype="float64")
    raw = pd.Series(0.0, index=geometry.values.index)
    for axis in available:
        series = geometry.values[axis]
        method = scoring.resolve_axis_method(axis, series, config)
        normed = scoring.normalize_series(series, method)
        raw = raw + normed.fillna(0.0) * flat_weights.get(axis, 0.0)
    return scoring.normalize_series(raw, config.normalization)


def run_validation(
    scoring_result: scoring.ScoringResult,
    geometry: AxisResult,
    ingest: IngestResult,
    config: Config,
) -> dict:
    if not ingest.is_available("siniestros"):
        return {
            "status": "skipped",
            "reason": ingest.unavailable.get(
                "siniestros", "no hay dataset de siniestros viales en data/raw/ para este scope"
            ),
            "axes_used_in_composite": list(scoring_result.included_weights.keys()),
        }

    crash = scoring_result.scores.get("crash_history_raw")
    if crash is None or crash.dropna().empty:
        return {
            "status": "skipped",
            "reason": "crash_history no pudo calcularse para ninguna esquina de este scope",
        }

    composite = scoring_result.scores["indice"]
    geometric_index = _geometric_only_index(geometry, config)

    valid = crash.notna() & composite.notna()
    rho_composite, p_composite = spearmanr(composite[valid], crash[valid])

    valid_geo = crash.notna() & geometric_index.notna()
    if valid_geo.any():
        rho_geo, p_geo = spearmanr(geometric_index[valid_geo], crash[valid_geo])
    else:
        rho_geo, p_geo = None, None

    crash_normed = scoring.normalize_series(crash, config.normalization)
    residuals = (geometric_index - crash_normed).dropna().sort_values()

    return {
        "status": "ok",
        "n_corners": int(valid.sum()),
        "spearman_indice_compuesto_vs_siniestros": {"rho": rho_composite, "p_value": p_composite},
        "spearman_indice_geometrico_vs_siniestros": {"rho": rho_geo, "p_value": p_geo},
        "residuos": {
            "nota": "geometria_alta_pocos_siniestros: ¿mitigación efectiva o poco flujo? "
                    "geometria_baja_muchos_siniestros: ¿falta un eje geométrico relevante?",
            "geometria_alta_pocos_siniestros": residuals.tail(10).index.tolist(),
            "geometria_baja_muchos_siniestros": residuals.head(10).index.tolist(),
        },
    }


def save_validation_report(report: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
