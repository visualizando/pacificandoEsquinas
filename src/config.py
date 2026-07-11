"""Carga y validación de config.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_KEYS = [
    "scope",
    "corner_definition",
    "node_merge_threshold_m",
    "angle_normal_range",
    "radii",
    "normalization",
    "weights",
]

VALID_CORNER_DEFINITIONS = {"all_intersections", "formal_crossings_only", "hybrid"}
VALID_NORMALIZATIONS = {"minmax", "percentile"}
# Métodos adicionales para axis_normalization (override por eje):
# - binary: deja 0/1 tal cual. Percentil sobre un eje binario es engañoso
#   (los ceros reciben el rank promedio, ~0.4, en vez de 0).
# - zero_inflated: 0 queda en 0, los positivos se rankean entre sí. Para
#   conteos donde la mayoría de las esquinas tiene 0 (ej. siniestros).
VALID_AXIS_NORMALIZATIONS = {"minmax", "percentile", "binary", "zero_inflated"}
VALID_SCOPE_MODES = {"comuna", "barrio", "bbox", "all"}

KNOWN_AXES = {
    # geometry
    "crossing_length", "n_branches", "acute_angle", "roadway_width", "no_refuge", "speed_limit",
    # mitigation
    "has_ped_signal", "traffic_calming", "crossing_marked",
    # exposure
    "near_school", "crash_history", "ped_flow_proxy", "heavy_traffic",
}

# Peso de cada fuente de transporte en el proxy de flujo peatonal: una boca
# de subte mueve mucha más gente que una parada de colectivo.
DEFAULT_PED_FLOW_WEIGHTS = {"paradas": 1.0, "subte": 3.0, "ferrocarril": 2.0}

REQUIRED_RADII = {
    "school_radius_m", "crash_radius_m", "ped_flow_radius_m",
    "ped_signal_radius_m", "traffic_calming_radius_m",
}

# Pesos de severidad para el conteo ponderado de crash_history (spec 5.3:
# "conteo ponderado de siniestros con víctimas"). Configurable pero con
# default razonable si config.yaml no lo especifica.
DEFAULT_CRASH_SEVERITY_WEIGHTS = {"LEVE": 1.0, "GRAVE": 3.0, "MORTAL": 5.0}


@dataclass
class ScopeConfig:
    mode: str
    comuna: int | float | None = None
    barrio: str | None = None
    bbox: list[float] | None = None
    # buffer alrededor de las calles del scope para recortar capas sin
    # atributo administrativo (semáforos, siniestros, etc.)
    buffer_m: float = 40.0


@dataclass
class CrossingMeasurementConfig:
    """Parámetros de la medición de ancho de calzada por transectos contra
    los polígonos de vereda (geometry_axes)."""
    # distancia desde el centro de la esquina, a lo largo del ramal, donde se
    # mide: pasada la ochava pero antes de mitad de cuadra
    offset_m: float = 12.0
    # ancho máximo medible; huecos más grandes se descartan como no confiables
    # (autopista, parque, borde del scope)
    max_width_m: float = 40.0
    # radio de búsqueda de polígonos de vereda alrededor de la esquina
    sidewalk_search_radius_m: float = 80.0


@dataclass
class NetworkConfig:
    # distancia a lo largo del ramal para estimar su rumbo, lejos del ruido
    # del vértice justo en la esquina
    bearing_sample_m: float = 15.0
    # ramales del mismo nombre en el mismo sector angular se colapsan en uno
    # (avenida con calzadas separadas)
    branch_dedupe_bucket_deg: float = 30.0
    # ramales mínimos para que un nodo cuente como esquina (spec: grado >= 3)
    min_branches: int = 3


@dataclass
class Config:
    scope: ScopeConfig
    corner_definition: str
    node_merge_threshold_m: float
    angle_normal_range: tuple[float, float]
    radii: dict[str, float]
    normalization: str
    weights: dict[str, dict[str, float]] = field(default_factory=dict)
    report_top_n: int = 100
    # cuántas fichas JSON escribir (None = todas). A escala ciudad conviene limitar.
    fichas_top_n: int | None = None
    # umbral (sobre el eje normalizado 0-1) a partir del cual un eje "dispara"
    # una recomendación de intervención (ej. cruce entre el 25% más largo)
    intervention_threshold: float = 0.75
    # ventanas para la tendencia de siniestros por esquina (¿mejoró/empeoró?);
    # mismas longitudes para que sean comparables, con año buffer en el medio
    crash_trend_early: tuple[int, int] = (2019, 2021)
    crash_trend_late: tuple[int, int] = (2023, 2025)
    crash_severity_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_CRASH_SEVERITY_WEIGHTS)
    )
    ped_flow_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PED_FLOW_WEIGHTS)
    )
    axis_normalization: dict[str, str] = field(default_factory=dict)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    crossing_measurement: CrossingMeasurementConfig = field(default_factory=CrossingMeasurementConfig)
    raw: dict = field(default_factory=dict)

    def flat_weights(self) -> dict[str, float]:
        """Todos los pesos (geometry+mitigation+exposure) en un único dict eje -> peso."""
        out: dict[str, float] = {}
        for group in self.weights.values():
            out.update(group)
        return out


def load_config(path: str | Path | None = None) -> Config:
    path = Path(path) if path else REPO_ROOT / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró config.yaml en {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise ValueError(f"config.yaml no tiene las claves requeridas: {missing}")

    scope_raw = raw["scope"]
    if scope_raw.get("mode") not in VALID_SCOPE_MODES:
        raise ValueError(
            f"scope.mode inválido: {scope_raw.get('mode')!r}. Debe ser uno de {VALID_SCOPE_MODES}"
        )
    scope = ScopeConfig(
        mode=scope_raw["mode"],
        comuna=scope_raw.get("comuna"),
        barrio=scope_raw.get("barrio"),
        bbox=scope_raw.get("bbox"),
        buffer_m=float(scope_raw.get("buffer_m", 40.0)),
    )

    if raw["corner_definition"] not in VALID_CORNER_DEFINITIONS:
        raise ValueError(
            f"corner_definition inválido: {raw['corner_definition']!r}. "
            f"Debe ser uno de {VALID_CORNER_DEFINITIONS}"
        )

    if raw["normalization"] not in VALID_NORMALIZATIONS:
        raise ValueError(
            f"normalization inválido: {raw['normalization']!r}. Debe ser uno de {VALID_NORMALIZATIONS}"
        )

    angle_range = raw["angle_normal_range"]
    if not (isinstance(angle_range, list) and len(angle_range) == 2):
        raise ValueError("angle_normal_range debe ser una lista [min, max]")

    radii = {k: float(v) for k, v in raw["radii"].items()}
    missing_radii = REQUIRED_RADII - radii.keys()
    if missing_radii:
        raise ValueError(
            f"config.yaml: faltan radios requeridos en radii: {sorted(missing_radii)}"
        )

    # typos en nombres de ejes fallan silenciosamente (el peso nunca se aplica),
    # así que se avisa temprano en vez de dejar que pase inadvertido.
    unknown_weight_axes = {
        axis for group in raw["weights"].values() for axis in group
    } - KNOWN_AXES
    if unknown_weight_axes:
        print(f"AVISO: ejes desconocidos en weights (¿typo?): {sorted(unknown_weight_axes)}")

    axis_normalization = raw.get("axis_normalization", {}) or {}
    for axis, method in axis_normalization.items():
        if axis not in KNOWN_AXES:
            print(f"AVISO: eje desconocido en axis_normalization (¿typo?): {axis!r}")
        if method not in VALID_AXIS_NORMALIZATIONS:
            raise ValueError(
                f"axis_normalization.{axis} inválido: {method!r}. "
                f"Debe ser uno de {sorted(VALID_AXIS_NORMALIZATIONS)}"
            )

    network_raw = raw.get("network", {}) or {}
    network = NetworkConfig(
        bearing_sample_m=float(network_raw.get("bearing_sample_m", 15.0)),
        branch_dedupe_bucket_deg=float(network_raw.get("branch_dedupe_bucket_deg", 30.0)),
        min_branches=int(network_raw.get("min_branches", 3)),
    )

    crossing_raw = raw.get("crossing_measurement", {}) or {}
    crossing_measurement = CrossingMeasurementConfig(
        offset_m=float(crossing_raw.get("offset_m", 12.0)),
        max_width_m=float(crossing_raw.get("max_width_m", 40.0)),
        sidewalk_search_radius_m=float(crossing_raw.get("sidewalk_search_radius_m", 80.0)),
    )

    return Config(
        scope=scope,
        corner_definition=raw["corner_definition"],
        node_merge_threshold_m=float(raw["node_merge_threshold_m"]),
        angle_normal_range=(float(angle_range[0]), float(angle_range[1])),
        radii=radii,
        normalization=raw["normalization"],
        weights=raw["weights"],
        report_top_n=int(raw.get("report", {}).get("top_n", 100)),
        fichas_top_n=(
            None if raw.get("report", {}).get("fichas_top_n") in (None, "all")
            else int(raw["report"]["fichas_top_n"])
        ),
        intervention_threshold=float(raw.get("report", {}).get("intervention_threshold", 0.75)),
        crash_trend_early=tuple(raw.get("crash_trend", {}).get("early", (2019, 2021))),
        crash_trend_late=tuple(raw.get("crash_trend", {}).get("late", (2023, 2025))),
        crash_severity_weights={
            k.upper(): float(v)
            for k, v in raw.get("crash_severity_weights", DEFAULT_CRASH_SEVERITY_WEIGHTS).items()
        },
        ped_flow_weights={
            k: float(v)
            for k, v in raw.get("ped_flow_weights", DEFAULT_PED_FLOW_WEIGHTS).items()
        },
        axis_normalization=axis_normalization,
        network=network,
        crossing_measurement=crossing_measurement,
        raw=raw,
    )
