"""Ejes de riesgo geométrico (sección 5.1 del spec).

- `n_branches` y `acute_angle`: derivados del grafo vial en network.py.
- `crossing_length` y `roadway_width`: medidos contra los polígonos de vereda
  (veredas-2019). Para cada ramal se tira un transecto perpendicular a la
  calle a `offset_m` del centro de la esquina y se mide el hueco libre entre
  las veredas enfrentadas: ese hueco es la calzada que el peatón cruza.
  crossing_length = el hueco máximo de la esquina (el peor cruce);
  roadway_width = el promedio. OJO: ambos salen de la misma medición, así que
  están correlacionados por construcción; cuando haya dataset de sendas
  peatonales, crossing_length debería pasar a medirse sobre la senda real.
- `no_refuge` y `speed_limit`: sin fuente todavía (ver MANIFEST.md).
"""
from __future__ import annotations

import json
import math

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from config import Config, CrossingMeasurementConfig
from geo_utils import AxisResult
from ingest import METRIC_CRS, IngestResult

BASE_NULL_REASONS = {
    "no_refuge": "requiere geometría de refugios/canteros centrales (ej. OSM crossing:island; no presente en data/raw/)",
    "speed_limit": "requiere velocidad máxima por tramo (no está en callejero.geojson ni en otra fuente de data/raw/)",
}

VEREDAS_NULL_REASONS = {
    "crossing_length": "requiere veredas-2019.geojson para medir el hueco de calzada entre veredas",
    "roadway_width": "requiere veredas-2019.geojson para medir el hueco de calzada entre veredas",
}

_EPS = 1e-6


def measure_roadway_width(
    sidewalks, corner_xy: tuple[float, float], bearing_deg: float, cm: CrossingMeasurementConfig
) -> float | None:
    """Ancho de calzada de un ramal: hueco libre del transecto perpendicular
    al ramal (a offset_m de la esquina) entre las veredas enfrentadas.
    Devuelve None si la medición no es confiable: el punto de medición cae
    sobre una vereda (rumbo mal estimado), no hay vereda de uno de los dos
    lados (parque, autopista, borde del scope) o no hay vereda cerca."""
    theta = math.radians(bearing_deg)
    ux, uy = math.sin(theta), math.cos(theta)  # rumbo: 0=Norte, sentido horario
    nx, ny = math.cos(theta), -math.sin(theta)  # perpendicular

    px = corner_xy[0] + ux * cm.offset_m
    py = corner_xy[1] + uy * cm.offset_m
    p = Point(px, py)
    if sidewalks.covers(p):
        return None

    half = cm.max_width_m
    a = (px - nx * half, py - ny * half)
    b = (px + nx * half, py + ny * half)
    transect = LineString([a, b])

    free = transect.difference(sidewalks)
    if free.is_empty:
        return None
    parts = [free] if free.geom_type == "LineString" else list(free.geoms)
    component = min(parts, key=lambda g: g.distance(p))
    if component.distance(p) > _EPS:
        return None

    # si el hueco llega hasta el borde del transecto no hay vereda "del otro
    # lado" dentro de max_width_m: medición no confiable, mejor null que un
    # ancho inventado
    for end in (component.coords[0], component.coords[-1]):
        for extreme in (a, b):
            if abs(end[0] - extreme[0]) < _EPS and abs(end[1] - extreme[1]) < _EPS:
                return None
    # huecos más anchos que max_width_m no son una calzada cruzable normal
    # (playón, autopista con colectoras, vereda fantasma lejana): descartar
    if component.length > cm.max_width_m:
        return None
    return component.length


def _crossing_metrics(
    corners: gpd.GeoDataFrame, veredas: gpd.GeoDataFrame, config: Config
) -> tuple[list[float], list[float]]:
    cm = config.crossing_measurement
    corners_metric = corners.to_crs(METRIC_CRS)
    veredas_metric = veredas.to_crs(METRIC_CRS)
    sindex = veredas_metric.sindex

    crossing_length: list[float] = []
    roadway_width: list[float] = []
    nan = float("nan")

    for (_, row), pt in zip(corners.iterrows(), corners_metric.geometry):
        bearings = [br["bearing_deg"] for br in json.loads(row["branches_json"])]
        candidate_idx = sindex.query(pt.buffer(cm.sidewalk_search_radius_m))
        if len(candidate_idx) == 0 or not bearings:
            crossing_length.append(nan)
            roadway_width.append(nan)
            continue
        sidewalks = veredas_metric.geometry.iloc[candidate_idx].union_all()
        widths = [
            w for bearing in bearings
            if (w := measure_roadway_width(sidewalks, (pt.x, pt.y), bearing, cm)) is not None
        ]
        if not widths:
            crossing_length.append(nan)
            roadway_width.append(nan)
            continue
        crossing_length.append(max(widths))
        roadway_width.append(sum(widths) / len(widths))

    return crossing_length, roadway_width


def compute(corners: gpd.GeoDataFrame, ingest: IngestResult, config: Config) -> AxisResult:
    df = pd.DataFrame(index=corners["corner_id"])
    df["n_branches"] = corners["n_branches"].to_numpy(dtype=float)
    df["acute_angle"] = corners["acute_angle_raw"].to_numpy(dtype=float)

    null_reasons = dict(BASE_NULL_REASONS)

    if ingest.is_available("veredas"):
        crossing_length, roadway_width = _crossing_metrics(corners, ingest.get("veredas"), config)
        df["crossing_length"] = crossing_length
        df["roadway_width"] = roadway_width
    else:
        df["crossing_length"] = float("nan")
        df["roadway_width"] = float("nan")
        for axis, reason in VEREDAS_NULL_REASONS.items():
            null_reasons[axis] = ingest.unavailable.get("veredas", reason)

    # float("nan"), no pd.NA: una columna object con pd.NA se serializa como
    # el string literal "<NA>" al exportar a GeoJSON en vez de null.
    for axis in BASE_NULL_REASONS:
        df[axis] = float("nan")

    return AxisResult(values=df, null_reasons=null_reasons)
