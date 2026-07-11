from network import _angle_metrics, _dedupe_branches

DEFAULT_RANGE = (70.0, 110.0)


def _branch(name, bearing):
    return dict(nomoficial=name, bearing_deg=bearing)


def test_dedupe_collapses_same_street_same_direction():
    branches = [_branch("AV. X", 90.0), _branch("AV. X", 95.0), _branch("CALLE Y", 0.0)]
    assert len(_dedupe_branches(branches, 30.0)) == 2


def test_dedupe_wraps_around_north():
    # 358° y 2° son la misma dirección: el bucket angular es circular
    branches = [_branch("AV. X", 358.0), _branch("AV. X", 2.0)]
    assert len(_dedupe_branches(branches, 30.0)) == 1


def test_dedupe_keeps_same_street_opposite_directions():
    # la misma calle entrando y saliendo de la esquina son dos ramales
    branches = [_branch("CALLE Y", 0.0), _branch("CALLE Y", 180.0)]
    assert len(_dedupe_branches(branches, 30.0)) == 2


def test_four_way_perpendicular_is_not_diagonal():
    is_diagonal, deviation = _angle_metrics([0.0, 90.0, 180.0, 270.0], DEFAULT_RANGE)
    assert is_diagonal is False
    assert deviation == 0.0


def test_four_way_rotated_45_is_diagonal():
    # cruce en X (dos calles a 45°/225° y 0°/180°) en vez de perpendicular
    is_diagonal, deviation = _angle_metrics([0.0, 45.0, 180.0, 225.0], DEFAULT_RANGE)
    assert is_diagonal is True
    assert deviation == 45.0


def test_t_intersection_perpendicular_is_not_diagonal():
    is_diagonal, deviation = _angle_metrics([0.0, 90.0, 180.0], DEFAULT_RANGE)
    assert is_diagonal is False
    assert deviation == 0.0


def test_t_intersection_skewed_is_diagonal():
    is_diagonal, deviation = _angle_metrics([0.0, 60.0, 180.0], DEFAULT_RANGE)
    assert is_diagonal is True
    assert deviation == 30.0


def test_single_branch_has_no_angle_metrics():
    is_diagonal, deviation = _angle_metrics([0.0], DEFAULT_RANGE)
    assert is_diagonal is False
    assert deviation is None
