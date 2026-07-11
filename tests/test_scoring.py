import pandas as pd

from config import load_config
from geo_utils import AxisResult
from scoring import compute_index, normalize_series


def test_percentile_normalization_orders_values_into_zero_one():
    series = pd.Series([10.0, 20.0, 30.0, 40.0])
    normed = normalize_series(series, "percentile")
    assert list(normed) == sorted(normed)
    assert normed.min() > 0
    assert normed.max() == 1.0


def test_minmax_normalization_maps_extremes_to_zero_and_one():
    series = pd.Series([10.0, 20.0, 30.0])
    normed = normalize_series(series, "minmax")
    assert normed.iloc[0] == 0.0
    assert normed.iloc[-1] == 1.0
    assert normed.iloc[1] == 0.5


def test_constant_series_normalizes_to_neutral_0_5():
    series = pd.Series([5.0, 5.0, 5.0])
    normed = normalize_series(series, "minmax")
    assert (normed == 0.5).all()


def test_nulls_are_preserved_not_treated_as_zero():
    series = pd.Series([1.0, None, 3.0])
    normed = normalize_series(series, "percentile")
    assert pd.isna(normed.iloc[1])
    assert normed.iloc[0] < normed.iloc[2]


def test_all_null_series_stays_all_null():
    series = pd.Series([None, None])
    normed = normalize_series(series, "percentile")
    assert normed.isna().all()


def test_binary_keeps_zero_as_zero():
    # percentil sobre un binario le daría ~0.4 a los ceros; binary los deja en 0
    series = pd.Series([0.0, 0.0, 0.0, 1.0])
    normed = normalize_series(series, "binary")
    assert list(normed) == [0.0, 0.0, 0.0, 1.0]


def test_zero_inflated_zeros_stay_zero_and_positives_rank():
    series = pd.Series([0.0, 0.0, 2.0, 5.0])
    normed = normalize_series(series, "zero_inflated")
    assert normed.iloc[0] == 0.0
    assert normed.iloc[1] == 0.0
    assert 0.0 < normed.iloc[2] < normed.iloc[3] <= 1.0


def test_zero_inflated_all_zeros_stays_zero_not_neutral():
    series = pd.Series([0.0, 0.0, 0.0])
    normed = normalize_series(series, "zero_inflated")
    assert (normed == 0.0).all()


def _axis_result(corner_ids, values):
    df = pd.DataFrame({"n_branches": values}, index=pd.Index(corner_ids, name="corner_id"))
    return AxisResult(values=df, null_reasons={})


def test_indice_comuna_normaliza_dentro_de_cada_grupo():
    # dos comunas con rangos de riesgo muy distintos: el índice global las
    # ordena juntas, pero indice_comuna debe llegar a ~1 en cada una por separado
    ids = ["a", "b", "c", "d"]
    cfg = load_config()
    geo = _axis_result(ids, [1.0, 2.0, 100.0, 200.0])
    empty = AxisResult(values=pd.DataFrame(index=pd.Index(ids, name="corner_id")), null_reasons={})
    group = pd.Series({"a": 1, "b": 1, "c": 2, "d": 2})

    res = compute_index(geo, empty, empty, cfg, group=group)
    scores = res.scores
    # cada comuna alcanza su propio máximo (1.0) en indice_comuna
    assert scores.loc["b", "indice_comuna"] == 1.0   # tope de comuna 1
    assert scores.loc["d", "indice_comuna"] == 1.0   # tope de comuna 2
    # el índice global, en cambio, pone a la comuna 2 por encima de la 1
    assert scores.loc["c", "indice"] > scores.loc["b", "indice"]


def test_sin_group_indice_comuna_iguala_al_global():
    ids = ["a", "b", "c"]
    cfg = load_config()
    geo = _axis_result(ids, [1.0, 5.0, 9.0])
    empty = AxisResult(values=pd.DataFrame(index=pd.Index(ids, name="corner_id")), null_reasons={})
    res = compute_index(geo, empty, empty, cfg)
    assert (res.scores["indice_comuna"] == res.scores["indice"]).all()
