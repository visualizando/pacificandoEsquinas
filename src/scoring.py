"""Índice compuesto (sección 6 del spec).

riesgo_bruto = Σ(w_i · eje_i) [geometría + exposición] − Σ(w_j · eje_j) [mitigación]
indice = normalizar(riesgo_bruto) → [0,1]

Ejes sin ningún valor en el scope actual (fuente ausente) se excluyen del
cálculo y los pesos restantes se re-escalan para conservar el mismo total de
peso configurado (ver `config.yaml: weights`), documentado en
`ScoringResult.included_weights` / `excluded_axes` para trazabilidad.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from config import Config
from geo_utils import AxisResult

MITIGATION_AXES = {"has_ped_signal", "traffic_calming", "crossing_marked"}


@dataclass
class ScoringResult:
    scores: pd.DataFrame
    included_weights: dict[str, float] = field(default_factory=dict)
    excluded_axes: dict[str, str] = field(default_factory=dict)
    normalization: str = "percentile"
    # método efectivamente usado por eje (trazabilidad: 'binary' puede ser
    # auto-detectado, no solo configurado)
    normalization_methods: dict[str, str] = field(default_factory=dict)


def resolve_axis_method(axis: str, series: pd.Series, config: Config) -> str:
    """Método de normalización para un eje: el override de config.yaml
    (axis_normalization) manda; si no hay, los ejes cuyo valor crudo es solo
    0/1 se tratan como binary (percentil sobre un binario es engañoso: los
    ceros reciben el rank promedio ~0.4 en vez de 0); el resto usa el método
    global."""
    override = config.axis_normalization.get(axis)
    if override:
        return override
    valid = series.dropna()
    if not valid.empty and set(valid.unique()) <= {0.0, 1.0}:
        return "binary"
    return config.normalization


def normalize_series(series: pd.Series, method: str) -> pd.Series:
    """Normaliza una serie a [0,1] sobre sus valores no nulos; los nulos se
    preservan como nulos.

    - binary: identidad (0/1 tal cual).
    - zero_inflated: 0 queda en 0; los positivos se rankean entre sí (para
      conteos donde la mayoría de las esquinas vale 0, ej. siniestros).
    - minmax / percentile: clásicos; si todos los valores no nulos son
      iguales no hay señal para discriminar y se asigna 0.5 (neutro).
    """
    result = pd.Series(float("nan"), index=series.index, dtype="float64")
    valid = series.dropna()
    if valid.empty:
        return result

    if method == "binary":
        result.loc[valid.index] = valid.astype(float)
        return result

    if method == "zero_inflated":
        result.loc[valid.index] = 0.0
        positive = valid[valid > 0]
        if not positive.empty:
            result.loc[positive.index] = positive.rank(method="average", pct=True)
        return result

    if valid.nunique() == 1:
        result.loc[valid.index] = 0.5
        return result
    if method == "percentile":
        normed = valid.rank(method="average", pct=True)
    elif method == "minmax":
        lo, hi = valid.min(), valid.max()
        normed = (valid - lo) / (hi - lo)
    else:
        raise ValueError(f"normalization desconocida: {method!r}")
    result.loc[valid.index] = normed
    return result


def compute_index(
    geometry: AxisResult, mitigation: AxisResult, exposure: AxisResult, config: Config,
    group: pd.Series | None = None,
) -> ScoringResult:
    """Calcula el índice compuesto. Si se pasa `group` (serie corner_id ->
    comuna), además calcula `indice_comuna`: el mismo riesgo_bruto rankeado
    dentro de cada grupo, para poder comparar esquinas dentro de su comuna
    (equidad territorial) en paralelo al ranking global."""
    values = pd.concat([geometry.values, mitigation.values, exposure.values], axis=1)
    null_reasons = {**geometry.null_reasons, **mitigation.null_reasons, **exposure.null_reasons}

    flat_weights = config.flat_weights()
    available_axes = [
        axis for axis in flat_weights
        if axis in values.columns and values[axis].notna().any()
    ]
    excluded_axes = {
        axis: null_reasons.get(axis, "eje sin valores en el scope actual")
        for axis in flat_weights
        if axis not in available_axes
    }

    total_weight = sum(flat_weights.values())
    available_weight = sum(flat_weights[a] for a in available_axes)
    scale = (total_weight / available_weight) if available_weight > 0 else 0.0
    included_weights = {a: flat_weights[a] * scale for a in available_axes}

    out = pd.DataFrame(index=values.index)
    riesgo_bruto = pd.Series(0.0, index=values.index)
    normalization_methods: dict[str, str] = {}

    for axis in flat_weights:
        # float64 con NaN, no pd.NA: una columna object con pd.NA se serializa
        # como el string literal "<NA>" al exportar a GeoJSON en vez de null.
        raw = values[axis] if axis in values.columns else pd.Series(float("nan"), index=values.index)
        out[f"{axis}_raw"] = raw
        if axis not in available_axes:
            out[f"{axis}_norm"] = float("nan")
            continue
        method = resolve_axis_method(axis, raw, config)
        normalization_methods[axis] = method
        normed = normalize_series(raw, method)
        out[f"{axis}_norm"] = normed
        signed = -normed if axis in MITIGATION_AXES else normed
        riesgo_bruto = riesgo_bruto + signed.fillna(0.0) * included_weights[axis]

    out["riesgo_bruto"] = riesgo_bruto
    out["indice"] = normalize_series(riesgo_bruto, config.normalization)

    # índice normalizado dentro de cada comuna (rank intra-grupo del mismo
    # riesgo_bruto). Con un solo grupo coincide con el índice global.
    if group is not None:
        grp = group.reindex(out.index)
        indice_comuna = pd.Series(float("nan"), index=out.index)
        for _, idx in grp.groupby(grp).groups.items():
            indice_comuna.loc[idx] = normalize_series(riesgo_bruto.loc[idx], config.normalization)
        out["indice_comuna"] = indice_comuna
    else:
        out["indice_comuna"] = out["indice"]

    return ScoringResult(
        scores=out,
        included_weights=included_weights,
        excluded_axes=excluded_axes,
        normalization=config.normalization,
        normalization_methods=normalization_methods,
    )
