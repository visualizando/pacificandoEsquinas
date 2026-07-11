from shapely.geometry import box
from shapely.ops import unary_union

from config import CrossingMeasurementConfig
from geometry_axes import measure_roadway_width

CM = CrossingMeasurementConfig(offset_m=12.0, max_width_m=40.0, sidewalk_search_radius_m=80.0)


def _street_north_10m_wide():
    # calle hacia el norte de 10 m de calzada: veredas a ambos lados
    east_sidewalk = box(5, 0, 15, 30)
    west_sidewalk = box(-15, 0, -5, 30)
    return unary_union([east_sidewalk, west_sidewalk])


def test_measures_gap_between_opposing_sidewalks():
    width = measure_roadway_width(_street_north_10m_wide(), (0.0, 0.0), 0.0, CM)
    assert width is not None
    assert abs(width - 10.0) < 0.01


def test_returns_none_when_one_side_has_no_sidewalk():
    only_east = box(5, 0, 15, 30)
    assert measure_roadway_width(only_east, (0.0, 0.0), 0.0, CM) is None


def test_returns_none_when_sample_point_falls_on_sidewalk():
    # rumbo este: el punto de medición (12, 0) cae dentro de la vereda este
    width = measure_roadway_width(_street_north_10m_wide(), (0.0, 0.0), 90.0, CM)
    assert width is None


def test_wider_street_measures_wider():
    east = box(12, 0, 22, 30)
    west = box(-22, 0, -12, 30)
    width = measure_roadway_width(unary_union([east, west]), (0.0, 0.0), 0.0, CM)
    assert width is not None
    assert abs(width - 24.0) < 0.01
