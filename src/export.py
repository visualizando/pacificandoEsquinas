"""Exportación de artefactos finales (sección 8 del spec):
esquinas.gpkg, esquinas.geojson, fichas/<corner_id>.json y metadatos de la corrida.

Los campos de imagen satelital/street view quedan como stub (`null` + nota)
hasta que se agreguen MAPBOX_TOKEN / STREETVIEW_API_KEY a .env.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd

from config import Config
from geo_utils import nearby_bool
from ingest import GEOGRAPHIC_CRS, IngestResult
from scoring import ScoringResult

# columnas que no van al geojson liviano del mapa: bookkeeping interno y
# branches_json (grande; el front usa el campo `calles` derivado de él).
GEOJSON_DROP_COLUMNS = ["n_merged_nodes", "branches_json"]
GEOJSON_FLOAT_DECIMALS = 4  # redondear reduce ~30% el tamaño del geojson a escala ciudad


def _branch_street_names(branches_json: str) -> list[str]:
    try:
        branches = json.loads(branches_json)
    except (TypeError, json.JSONDecodeError):
        return []
    names = []
    for b in branches:
        name = b.get("nomoficial")
        if name and name not in names:
            names.append(name)
    return names


def _context_flag(corners_indexed, ingest: IngestResult, source: str, radius_m: float):
    """Flag informativo (no puntúa en el índice): 1/0 si hay geometría de la
    fuente cerca de la esquina; NaN si la fuente no está en data/raw/."""
    if not ingest.is_available(source):
        return float("nan")
    return nearby_bool(corners_indexed, ingest.get(source), radius_m).astype(float).to_numpy()


def build_export_gdf(
    corners: gpd.GeoDataFrame, scoring_result: ScoringResult, ingest: IngestResult, config: Config
) -> gpd.GeoDataFrame:
    corners_indexed = corners.set_index("corner_id")
    # acute_angle_raw ya viaja en scoring_result.scores (copiado de geometry_axes,
    # que a su vez lo toma de corners); se descarta acá para evitar la colisión.
    merged = corners_indexed.drop(columns=["acute_angle_raw"]).join(scoring_result.scores)
    merged["calles"] = corners_indexed["branches_json"].map(_branch_street_names).map(", ".join)
    # flags de contexto para el informe de intervenciones: priorizan esquinas
    # (una esquina peligrosa sobre un sendero escolar se interviene primero)
    merged["on_sendero_escolar"] = _context_flag(
        corners_indexed, ingest, "senderos_escolares", config.radii.get("sendero_escolar_radius_m", 20.0)
    )
    merged["near_ciclovia"] = _context_flag(
        corners_indexed, ingest, "ciclovias", config.radii.get("ciclovia_radius_m", 15.0)
    )
    merged = merged.reset_index()
    return gpd.GeoDataFrame(merged, geometry="geometry", crs=GEOGRAPHIC_CRS)


def save_gpkg(gdf: gpd.GeoDataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GPKG", layer="esquinas")


def save_geojson(gdf: gpd.GeoDataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    light = gdf.drop(columns=[c for c in GEOJSON_DROP_COLUMNS if c in gdf.columns])
    float_cols = light.select_dtypes(include="float").columns
    light[float_cols] = light[float_cols].round(GEOJSON_FLOAT_DECIMALS)
    if path.exists():
        path.unlink()  # GeoJSON driver no sobreescribe in-place
    light.to_file(path, driver="GeoJSON")


def _generate_text(row: pd.Series, excluded_axes: dict[str, str], config: Config) -> str:
    parts = [f"Esquina de {int(row['n_branches'])} ramales" + (f" ({row['calles']})" if row.get("calles") else "")]

    if row.get("is_diagonal"):
        angle = row.get("acute_angle_raw")
        if pd.notna(angle):
            parts.append(f"con cruce en ángulo agudo (desvío de {angle:.0f}° respecto de 90°)")
        else:
            parts.append("con cruce en ángulo diagonal")

    crossing = row.get("crossing_length_raw")
    if pd.notna(crossing):
        parts.append(f"con un cruce peatonal más largo de {crossing:.0f} m")

    school = row.get("near_school_raw")
    if pd.notna(school) and school == 1.0:
        radius = int(config.radii["school_radius_m"])
        parts.append(f"a menos de {radius} m de un establecimiento educativo")

    crash = row.get("crash_history_raw")
    if pd.notna(crash) and crash > 0:
        radius = int(config.radii["crash_radius_m"])
        parts.append(
            f"con historial de siniestros con víctimas en un radio de {radius} m "
            f"(score de gravedad {crash:.0f})"
        )

    heavy = row.get("heavy_traffic_raw")
    if pd.notna(heavy) and heavy == 1.0:
        parts.append("sobre la red de tránsito pesado (camiones)")

    ped_signal = row.get("has_ped_signal_raw")
    if pd.notna(ped_signal):
        parts.append("con semáforo peatonal cercano" if ped_signal == 1.0 else "sin semáforo peatonal cercano")

    calming = row.get("traffic_calming_raw")
    if pd.notna(calming) and calming == 1.0:
        parts.append("con reductor de velocidad/oreja de vereda cercano")

    sendero = row.get("on_sendero_escolar")
    if pd.notna(sendero) and sendero == 1.0:
        parts.append("sobre un sendero escolar")

    ciclovia = row.get("near_ciclovia")
    if pd.notna(ciclovia) and ciclovia == 1.0:
        parts.append("con ciclovía en la esquina")

    text = ", ".join(parts) + "."
    if excluded_axes:
        text += " Ejes sin datos todavía en este scope: " + ", ".join(sorted(excluded_axes)) + "."
    return text


def _axis_names(row: pd.Series) -> list[str]:
    return sorted({c[: -len("_raw")] for c in row.index if c.endswith("_raw")})


def _high(row: pd.Series, axis: str, threshold: float) -> bool:
    """El eje está entre los peores (su valor normalizado supera el umbral)."""
    norm = row.get(f"{axis}_norm")
    return pd.notna(norm) and norm >= threshold


def recommend_interventions(row: pd.Series, config: Config) -> list[dict]:
    """Deriva de los ejes qué intervenciones de bajo costo aplican a la esquina.
    Cada una: tipo, motivo (con el dato concreto) y prioridad (para ordenar).
    Se apoya en los ejes normalizados (percentil) con `intervention_threshold`
    para "alto", y en los valores crudos para el texto y los flags binarios."""
    thr = config.intervention_threshold
    recs: list[dict] = []

    near_school = row.get("near_school_raw") == 1.0
    has_crashes = pd.notna(row.get("crash_history_raw")) and row.get("crash_history_raw") > 0
    prioridad_exposicion = 2 if (near_school or has_crashes) else 0

    # 1) Cruce largo / calzada ancha -> acortar con orejas o refugio
    if _high(row, "crossing_length", thr) or _high(row, "roadway_width", thr):
        cl = row.get("crossing_length_raw")
        motivo = f"cruce peatonal de {cl:.0f} m" if pd.notna(cl) else "calzada ancha para cruzar"
        recs.append({
            "tipo": "Acortar el cruce",
            "detalle": "Orejas de vereda (bulb-out) y/o isla de refugio para reducir los metros expuestos.",
            "motivo": motivo,
            "prioridad": 3 + prioridad_exposicion,
        })

    # 2) Cruce diagonal / ángulo agudo -> enderezar la geometría
    if row.get("is_diagonal") is True or _high(row, "acute_angle", thr):
        aa = row.get("acute_angle_raw")
        motivo = f"cruce diagonal (desvío de {aa:.0f}° respecto de 90°)" if pd.notna(aa) else "cruce en ángulo agudo"
        recs.append({
            "tipo": "Enderezar el cruce",
            "detalle": "Redemarcar sendas perpendiculares y ampliar la ochava para acortar y ordenar el paso.",
            "motivo": motivo,
            "prioridad": 2 + prioridad_exposicion,
        })

    # 3) Sin semáforo peatonal donde hay exposición -> instalarlo
    if row.get("has_ped_signal_raw") == 0.0 and (near_school or has_crashes or _high(row, "ped_flow_proxy", thr)):
        razones = []
        if near_school:
            razones.append("a metros de una escuela")
        if has_crashes:
            razones.append(f"{row.get('crash_history_raw'):.0f} pts de siniestros")
        if _high(row, "ped_flow_proxy", thr):
            razones.append("alto flujo peatonal")
        recs.append({
            "tipo": "Instalar semáforo peatonal",
            "detalle": "Semáforo con fase peatonal (idealmente con conteo regresivo).",
            "motivo": "sin semáforo peatonal y " + ", ".join(razones),
            "prioridad": 3 + prioridad_exposicion,
        })

    # 4) Sin reductor cerca de escuela o tránsito pesado -> calmar el tránsito
    if row.get("traffic_calming_raw") == 0.0 and (near_school or row.get("heavy_traffic_raw") == 1.0):
        motivo = "entorno escolar sin reductor" if near_school else "ruta de tránsito pesado sin reductor"
        recs.append({
            "tipo": "Calmar el tránsito",
            "detalle": "Lomo de burro / reductor de velocidad o elevación del cruce.",
            "motivo": motivo,
            "prioridad": 1 + prioridad_exposicion,
        })

    recs.sort(key=lambda r: r["prioridad"], reverse=True)
    return recs


def build_ficha(row: pd.Series, excluded_axes: dict[str, str], config: Config) -> dict:
    desglose = {}
    for axis in _axis_names(row):
        raw = row.get(f"{axis}_raw")
        norm = row.get(f"{axis}_norm")
        desglose[axis] = {
            "raw": None if pd.isna(raw) else float(raw),
            "normalizado": None if pd.isna(norm) else float(norm),
            "disponible": axis not in excluded_axes,
        }
    return {
        "corner_id": row["corner_id"],
        "comuna": None if pd.isna(row.get("comuna")) else int(row["comuna"]),
        "barrio": None if pd.isna(row.get("barrio")) else str(row["barrio"]),
        "ubicacion": {"lat": row.geometry.y, "lon": row.geometry.x},
        "calles": row.get("calles", ""),
        "n_branches": int(row["n_branches"]),
        "is_diagonal": bool(row["is_diagonal"]),
        "indice_compuesto": None if pd.isna(row["indice"]) else float(row["indice"]),
        "indice_comuna": None if pd.isna(row.get("indice_comuna")) else float(row["indice_comuna"]),
        "riesgo_bruto": None if pd.isna(row["riesgo_bruto"]) else float(row["riesgo_bruto"]),
        "desglose_por_eje": desglose,
        "contexto": {
            "on_sendero_escolar": None if pd.isna(row.get("on_sendero_escolar")) else bool(row["on_sendero_escolar"]),
            "near_ciclovia": None if pd.isna(row.get("near_ciclovia")) else bool(row["near_ciclovia"]),
        },
        "intervenciones": recommend_interventions(row, config),
        "texto_explicativo": _generate_text(row, excluded_axes, config),
        "imagenes": {
            "satelital": None,
            "street_view": None,
            "nota": "Sin MAPBOX_TOKEN/STREETVIEW_API_KEY en .env todavía (ver .env.example); se completa en un build futuro.",
        },
    }


def save_fichas(
    gdf: gpd.GeoDataFrame, excluded_axes: dict[str, str], out_dir: str | Path, config: Config,
    top_n: int | None = None,
) -> int:
    """Escribe una ficha JSON por esquina. Si `top_n` se define, solo las
    top_n de mayor índice global (a escala ciudad no tiene sentido escribir
    15k fichas: el informe usa el top-N). Devuelve cuántas escribió."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # limpiar fichas de corridas anteriores: si no, quedan huérfanas y
    # desactualizadas al cambiar el scope o el top-N
    for old in out_dir.glob("*.json"):
        old.unlink()
    subset = gdf.nlargest(top_n, "indice") if top_n else gdf
    for _, row in subset.iterrows():
        ficha = build_ficha(row, excluded_axes, config)
        with open(out_dir / f"{row['corner_id']}.json", "w", encoding="utf-8") as f:
            json.dump(ficha, f, ensure_ascii=False, indent=2)
    return len(subset)


