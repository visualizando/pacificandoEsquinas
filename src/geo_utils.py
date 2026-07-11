"""Utilidades geoespaciales compartidas entre los módulos de ejes."""
from __future__ import annotations

from dataclasses import dataclass, field

import geopandas as gpd
import pandas as pd

from ingest import METRIC_CRS


@dataclass
class AxisResult:
    """Salida de un módulo de ejes: valores crudos por esquina + motivo de
    los ejes que quedaron `null` por falta de fuente."""

    values: pd.DataFrame  # index = corner_id, columnas = nombre de eje
    null_reasons: dict[str, str] = field(default_factory=dict)


def _buffered_join(
    corners: gpd.GeoDataFrame, target: gpd.GeoDataFrame, radius_m: float, extra_cols: list[str] | None = None
):
    corners_metric = corners.to_crs(METRIC_CRS)
    target_metric = target.to_crs(METRIC_CRS)
    cols = ["geometry"] + (extra_cols or [])
    buffered = gpd.GeoDataFrame(
        geometry=corners_metric.geometry.buffer(radius_m),
        index=corners_metric.index,
        crs=METRIC_CRS,
    )
    return gpd.sjoin(buffered, target_metric[cols], how="left", predicate="intersects")


def nearby_bool(corners: gpd.GeoDataFrame, target: gpd.GeoDataFrame | None, radius_m: float) -> pd.Series:
    """True si la esquina tiene al menos una geometría de `target` dentro de `radius_m`."""
    if target is None or target.empty:
        return pd.Series(False, index=corners.index)
    joined = _buffered_join(corners, target, radius_m)
    present = joined["index_right"].notna().groupby(level=0).any()
    return present.reindex(corners.index, fill_value=False)


def nearby_count(corners: gpd.GeoDataFrame, target: gpd.GeoDataFrame | None, radius_m: float) -> pd.Series:
    """Cantidad de geometrías de `target` dentro de `radius_m` de cada esquina."""
    if target is None or target.empty:
        return pd.Series(0, index=corners.index)
    joined = _buffered_join(corners, target, radius_m)
    counts = joined["index_right"].notna().groupby(level=0).sum()
    return counts.reindex(corners.index, fill_value=0)


def nearby_weighted_sum(
    corners: gpd.GeoDataFrame, target: gpd.GeoDataFrame | None, radius_m: float, weights: pd.Series
) -> pd.Series:
    """Suma ponderada de `weights` (misma cardinalidad e índice que `target`)
    para las geometrías de `target` dentro de `radius_m` de cada esquina.
    Para ejes donde no todos los eventos pesan igual (ej. crash_history
    ponderado por gravedad LEVE/GRAVE/MORTAL)."""
    if target is None or target.empty:
        return pd.Series(0.0, index=corners.index)
    target = target.copy()
    target["__weight__"] = weights.to_numpy()
    joined = _buffered_join(corners, target, radius_m, extra_cols=["__weight__"])
    total = joined["__weight__"].fillna(0.0).groupby(level=0).sum()
    return total.reindex(corners.index, fill_value=0.0)
