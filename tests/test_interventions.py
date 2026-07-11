import pandas as pd

from config import load_config
from export import recommend_interventions

CFG = load_config()  # intervention_threshold por defecto (0.75)


def _row(**kw):
    # valores por defecto: esquina "segura" (todo bajo, con mitigación)
    base = dict(
        crossing_length_norm=0.2, crossing_length_raw=8.0,
        roadway_width_norm=0.2, roadway_width_raw=8.0,
        acute_angle_norm=0.1, acute_angle_raw=2.0, is_diagonal=False,
        near_school_raw=0.0, crash_history_raw=0.0, ped_flow_proxy_norm=0.1,
        has_ped_signal_raw=1.0, traffic_calming_raw=1.0, heavy_traffic_raw=0.0,
    )
    base.update(kw)
    return pd.Series(base)


def _tipos(row):
    return {iv["tipo"] for iv in recommend_interventions(row, CFG)}


def test_safe_corner_gets_no_interventions():
    assert recommend_interventions(_row(), CFG) == []


def test_long_crossing_triggers_acortar_with_meters_in_motivo():
    ivs = recommend_interventions(_row(crossing_length_norm=0.9, crossing_length_raw=32.0), CFG)
    acortar = [iv for iv in ivs if iv["tipo"] == "Acortar el cruce"]
    assert acortar and "32 m" in acortar[0]["motivo"]


def test_missing_signal_near_school_triggers_semaforo():
    assert "Instalar semáforo peatonal" in _tipos(_row(has_ped_signal_raw=0.0, near_school_raw=1.0))


def test_missing_signal_without_exposure_does_not_trigger_semaforo():
    # sin escuela, siniestros ni flujo alto, la falta de semáforo no dispara la intervención
    assert "Instalar semáforo peatonal" not in _tipos(_row(has_ped_signal_raw=0.0))


def test_diagonal_triggers_enderezar():
    assert "Enderezar el cruce" in _tipos(_row(is_diagonal=True))


def test_school_without_calming_triggers_calmar_transito():
    assert "Calmar el tránsito" in _tipos(_row(near_school_raw=1.0, traffic_calming_raw=0.0))


def test_exposicion_prioriza_intervenciones():
    # una esquina con escuela+siniestros debe ordenar las intervenciones por
    # prioridad (la de mayor prioridad primero)
    row = _row(crossing_length_norm=0.9, crossing_length_raw=30.0,
               has_ped_signal_raw=0.0, near_school_raw=1.0, crash_history_raw=10.0)
    ivs = recommend_interventions(row, CFG)
    prioridades = [iv["prioridad"] for iv in ivs]
    assert prioridades == sorted(prioridades, reverse=True)
