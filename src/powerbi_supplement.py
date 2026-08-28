"""Agrega localmente el dataset extraído del Power BI por esquina.

El módulo aplica una lista blanca estricta de campos y solo exporta conteos
agregados. No copia DNI, dominios, domicilios, causas, observaciones ni texto
libre. El resultado es deliberadamente local y no se versiona hasta contar
con una revisión de procedencia, privacidad y licencia.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_RADIUS_M = 30.0
GRID_DEG = 0.001

AGGREGATE_FIELDS = (
    "fatal_events_total",
    "fatal_events_2019_2025",
    "fatal_events_early",
    "fatal_events_late",
    "victims_total",
    "pedestrian_victims",
    "cyclist_victims",
    "child_victims",
    "older_victims",
)

EXCLUDED_PERSONAL_FIELDS = (
    "DNI_VICTIMA",
    "DOMINIO_VICTIMA",
    "residencia según DNI",
    "DNI_ACUSADO",
    "DOMINIO_ACUSADO",
    "datos acusado",
    "residencia_acusado",
    "NRO_CAUSA",
    "Observaciones",
)


def _number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text or text.upper() in {"SD", "S/D", "NAN", "#REF!"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode().upper().strip()


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


class CornerIndex:
    """Índice espacial mínimo, sin dependencias GIS, para puntos de CABA."""

    def __init__(self, features: list[dict]):
        self.cells: dict[tuple[int, int], list[tuple[str, float, float]]] = defaultdict(list)
        for feature in features:
            lon, lat = feature["geometry"]["coordinates"]
            corner_id = feature["properties"]["corner_id"]
            self.cells[self._cell(lon, lat)].append((corner_id, lon, lat))

    @staticmethod
    def _cell(lon: float, lat: float) -> tuple[int, int]:
        return math.floor(lon / GRID_DEG), math.floor(lat / GRID_DEG)

    def nearest(self, lon: float, lat: float, radius_m: float = DEFAULT_RADIUS_M) -> str | None:
        cx, cy = self._cell(lon, lat)
        best: tuple[float, str] | None = None
        # Una celda mide ~91 x 111 m en CABA. El alcance dinámico conserva
        # resultados correctos si se cambia el radio desde la línea de comandos.
        reach = max(1, math.ceil(radius_m / 85.0))
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                for corner_id, clon, clat in self.cells.get((cx + dx, cy + dy), []):
                    distance = _haversine_m(lon, lat, clon, clat)
                    if distance <= radius_m and (best is None or distance < best[0]):
                        best = (distance, corner_id)
        return best[1] if best else None


def _empty_counts() -> dict[str, int]:
    return {field: 0 for field in AGGREGATE_FIELDS}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_aggregates(
    hechos_path: Path,
    victimas_path: Path,
    corners_path: Path,
    radius_m: float = DEFAULT_RADIUS_M,
) -> dict:
    with corners_path.open(encoding="utf-8") as handle:
        corner_index = CornerIndex(json.load(handle)["features"])

    aggregates: dict[str, dict[str, int]] = defaultdict(_empty_counts)
    event_corner: dict[str, str] = {}
    matched_events = 0
    invalid_coordinates = 0

    with hechos_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            lon, lat = _number(row.get("LONGITUD")), _number(row.get("LATITUD"))
            if lon is None or lat is None:
                invalid_coordinates += 1
                continue
            corner_id = corner_index.nearest(lon, lat, radius_m)
            if corner_id is None:
                continue
            matched_events += 1
            event_id = row.get("ID_MDD", "").strip()
            if event_id:
                event_corner[event_id] = corner_id
            counts = aggregates[corner_id]
            counts["fatal_events_total"] += 1
            year = _number(row.get("AAAA"))
            if year is not None:
                year = int(year)
                if 2019 <= year <= 2025:
                    counts["fatal_events_2019_2025"] += 1
                if 2019 <= year <= 2021:
                    counts["fatal_events_early"] += 1
                if 2023 <= year <= 2025:
                    counts["fatal_events_late"] += 1

    matched_victims = 0
    with victimas_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            corner_id = event_corner.get(row.get("ID_MDD", ""))
            if corner_id is None:
                continue
            matched_victims += 1
            counts = aggregates[corner_id]
            counts["victims_total"] += 1
            mode = _normalized(row.get("VICTIMA_AGREGADO") or row.get("VICTIMA_DESAGREGADO"))
            if "PEATON" in mode:
                counts["pedestrian_victims"] += 1
            if "BICI" in mode or "CICL" in mode:
                counts["cyclist_victims"] += 1
            age = _number(row.get("EDAD_VICTIMA"))
            if age is not None and 0 <= age < 15:
                counts["child_victims"] += 1
            if age is not None and age >= 65:
                counts["older_victims"] += 1

    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "Power BI público de siniestros viales fatales; extracción local",
            "radius_m": radius_m,
            "matched_events": matched_events,
            "matched_victims": matched_victims,
            "invalid_event_coordinates": invalid_coordinates,
            "contains_personal_data": False,
            "privacy_policy": "strict allowlist; aggregate counts by corner only",
            "input_sha256": {
                "Base_Hechos.csv": _sha256(hechos_path),
                "Base_Victimas.csv": _sha256(victimas_path),
                "esquinas.geojson": _sha256(corners_path),
            },
        },
        "corners": dict(sorted(aggregates.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Agrega el suplemento Power BI por esquina sin exportar PII")
    parser.add_argument("--hechos", required=True, type=Path)
    parser.add_argument("--victimas", required=True, type=Path)
    parser.add_argument("--corners", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--radius-m", type=float, default=DEFAULT_RADIUS_M)
    args = parser.parse_args()

    result = build_aggregates(args.hechos, args.victimas, args.corners, args.radius_m)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(
        f"OK: {result['metadata']['matched_events']} hechos y "
        f"{result['metadata']['matched_victims']} víctimas agregados -> {args.output}"
    )


if __name__ == "__main__":
    main()
