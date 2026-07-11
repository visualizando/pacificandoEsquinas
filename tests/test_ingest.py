from ingest import load_all_raw


def test_present_sources_load_and_missing_sources_are_reported():
    layers, unavailable = load_all_raw()

    assert "callejero" in layers
    assert not layers["callejero"].empty

    # Fuentes de transporte y contexto agregadas el 2026-07-08: deben cargar.
    for present in ("paradas", "subte", "ferrocarril", "transito_pesado",
                    "senderos_escolares", "ciclovias"):
        assert present in layers, f"{present} debería cargar desde data/raw/"
        assert not layers[present].empty

    # Fuentes documentadas como pendientes en data/raw/MANIFEST.md: deben
    # degradar con elegancia (quedar en `unavailable`), no romper el pipeline.
    for missing in ("censo", "sendas_peatonales"):
        assert missing in unavailable
        assert "no encontrado" in unavailable[missing]


def test_siniestros_source_parses_semicolon_csv_and_drops_ungeocoded_rows():
    # siniestros_viales_hechos.csv usa ';' como separador y tiene filas sin
    # coordenada geocodificada ("SD", "#REF!") que no se pueden ubicar.
    layers, _ = load_all_raw()
    assert "siniestros" in layers
    siniestros = layers["siniestros"]
    assert not siniestros.empty
    assert set(siniestros["gravedad_siniestro"].unique()) <= {"LEVE", "GRAVE", "MORTAL"}
    lon, lat = siniestros.geometry.iloc[0].x, siniestros.geometry.iloc[0].y
    assert -59 < lon < -57
    assert -35 < lat < -34


def test_escuelas_source_loads_and_reprojects_to_wgs84():
    # establecimientos_educativos.geojson viene en EPSG:9498 (POSGAR 2007 /
    # CABA 2019, coordenadas planas), no en WGS84 como el resto de las fuentes.
    layers, _ = load_all_raw()
    assert "escuelas" in layers
    escuelas = layers["escuelas"]
    assert str(escuelas.crs).upper() in ("EPSG:4326", "WGS84")
    lon, lat = escuelas.geometry.iloc[0].x, escuelas.geometry.iloc[0].y
    assert -59 < lon < -57  # CABA en grados de longitud, no metros planos
    assert -35 < lat < -34


def test_callejero_accented_fields_are_repaired_not_mojibake():
    layers, _ = load_all_raw()
    callejero = layers["callejero"]
    barrios = set(callejero["barrio"].dropna().unique())
    assert "Nuñez" in barrios or "Núñez" in barrios
    assert not any("�" in b for b in barrios)
