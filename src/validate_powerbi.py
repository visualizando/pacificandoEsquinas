"""Validación externa del riesgo geométrico contra fatalidades del Power BI.

Usa únicamente artefactos procesados: el GeoJSON de esquinas y el suplemento
anonimizado. Las fatalidades recientes son la variable objetivo y nunca entran
en el score geométrico, evitando la circularidad del índice compuesto.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

GEOMETRY_AXES = ("crossing_length", "n_branches", "acute_angle", "roadway_width")
DEFAULT_WEIGHTS = {
    "crossing_length": 1.0,
    "n_branches": 0.8,
    "acute_angle": 1.0,
    "roadway_width": 0.9,
}


def geometry_score(properties: dict, weights: dict[str, float]) -> float | None:
    """Promedio ponderado de ejes disponibles para no premiar un dato nulo."""
    numerator = 0.0
    denominator = 0.0
    for axis in GEOMETRY_AXES:
        value = properties.get(f"{axis}_norm")
        if value is None:
            continue
        weight = float(weights.get(axis, DEFAULT_WEIGHTS[axis]))
        numerator += float(value) * weight
        denominator += weight
    return numerator / denominator if denominator else None


def _spearman(x: pd.Series, y: pd.Series) -> dict:
    valid = x.notna() & y.notna()
    if valid.sum() < 3 or x[valid].nunique() < 2 or y[valid].nunique() < 2:
        return {"rho": None, "p_value": None, "n": int(valid.sum())}
    rho, p_value = spearmanr(x[valid], y[valid])
    return {
        "rho": None if pd.isna(rho) else float(rho),
        "p_value": None if pd.isna(p_value) else float(p_value),
        "n": int(valid.sum()),
    }


def build_validation_report(geojson: dict, supplement: dict, weights: dict[str, float]) -> dict:
    fatal_by_corner = supplement.get("corners", {})
    rows = []
    for feature in geojson["features"]:
        props = feature["properties"]
        corner_id = props["corner_id"]
        fatal = fatal_by_corner.get(corner_id, {})
        rows.append({
            "corner_id": corner_id,
            "geometry_score": geometry_score(props, weights),
            "composite_index": props.get("indice"),
            "fatal_early": int(fatal.get("fatal_events_early", 0)),
            "fatal_late": int(fatal.get("fatal_events_late", 0)),
        })
    frame = pd.DataFrame(rows).set_index("corner_id")

    valid_geometry = frame["geometry_score"].notna()
    threshold = frame.loc[valid_geometry, "geometry_score"].quantile(0.9)
    top = frame[valid_geometry & (frame["geometry_score"] >= threshold)]
    overall_rate = float(frame.loc[valid_geometry, "fatal_late"].mean())
    top_rate = float(top["fatal_late"].mean()) if not top.empty else 0.0
    lift = (top_rate / overall_rate) if overall_rate > 0 else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "target": "fatal_events_late (2023-2025)",
        "n_corners": len(frame),
        "n_fatal_events_early": int(frame["fatal_early"].sum()),
        "n_fatal_events_late": int(frame["fatal_late"].sum()),
        "spearman_geometry_vs_late_fatalities": _spearman(
            frame["geometry_score"], frame["fatal_late"]
        ),
        "spearman_composite_vs_late_fatalities": _spearman(
            frame["composite_index"], frame["fatal_late"]
        ),
        "spearman_early_vs_late_fatalities": _spearman(
            frame["fatal_early"], frame["fatal_late"]
        ),
        "top_geometry_decile": {
            "threshold": float(threshold),
            "n_corners": len(top),
            "late_fatality_rate": top_rate,
            "citywide_late_fatality_rate": overall_rate,
            "lift": lift,
        },
        "note": (
            "Validación observacional sobre conteos escasos y con muchos ceros; "
            "no implica causalidad ni reemplaza una evaluación temporal formal."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida geometría contra fatalidades recientes")
    parser.add_argument("--corners", required=True, type=Path)
    parser.add_argument("--supplement", required=True, type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    geojson = json.loads(args.corners.read_text(encoding="utf-8"))
    supplement = json.loads(args.supplement.read_text(encoding="utf-8"))
    weights = dict(DEFAULT_WEIGHTS)
    if args.metadata and args.metadata.exists():
        metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
        weights.update(metadata.get("pesos_configurados", {}))

    report = build_validation_report(geojson, supplement, weights)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "OK: geometría vs fatalidades recientes "
        f"rho={report['spearman_geometry_vs_late_fatalities']['rho']:.3f}, "
        f"lift decil superior={report['top_geometry_decile']['lift']:.2f} -> {args.output}"
    )


if __name__ == "__main__":
    main()
