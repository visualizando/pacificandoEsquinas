import json

from powerbi_supplement import CornerIndex, _haversine_m, _normalized, _number, build_aggregates


def _feature(corner_id, lon, lat):
    return {
        "type": "Feature",
        "properties": {"corner_id": corner_id},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def test_nearest_corner_respects_radius():
    index = CornerIndex([_feature("c1", -58.45, -34.61)])
    assert index.nearest(-58.4501, -34.6101, 30) == "c1"
    assert index.nearest(-58.46, -34.62, 30) is None


def test_haversine_is_zero_for_same_point():
    assert _haversine_m(-58.45, -34.61, -58.45, -34.61) == 0


def test_safe_parsers_handle_source_conventions():
    assert _number("-58,45") == -58.45
    assert _number("SD") is None
    assert _normalized("peatón") == "PEATON"


def test_build_aggregates_does_not_export_personal_values(tmp_path):
    corners = {
        "type": "FeatureCollection",
        "features": [_feature("c1", -58.45, -34.61)],
    }
    corners_path = tmp_path / "corners.geojson"
    corners_path.write_text(json.dumps(corners), encoding="utf-8")

    hechos_path = tmp_path / "hechos.csv"
    hechos_path.write_text(
        "ID_MDD,LONGITUD,LATITUD,AAAA,NRO_CAUSA\n"
        "h1,-58.45,-34.61,2025,CAUSA-SECRETA\n",
        encoding="utf-8",
    )
    victimas_path = tmp_path / "victimas.csv"
    victimas_path.write_text(
        "ID_MDD,VICTIMA_AGREGADO,VICTIMA_DESAGREGADO,EDAD_VICTIMA,DNI_VICTIMA,DOMINIO_VICTIMA\n"
        "h1,PEATON,PEATON,12,12345678,ABC123\n",
        encoding="utf-8",
    )

    serialized = json.dumps(build_aggregates(hechos_path, victimas_path, corners_path))
    assert "12345678" not in serialized
    assert "ABC123" not in serialized
    assert "CAUSA-SECRETA" not in serialized
    assert "DNI_VICTIMA" not in serialized
    assert "DOMINIO_VICTIMA" not in serialized
