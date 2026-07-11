"""Ejes de mitigación (sección 5.2 del spec). Se restan del índice compuesto."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from config import Config
from geo_utils import AxisResult, nearby_bool
from ingest import IngestResult

NULL_AXIS_REASONS = {
    "crossing_marked": "requiere dataset de sendas peatonales pintadas/demarcadas (no presente en data/raw/)",
}


def compute(corners: gpd.GeoDataFrame, ingest: IngestResult, config: Config) -> AxisResult:
    corners_indexed = corners.set_index("corner_id")
    df = pd.DataFrame(index=corners["corner_id"])
    null_reasons: dict[str, str] = {}

    if ingest.is_available("cruces_semaforizados"):
        present = nearby_bool(
            corners_indexed, ingest.get("cruces_semaforizados"), config.radii["ped_signal_radius_m"]
        )
        df["has_ped_signal"] = present.astype(float).to_numpy()
    else:
        df["has_ped_signal"] = float("nan")
        null_reasons["has_ped_signal"] = ingest.unavailable.get(
            "cruces_semaforizados", "fuente cruces_semaforizados no disponible"
        )

    if ingest.is_available("ampliaciones_veredas"):
        present = nearby_bool(
            corners_indexed, ingest.get("ampliaciones_veredas"), config.radii["traffic_calming_radius_m"]
        )
        df["traffic_calming"] = present.astype(float).to_numpy()
    else:
        df["traffic_calming"] = float("nan")
        null_reasons["traffic_calming"] = ingest.unavailable.get(
            "ampliaciones_veredas", "fuente ampliaciones_veredas no disponible"
        )

    df["crossing_marked"] = float("nan")
    null_reasons.update(NULL_AXIS_REASONS)

    return AxisResult(values=df, null_reasons=null_reasons)