def save_reporte(
    gdf: gpd.GeoDataFrame, excluded_axes: dict[str, str], config: Config,
    validation_report: dict, path: str | Path,
) -> int:
    """Informe consolidado (un solo archivo que consume web/report.html): las
    top-N esquinas por índice global, cada una con su ficha completa e
    intervenciones recomendadas, más el contexto de la corrida para el
    encabezado del informe."""
    top = gdf.nlargest(config.report_top_n, "indice")
    fichas = [build_ficha(row, excluded_axes, config) for _, row in top.iterrows()]
    reporte = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "scope": {"mode": config.scope.mode, "comuna": config.scope.comuna},
        "top_n": len(fichas),
        "n_corners_total": len(gdf),
        "validacion": {
            "status": validation_report.get("status"),
            "spearman_geometrico": (
                validation_report.get("spearman_indice_geometrico_vs_siniestros", {}).get("rho")
                if validation_report.get("status") == "ok" else None
            ),
            "spearman_compuesto": (
                validation_report.get("spearman_indice_compuesto_vs_siniestros", {}).get("rho")
                if validation_report.get("status") == "ok" else None
            ),
        },
        "ejes_excluidos": sorted(excluded_axes.keys()),
        "esquinas": fichas,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2, default=str)
    return len(fichas)


def build_run_metadata(
    config: Config,
    ingest: IngestResult,
    scoring_result: ScoringResult,
    n_corners: int,
) -> dict:
    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "mode": config.scope.mode,
            "comuna": config.scope.comuna,
            "barrio": config.scope.barrio,
            "bbox": config.scope.bbox,
        },
        "corner_definition": config.corner_definition,
        "node_merge_threshold_m": config.node_merge_threshold_m,
        "angle_normal_range": list(config.angle_normal_range),
        "radii": config.radii,
        "normalization": config.normalization,
        "n_corners": n_corners,
        "fuentes_disponibles": sorted(ingest.layers.keys()),
        "fuentes_no_disponibles": ingest.unavailable,
        "pesos_configurados": config.flat_weights(),
        "pesos_aplicados_esta_corrida": scoring_result.included_weights,
        "ejes_excluidos": scoring_result.excluded_axes,
        "metodos_normalizacion_por_eje": scoring_result.normalization_methods,
    }


def save_metadata(metadata: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
