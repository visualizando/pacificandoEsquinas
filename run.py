#!/usr/bin/env python
"""Orquesta el pipeline end-to-end: ingest -> network -> ejes -> scoring -> validate -> export.

Uso:
    python run.py                  # usa config.yaml de la raíz del repo
    python run.py --config otro.yaml
    python run.py --top 10         # cuántas esquinas mostrar en el resumen final
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# la consola de Windows suele estar en cp1252 y los nombres de calle traen
# tildes/ñ; mejor degradar un carácter que abortar el pipeline entero
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

import export  # noqa: E402
import exposure_axes  # noqa: E402
import geometry_axes  # noqa: E402
import mitigation_axes  # noqa: E402
import network  # noqa: E402
import scoring  # noqa: E402
import validate  # noqa: E402
from config import load_config  # noqa: E402
from ingest import load_and_crop  # noqa: E402

PROCESSED = REPO_ROOT / "data" / "processed"
INTERIM = REPO_ROOT / "data" / "interim"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Índice de Esquinas Peligrosas — pipeline")
    parser.add_argument(
        "--config", default=None, metavar="RUTA",
        help="ruta a un config.yaml alternativo (default: el de la raíz del repo)",
    )
    parser.add_argument(
        "--top", type=int, default=5, metavar="N",
        help="cuántas esquinas mostrar en el resumen final (default: 5; 0 para omitir)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    t0 = time.time()
    config = load_config(args.config)
    print(f"[1/6] scope={config.scope.mode} corner_definition={config.corner_definition}")

    ingest_result = load_and_crop(config)
    print(f"[2/6] ingest: disponibles={sorted(ingest_result.layers.keys())}")
    if ingest_result.unavailable:
        print(f"       no disponibles: {sorted(ingest_result.unavailable.keys())}")

    corners = network.build_corners(ingest_result.layers["callejero"], config)
    network.save_corners(corners, INTERIM / "corners.gpkg")
    print(f"[3/6] network: {len(corners)} esquinas detectadas")

    geo = geometry_axes.compute(corners, ingest_result, config)
    mit = mitigation_axes.compute(corners, ingest_result, config)
    exp = exposure_axes.compute(corners, ingest_result, config)
    print("[4/6] ejes calculados (geometry/mitigation/exposure)")

    group = corners.set_index("corner_id")["comuna"] if "comuna" in corners.columns else None
    scoring_result = scoring.compute_index(geo, mit, exp, config, group=group)
    print(f"[5/6] scoring: ejes usados={list(scoring_result.included_weights.keys())}")
    print(f"       normalización por eje: {scoring_result.normalization_methods}")
    print(f"       ejes excluidos (sin fuente): {list(scoring_result.excluded_axes.keys())}")

    validation_report = validate.run_validation(scoring_result, geo, ingest_result, config)
    validate.save_validation_report(validation_report, PROCESSED / "validation_report.json")
    print(f"[6/6] validate: status={validation_report['status']}")
    if validation_report["status"] == "ok":
        rho_c = validation_report["spearman_indice_compuesto_vs_siniestros"]["rho"]
        rho_g = validation_report["spearman_indice_geometrico_vs_siniestros"]["rho"]
        print(f"       Spearman índice compuesto vs siniestros: {rho_c:.3f}")
        print(f"       Spearman índice geométrico puro vs siniestros: {rho_g:.3f}")

    export_gdf = export.build_export_gdf(corners, scoring_result, ingest_result, config)
    export.save_gpkg(export_gdf, PROCESSED / "esquinas.gpkg")
    export.save_geojson(export_gdf, PROCESSED / "esquinas.geojson")
    # a escala ciudad se escriben solo las top-N fichas (config report.fichas_top_n:
    # null = todas). El geojson y el gpkg siguen teniendo todas las esquinas.
    n_fichas = export.save_fichas(
        export_gdf, scoring_result.excluded_axes, PROCESSED / "fichas", config,
        top_n=config.fichas_top_n,
    )
    n_reporte = export.save_reporte(
        export_gdf, scoring_result.excluded_axes, config, validation_report,
        PROCESSED / "reporte.json",
    )

    metadata = export.build_run_metadata(config, ingest_result, scoring_result, len(corners))
    export.save_metadata(metadata, PROCESSED / "run_metadata.json")

    elapsed = time.time() - t0
    print(f"OK: {len(corners)} esquinas ({n_fichas} fichas, reporte top-{n_reporte}) exportadas en {elapsed:.1f}s -> {PROCESSED}")

    if args.top > 0 and not export_gdf.empty:
        top = export_gdf.nlargest(args.top, "indice")
        print(f"\nTop {len(top)} esquinas por índice compuesto:")
        for _, row in top.iterrows():
            print(f"  {row['indice']:.3f}  {row['calles']}  ({row['corner_id']})")


if __name__ == "__main__":
    main()
