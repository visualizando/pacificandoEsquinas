"""Grafo vial, detección de esquinas (nodos grado>=3) y clustering espacial.

Modelo: cada fila de callejero.geojson es un tramo de calle entre dos
intersecciones. Los extremos de esos tramos son los nodos del grafo; un nodo
con 3+ tramos confluyendo es candidato a esquina. Avenidas con cantero
central (o cualquier calle ancha) generan dos nodos separados por unos pocos
metros para la misma intersección real: se clusterizan dentro de
`node_merge_threshold_m`.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import geopandas as gpd
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point

from config import Config
from ingest import GEOGRAPHIC_CRS, METRIC_CRS

COORD_PRECISION = 7  # ~1 cm en grados: suficiente para snapear extremos coincidentes de distintos tramos
# bearing_sample_m, branch_dedupe_bucket_deg y min_branches viven en
# config.yaml bajo `network:` (ver config.NetworkConfig).

CORNER_COLUMNS = [
    "corner_id", "comuna", "barrio", "n_branches", "n_merged_nodes", "is_diagonal",
    "acute_angle_raw", "has_formal_crossing", "branches_json", "geometry",
]


def _segment_comuna(row) -> int | None:
    """Comuna del tramo. `comuna` es null en calles que son límite entre dos
    comunas; en ese caso se usa com_par/com_impar (cualquiera de los lados)."""
    for key in ("comuna", "com_par", "com_impar"):
        val = _clean(row.get(key))
        if val is not None:
            return int(val)
    return None


def _segment_barrio(row) -> str | None:
    """Barrio del tramo; mismo criterio que _segment_comuna para límites."""
    for key in ("barrio", "barrio_par", "barrio_imp"):
        val = _clean(row.get(key))
        if val is not None:
            return str(val)
    return None


def _round_coord(xy: tuple[float, float]) -> tuple[float, float]:
    return (round(xy[0], COORD_PRECISION), round(xy[1], COORD_PRECISION))


def _segment_endpoints(line: LineString) -> tuple[tuple, tuple]:
    coords = list(line.coords)
    return _round_coord(coords[0]), _round_coord(coords[-1])


def _bearing_deg(p_from: tuple[float, float], p_to: tuple[float, float]) -> float:
    dx = p_to[0] - p_from[0]
    dy = p_to[1] - p_from[1]
    return math.degrees(math.atan2(dx, dy)) % 360  # 0=Norte, sentido horario


def _clean(value):
    """Convierte NaN/np.* a tipos nativos serializables en JSON."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def _build_segments(callejero: gpd.GeoDataFrame):
    callejero = callejero.reset_index(drop=True)
    callejero_metric = callejero.to_crs(METRIC_CRS)

    segments = []
    node_segments: dict[tuple, list[int]] = {}

    for (idx, row), metric_geom in zip(callejero.iterrows(), callejero_metric.geometry):
        line = row.geometry
        if line is None or line.geom_type != "LineString" or metric_geom is None:
            continue
        a, b = _segment_endpoints(line)
        if a == b:
            continue  # tramo degenerado/loop: no aporta a una intersección real
        segments.append(dict(
            a=a, b=b, geom_metric=metric_geom,
            nomoficial=_clean(row.get("nomoficial")),
            tipo_c=_clean(row.get("tipo_c")),
            sentido=_clean(row.get("sentido")),
            bicisenda=_clean(row.get("bicisenda")),
            red_jerarq=_clean(row.get("red_jerarq")),
            comuna=_segment_comuna(row),
            barrio=_segment_barrio(row),
        ))
        seg_idx = len(segments) - 1
        node_segments.setdefault(a, []).append(seg_idx)
        node_segments.setdefault(b, []).append(seg_idx)

    return segments, node_segments


def _project_nodes(nodes: list[tuple]) -> dict[tuple, tuple[float, float]]:
    pts = gpd.GeoSeries([Point(n) for n in nodes], crs=GEOGRAPHIC_CRS).to_crs(METRIC_CRS)
    return {n: (p.x, p.y) for n, p in zip(nodes, pts)}


