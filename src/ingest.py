"""Carga de fuentes crudas, detección de disponibilidad y recorte al scope.

No descarga nada de red: solo lee lo que ya está en data/raw/. Si una fuente
no está, queda registrada en `IngestResult.unavailable` para que los módulos
de ejes (geometry/mitigation/exposure_axes.py) decidan `null` en vez de `0`.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from config import REPO_ROOT, Config

RAW_DIR = REPO_ROOT / "data" / "raw"

# CRS métrico usado para buffers y distancias (UTM 21S, estándar para CABA).
METRIC_CRS = "EPSG:32721"
GEOGRAPHIC_CRS = "EPSG:4326"

# El buffer para recortar capas sin atributo administrativo es configurable
# en config.yaml (scope.buffer_m, default 40 m: cubre el ancho de una esquina
# típica de CABA sin invadir la comuna vecina).

# Fuentes esperadas por el spec (sección 2). Los .geojson de BA Data están
# codificados en latin-1 pese a la extensión .geojson: decodificarlos como
# UTF-8 reemplaza tildes/ñ por U+FFFD de forma irreversible, así que estas
# capas se leen a mano en vez de vía GDAL/pyogrio.
SOURCE_SPECS = {
    "callejero": dict(file="callejero.geojson", kind="geojson_latin1"),
    "cruces_semaforizados": dict(file="cruces-semaforizados.geojson", kind="geojson_latin1"),
    "semaforos": dict(file="semaforos.csv", kind="csv_points"),
    "ampliaciones_veredas": dict(file="ampliaciones_de_veredas.geojson", kind="geojson_latin1"),
    "veredas": dict(file="veredas-2019.geojson", kind="geojson_gdal"),
    # Fuentes del spec todavía no presentes en data/raw/ (ver MANIFEST.md).
    "escuelas": dict(file="establecimientos_educativos.geojson", kind="geojson_latin1"),
    "siniestros": dict(
        file="siniestros_viales_hechos.csv", kind="csv_points", sep=";",
        lon_col="longitud_siniestro", lat_col="latitud_siniestro",
    ),
    "paradas": dict(file="colectivos_caba_paradas.json", kind="geojson_latin1"),
    "subte": dict(file="estaciones_de_subte.json", kind="geojson_latin1"),
    "ferrocarril": dict(file="estaciones_ferroviarias.json", kind="geojson_latin1"),
    "transito_pesado": dict(file="red_de_transito_pesado.json", kind="geojson_latin1"),
    "senderos_escolares": dict(file="senderos_escolares.json", kind="geojson_latin1"),
    "ciclovias": dict(file="ciclovias.json", kind="geojson_latin1"),
    "censo": dict(file="censo.shp", kind="geojson_gdal"),
    "sendas_peatonales": dict(file="sendas_peatonales.geojson", kind="geojson_latin1"),
    # data/raw/estacionamiento_normativa.json existe pero no se integra
    # todavía: queda reservado para la etapa del informe de intervenciones
    # (dónde hay cordón de estacionamiento convertible en oreja de vereda).
}


@dataclass
class IngestResult:
    layers: dict[str, gpd.GeoDataFrame] = field(default_factory=dict)
    unavailable: dict[str, str] = field(default_factory=dict)
    scope_geom: object | None = None  # shapely geometry en EPSG:4326; None = sin recorte (scope 'all')

    def get(self, name: str) -> gpd.GeoDataFrame | None:
        return self.layers.get(name)

    def is_available(self, name: str) -> bool:
        return name in self.layers and not self.layers[name].empty


def _repair_mojibake(s: str) -> str:
    """Estos .geojson de BA Data mezclan codificaciones dentro del mismo
    archivo: la mayoría del texto es latin-1 (ej. 'ñ' como un solo byte), pero
    algunos campos vienen en UTF-8 genuino (ej. 'Í' como 2 bytes) que al leer
    todo el archivo como latin-1 queda partido en 2 caracteres corruptos
    ('VÃ\x8dA' en vez de 'VÍA'). Re-codificar a latin-1 (siempre reversible,
    1 char = 1 byte) y volver a decodificar como UTF-8 repara ese segundo
    caso; si no es UTF-8 válido, era latin-1 genuino y se deja como está."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        return s


