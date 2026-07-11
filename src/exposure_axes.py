"""Ejes de exposición/vulnerabilidad (sección 5.3 del spec).

Ninguna de las tres fuentes requeridas (escuelas, siniestros, paradas) está
en data/raw/ todavía (ver MANIFEST.md), así que los tres ejes quedan `null`.
La función ya está armada para activarse sola en cuanto ingest.py detecte
esos archivos, sin tocar este módulo.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from config import Config
from geo_utils import AxisResult, nearby_bool, nearby_count, nearby_weighted_sum
from ingest import IngestResult

NULL_AXIS_REASONS = {
    "near_school": "requiere padrón de escuelas/jardines (no presente en data/raw/)",
    "crash_history": "requiere siniestros viales georreferenciados (no presente en data/raw/)",
    "ped_flow_proxy": "requiere paradas de colectivo / estaciones de subte o tren (no presente en data/raw/)",
    "heavy_traffic": "requiere red de tránsito pesado (no presente en data/raw/)",
}


def compute(corners: gpd.GeoDataFrame, ingest: IngestResult, config: Config) -> AxisResult:
    corners_indexed = corners.set_index("corner_id")
    df = pd.DataFrame(index=corners["corner_id"])
    null_reasons: dict[str, str] = {}

    if ingest.is_available("escuelas"):
        present = nearby_bool(corners_indexed, ingest.get("escuelas"), config.radii["school_radius_m"])
        df["near_school"] = present.astype(float).to_numpy()
    else:
        df["near_school"] = float("nan")
        null_reasons["near_school"] = ingest.unavailable.get("escuelas", NULL_AXIS_REASONS["near_school"])

    if ingest.is_available("siniestros"):
        siniestros = ingest.get("siniestros")
        # conteo ponderado por gravedad (spec 5.3), no un simple conteo:
        # un siniestro MORTAL no es equivalente a uno LEVE.
        severity = siniestros["gravedad_siniestro"].astype(str).str.upper().str.strip()
        weights = severity.map(config.crash_severity_weights).fillna(1.0)
        weighted = nearby_weighted_sum(corners_indexed, siniestros, config.radii["crash_radius_m"], weights)
        df["crash_history"] = weighted.to_numpy()
    else:
        df["crash_history"] = float("nan")
        null_reasons["crash_history"] = ingest.unavailable.get("siniestros", NULL_AXIS_REASONS["crash_history"])

    # ped_flow_proxy suma varias fuentes de transporte, cada una con su peso
    # (config.yaml: ped_flow_weights); con que haya una alcanza para calcularlo
    flow_sources = [
        (name, weight)
        for name, weight in config.ped_flow_weights.items()
        if ingest.is_available(name)
    ]
    if flow_sources:
        radius = config.radii["ped_flow_radius_m"]
        total = pd.Series(0.0, index=corners_indexed.index)
        for name, weight in flow_sources:
            count = nearby_count(corners_indexed, ingest.get(name), radius)
            total = total + count.astype(float) * weight
        df["ped_flow_proxy"] = total.to_numpy()
    else:
        df["ped_flow_proxy"] = float("nan")
        null_reasons["ped_flow_proxy"] = NULL_AXIS_REASONS["ped_flow_proxy"]

    if ingest.is_available("transito_pesado"):
        present = nearby_bool(
            corners_indexed, ingest.get("transito_pesado"), config.radii["heavy_traffic_radius_m"]
        )
        df["heavy_traffic"] = present.astype(float).to_numpy()
    else:
        df["heavy_traffic"] = float("nan")
        null_reasons["heavy_traffic"] = ingest.unavailable.get(
            "transito_pesado", NULL_AXIS_REASONS["heavy_traffic"]
        )

    return AxisResult(values=df, null_reasons=null_reasons)
