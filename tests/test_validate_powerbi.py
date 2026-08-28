from validate_powerbi import build_validation_report, geometry_score


def test_geometry_score_reweights_available_axes():
    props = {"crossing_length_norm": 1.0, "n_branches_norm": None}
    score = geometry_score(props, {"crossing_length": 1.0, "n_branches": 99.0})
    assert score == 1.0


def test_validation_report_counts_target_and_builds_lift():
    features = []
    supplement = {"corners": {}}
    for i in range(20):
        corner_id = f"c{i}"
        features.append({
            "type": "Feature",
            "properties": {
                "corner_id": corner_id,
                "indice": i / 19,
                "crossing_length_norm": i / 19,
                "n_branches_norm": i / 19,
                "acute_angle_norm": i / 19,
                "roadway_width_norm": i / 19,
            },
            "geometry": {"type": "Point", "coordinates": [-58.4, -34.6]},
        })
        supplement["corners"][corner_id] = {
            "fatal_events_early": 0,
            "fatal_events_late": 1 if i >= 18 else 0,
        }

    report = build_validation_report({"type": "FeatureCollection", "features": features}, supplement, {})
    assert report["n_fatal_events_late"] == 2
    assert report["top_geometry_decile"]["lift"] > 1