def _repair_properties(obj):
    if isinstance(obj, dict):
        return {k: _repair_properties(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_repair_properties(v) for v in obj]
    if isinstance(obj, str):
        return _repair_mojibake(obj)
    return obj


def _parse_geojson_crs(data: dict) -> str:
    """Lee el miembro `crs` (legacy, pero es lo que exportan estas fuentes) de
    un GeoJSON. No todas las capas de BA Data están en WGS84: ej.
    establecimientos_educativos.geojson viene en 'POSGAR 2007 / CABA 2019'
    (EPSG:9498, coordenadas planas en metros), no en lon/lat. Sin este chequeo,
    esas coordenadas se tratarían como grados y toda distancia a esa capa
    quedaría silenciosamente mal."""
    crs_member = data.get("crs")
    if not crs_member:
        return GEOGRAPHIC_CRS  # sin crs declarado: GeoJSON (RFC 7946) asume WGS84
    name = crs_member.get("properties", {}).get("name", "")
    if "CRS84" in name or "4326" in name:
        return GEOGRAPHIC_CRS
    match = re.search(r"EPSG[:]{1,2}(\d+)", name)
    return f"EPSG:{match.group(1)}" if match else GEOGRAPHIC_CRS


def _read_geojson_latin1(path) -> gpd.GeoDataFrame:
    with open(path, encoding="latin-1") as f:
        data = json.load(f)
    features = [
        {**feat, "properties": _repair_properties(feat.get("properties", {}))}
        for feat in data["features"]
    ]
    source_crs = _parse_geojson_crs(data)
    return gpd.GeoDataFrame.from_features(features, crs=source_crs)


def _read_csv_points(path, lon_col="long", lat_col="lat", sep=",") -> gpd.GeoDataFrame:
    try:
        df = pd.read_csv(path, sep=sep, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(path, sep=sep, encoding="latin-1", low_memory=False)
    # algunas fuentes tienen filas sin coordenada geocodificada (ej. "SD",
    # "#REF!" en siniestros_viales_hechos.csv): sin lon/lat no se puede ubicar
    # el punto, así que esas filas se descartan en vez de romper el pipeline.
    lon = pd.to_numeric(df[lon_col], errors="coerce")
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    valid = lon.notna() & lat.notna()
    df = df.loc[valid].reset_index(drop=True)
    geometry = gpd.points_from_xy(lon[valid], lat[valid])
    return gpd.GeoDataFrame(df, geometry=geometry, crs=GEOGRAPHIC_CRS)


def _load_one(name: str, spec: dict) -> gpd.GeoDataFrame:
    path = RAW_DIR / spec["file"]
    if spec["kind"] == "geojson_latin1":
        gdf = _read_geojson_latin1(path)
    elif spec["kind"] == "csv_points":
        gdf = _read_csv_points(
            path,
            lon_col=spec.get("lon_col", "long"),
            lat_col=spec.get("lat_col", "lat"),
            sep=spec.get("sep", ","),
        )
    elif spec["kind"] == "geojson_gdal":
        gdf = gpd.read_file(path)
    else:
        raise ValueError(f"kind desconocido para fuente {name!r}: {spec['kind']!r}")
    # normaliza toda capa a WGS84 sin importar el CRS de origen (ver _parse_geojson_crs)
    return gdf.to_crs(GEOGRAPHIC_CRS) if gdf.crs is not None else gdf


def load_all_raw() -> tuple[dict[str, gpd.GeoDataFrame], dict[str, str]]:
    layers: dict[str, gpd.GeoDataFrame] = {}
    unavailable: dict[str, str] = {}
    for name, spec in SOURCE_SPECS.items():
        path = RAW_DIR / spec["file"]
        if not path.exists():
            unavailable[name] = f"archivo no encontrado: data/raw/{spec['file']}"
            continue
        try:
            layers[name] = _load_one(name, spec)
        except Exception as exc:  # noqa: BLE001 - degradar con elegancia, no abortar el pipeline
            unavailable[name] = f"error al cargar data/raw/{spec['file']}: {exc}"
    return layers, unavailable


def _normalize(s: object) -> object:
    if not isinstance(s, str):
        return s
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()


def _crop_callejero(gdf: gpd.GeoDataFrame, config: Config) -> gpd.GeoDataFrame:
    mode = config.scope.mode
    if mode == "all":
        return gdf
    if mode == "comuna":
        target = float(config.scope.comuna)
        mask = (
            (gdf["comuna"] == target)
            | (gdf["com_par"] == target)
            | (gdf["com_impar"] == target)
        )
        return gdf[mask]
    if mode == "barrio":
        target = _normalize(config.scope.barrio)
        mask = (
            gdf["barrio"].map(_normalize).eq(target)
            | gdf["barrio_par"].map(_normalize).eq(target)
            | gdf["barrio_imp"].map(_normalize).eq(target)
        )
        return gdf[mask]
    if mode == "bbox":
        geom = box(*config.scope.bbox)
        return gdf[gdf.intersects(geom)]
    raise ValueError(f"scope.mode desconocido: {mode!r}")


def _compute_scope_geom(config: Config, callejero_scoped: gpd.GeoDataFrame | None):
    mode = config.scope.mode
    if mode == "all":
        return None
    if mode == "bbox":
        return box(*config.scope.bbox)
    # comuna | barrio: recorte real (con atributo) ya aplicado a callejero;
    # acá se buffer-iza esa unión de calles para poder recortar capas sin
    # atributo administrativo (semáforos, cruces, ampliaciones de vereda, etc).
    if callejero_scoped is None or callejero_scoped.empty:
        return None
    metric = callejero_scoped.to_crs(METRIC_CRS)
    unioned = metric.union_all().buffer(config.scope.buffer_m)
    return gpd.GeoSeries([unioned], crs=METRIC_CRS).to_crs(GEOGRAPHIC_CRS).iloc[0]


def _crop_veredas(gdf: gpd.GeoDataFrame, config: Config, scope_geom) -> gpd.GeoDataFrame:
    mode = config.scope.mode
    if mode == "all":
        return gdf
    if mode == "comuna":
        target = int(config.scope.comuna)
        return gdf[gdf["COMUNA"] == target]
    if mode == "bbox":
        geom = box(*config.scope.bbox)
        return gdf[gdf.intersects(geom)]
    # 'barrio': veredas no tiene atributo de barrio, se recorta por geometría.
    if scope_geom is None:
        return gdf.iloc[0:0]
    return gdf[gdf.intersects(scope_geom)]


def _crop_generic(gdf: gpd.GeoDataFrame, scope_geom) -> gpd.GeoDataFrame:
    if scope_geom is None:
        return gdf
    return gdf[gdf.intersects(scope_geom)]


def load_and_crop(config: Config) -> IngestResult:
    raw, unavailable = load_all_raw()
    result = IngestResult(unavailable=unavailable)

    if "callejero" not in raw:
        raise FileNotFoundError(
            "callejero.geojson no está en data/raw/: es la fuente base para detectar esquinas (network.py)"
        )

    callejero_scoped = _crop_callejero(raw["callejero"], config)
    result.layers["callejero"] = callejero_scoped
    result.scope_geom = _compute_scope_geom(config, callejero_scoped)

    if "veredas" in raw:
        result.layers["veredas"] = _crop_veredas(raw["veredas"], config, result.scope_geom)

    for name, gdf in raw.items():
        if name in ("callejero", "veredas"):
            continue
        result.layers[name] = _crop_generic(gdf, result.scope_geom)

    return result