def _cluster_nodes(nodes: list[tuple], node_metric: dict, threshold_m: float) -> list[list[tuple]]:
    """Une nodos grado>=3 que estén a <= threshold_m entre sí en una sola esquina."""
    coords = np.array([node_metric[n] for n in nodes])
    parent = list(range(len(nodes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    if len(nodes) > 1:
        tree = cKDTree(coords)
        for i, j in tree.query_pairs(r=threshold_m):
            union(i, j)

    groups: dict[int, list[tuple]] = {}
    for i, node in enumerate(nodes):
        groups.setdefault(find(i), []).append(node)
    return list(groups.values())


def _branch_bearing(corner_node: tuple, segment: dict, sample_m: float) -> float:
    geom_metric = segment["geom_metric"]
    at_start = segment["a"] == corner_node
    coords = list(geom_metric.coords)
    if not at_start:
        coords = list(reversed(coords))
    line = LineString(coords)
    length = line.length
    sample_dist = min(sample_m, length) if length > 0 else 0.0
    origin = coords[0]
    sample_pt = line.interpolate(sample_dist)
    return _bearing_deg(origin, (sample_pt.x, sample_pt.y))


def _dedupe_branches(branches: list[dict], bucket_deg: float) -> list[dict]:
    """Colapsa ramales del mismo nombre de calle en el mismo sector angular
    (ej. avenida con calzadas separadas por cantero central = 2 tramos, 1 ramal)."""
    n_buckets = max(1, round(360.0 / bucket_deg))
    seen: dict[tuple, dict] = {}
    for br in branches:
        # % n_buckets: el rumbo es circular — 358° y 2° son la misma dirección
        # y deben caer en el mismo bucket, no en los extremos opuestos del rango.
        bucket = round(br["bearing_deg"] / bucket_deg) % n_buckets
        key = (br["nomoficial"], bucket)
        if key not in seen:
            seen[key] = br
    return list(seen.values())


def _angle_metrics(bearings: list[float], angle_normal_range: tuple[float, float]) -> tuple[bool, float | None]:
    """Determina si la esquina es "diagonal" (algún ángulo entre ramales
    adyacentes cae fuera de angle_normal_range) y la desviación mínima
    respecto de 90° entre ramales que efectivamente cruzan (se ignoran los
    gaps cercanos a 180°, que son una misma calle siguiendo derecho, no un
    cruce)."""
    if len(bearings) < 2:
        return False, None
    lo, hi = angle_normal_range
    half_dev = hi - 90.0
    ordered = sorted(bearings)
    raw_gaps = [
        (ordered[(i + 1) % len(ordered)] - ordered[i]) % 360
        for i in range(len(ordered))
    ]
    # Los gaps circulares pueden superar 180° (arco "vacío" grande entre dos
    # ramales cuando el resto están agrupados). Se pliegan a su forma no
    # reflexiva (<=180) para que la desviación respecto de 90° quede acotada
    # a [0,90] y no confunda un arco vacío con un cruce muy agudo.
    gaps = [min(g, 360.0 - g) for g in raw_gaps]
    is_diagonal = False
    crossing_deviations = []
    for gap in gaps:
        if abs(gap - 180.0) <= half_dev:
            continue  # continuación recta de una misma calle, no es un ángulo de cruce
        crossing_deviations.append(abs(gap - 90.0))
        if not (lo <= gap <= hi):
            is_diagonal = True
    # max(): el eje mide el ángulo de cruce MÁS agudo (peor caso), no el mejor
    acute_angle_raw = max(crossing_deviations) if crossing_deviations else None
    return is_diagonal, acute_angle_raw


def _build_corner_record(cluster_nodes, node_metric, node_segments, segments, config: Config) -> dict:
    cluster_set = set(cluster_nodes)
    centroid_metric = np.mean([node_metric[n] for n in cluster_nodes], axis=0)
    centroid_geom_metric = Point(centroid_metric)
    centroid_geom = gpd.GeoSeries([centroid_geom_metric], crs=METRIC_CRS).to_crs(GEOGRAPHIC_CRS).iloc[0]

    raw_branches = []
    comunas = []
    barrios = []
    for node in cluster_nodes:
        for seg_idx in node_segments[node]:
            seg = segments[seg_idx]
            if seg["comuna"] is not None:
                comunas.append(seg["comuna"])
            if seg["barrio"] is not None:
                barrios.append(seg["barrio"])
            other = seg["b"] if seg["a"] == node else seg["a"]
            if other in cluster_set:
                continue  # conector interno entre nodos fusionados de la misma esquina, no es un ramal
            bearing = _branch_bearing(node, seg, config.network.bearing_sample_m)
            raw_branches.append(dict(
                nomoficial=seg["nomoficial"], tipo_c=seg["tipo_c"], sentido=seg["sentido"],
                bicisenda=seg["bicisenda"], red_jerarq=seg["red_jerarq"], bearing_deg=round(bearing, 1),
            ))

    branches = _dedupe_branches(raw_branches, config.network.branch_dedupe_bucket_deg)
    is_diagonal, acute_angle_raw = _angle_metrics(
        [b["bearing_deg"] for b in branches], config.angle_normal_range
    )
    # comuna/barrio modal de los tramos que confluyen; una esquina en el
    # límite entre dos se asigna al más frecuente
    comuna = Counter(comunas).most_common(1)[0][0] if comunas else None
    barrio = Counter(barrios).most_common(1)[0][0] if barrios else None

    lon, lat = centroid_geom.x, centroid_geom.y
    corner_id = "c" + hashlib.sha1(f"{lon:.6f},{lat:.6f}".encode()).hexdigest()[:10]

    return dict(
        corner_id=corner_id,
        comuna=comuna,
        barrio=barrio,
        n_branches=len(branches),
        n_merged_nodes=len(cluster_nodes),
        is_diagonal=is_diagonal,
        acute_angle_raw=acute_angle_raw,
        has_formal_crossing=None,  # sin fuente de sendas peatonales pintadas en data/raw/ (ver MANIFEST.md)
        branches_json=json.dumps(branches, ensure_ascii=False),
        geometry=centroid_geom,
    )


def build_corners(callejero: gpd.GeoDataFrame, config: Config) -> gpd.GeoDataFrame:
    segments, node_segments = _build_segments(callejero)

    candidate_nodes = [
        n for n, segs in node_segments.items() if len(segs) >= config.network.min_branches
    ]
    if not candidate_nodes:
        return gpd.GeoDataFrame(columns=CORNER_COLUMNS, geometry="geometry", crs=GEOGRAPHIC_CRS)

    node_metric = _project_nodes(candidate_nodes)
    clusters = _cluster_nodes(candidate_nodes, node_metric, config.node_merge_threshold_m)

    records = [
        _build_corner_record(cluster, node_metric, node_segments, segments, config)
        for cluster in clusters
    ]
    # El filtro de grado se aplica sobre nodos crudos, pero una avenida con
    # calzadas separadas puede aportar 2-3 tramos redundantes en la misma
    # dirección (mismo nombre, mismo sector angular) sin que exista una calle
    # transversal real. _dedupe_branches ya los colapsa; si después de eso
    # quedan menos ramales que min_branches, no es una esquina real sino un
    # punto de paso.
    records = [r for r in records if r["n_branches"] >= config.network.min_branches]
    if not records:
        return gpd.GeoDataFrame(columns=CORNER_COLUMNS, geometry="geometry", crs=GEOGRAPHIC_CRS)
    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=GEOGRAPHIC_CRS)

    if config.corner_definition == "formal_crossings_only":
        if gdf.empty or gdf["has_formal_crossing"].isna().all():
            raise ValueError(
                "corner_definition='formal_crossings_only' requiere el eje has_formal_crossing, "
                "que depende de un dataset de sendas peatonales no presente en data/raw/ "
                "(ver data/raw/MANIFEST.md). Agregalo o usá 'hybrid' / 'all_intersections'."
            )
        gdf = gdf[gdf["has_formal_crossing"] == True]  # noqa: E712

    return gdf.reset_index(drop=True)


def save_corners(gdf: gpd.GeoDataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GPKG", layer="corners")
