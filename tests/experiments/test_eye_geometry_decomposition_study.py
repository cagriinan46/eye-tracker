"""Hardware-free contract checks for the geometry decomposition protocol."""

from collections import Counter
from statistics import median

import pytest

from experiments.eye_geometry_decomposition_study.analysis import (
    aggregate,
    analyze,
    decompose_vertical,
)
from experiments.eye_geometry_decomposition_study.geometry import eye_record, geometry_metrics
from experiments.eye_geometry_decomposition_study.protocol import (
    CONDITIONS,
    CUE_SECONDS,
    INSTRUCTIONS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGETS,
    schedule,
    screen_content,
)
from experiments.eye_geometry_decomposition_study.run import (
    collect_study_presentation,
    measure_geometry_once,
)
from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint
from eye_tracker.vision.eye_features import EyeGeometry, extract_eye_features


def point(x, y):
    return NormalizedPoint(x, y)


def synthetic_eye(iris_y=0.51, upper_y=0.48, lower_y=0.52, center_x=0.3):
    return EyeGeometry(
        contour=(
            point(center_x - 0.1, 0.5),
            point(center_x + 0.1, 0.5),
            point(center_x, upper_y),
            point(center_x, lower_y),
        ),
        iris_ring=(
            point(center_x - 0.005, iris_y),
            point(center_x + 0.005, iris_y),
            point(center_x, iris_y - 0.005),
            point(center_x, iris_y + 0.005),
        ),
        corner_a=point(center_x - 0.1, 0.5),
        corner_b=point(center_x + 0.1, 0.5),
        upper_lid=point(center_x, upper_y),
        lower_lid=point(center_x, lower_y),
    )


def test_five_condition_schedule_is_balanced_and_nonordinal():
    plan = schedule()
    assert len(CONDITIONS) == 5
    assert CONDITIONS == (
        "comfortably_narrow",
        "slightly_narrow",
        "natural",
        "slightly_wide",
        "comfortably_wide",
    )
    assert len(TARGETS) == 3
    assert PROTOCOL_NAME == "eye_geometry_decomposition"
    assert PROTOCOL_VERSION == 1
    assert ORDER_SEED == 20261004
    assert CUE_SECONDS == 1.5
    assert plan == schedule()
    assert len(plan) == 54
    assert sum(p.phase == "calibration" for p in plan) == 9
    diagnostics = [p for p in plan if p.phase == "diagnostic"]
    assert len(diagnostics) == 45
    assert Counter((p.target.name, p.condition) for p in diagnostics) == {
        (target.name, condition): 3 for target in TARGETS for condition in CONDITIONS
    }
    assert all(
        Counter((p.target.name, p.condition) for p in diagnostics if p.block == block)
        == {(target.name, condition): 1 for target in TARGETS for condition in CONDITIONS}
        for block in (1, 2, 3)
    )
    assert all(
        [p.condition for p in diagnostics if p.block == block and p.target == target]
        != list(CONDITIONS)
        for block in (1, 2, 3)
        for target in TARGETS
    )
    for condition in CONDITIONS:
        positions = Counter(
            index
            for block in (1, 2, 3)
            for target in TARGETS
            for index, item in enumerate(
                p for p in diagnostics if p.block == block and p.target == target
            )
            if item.condition == condition
        )
        assert sorted(positions.values()) == [1, 2, 2, 2, 2]


def test_cue_and_target_content_are_disjoint():
    item = schedule()[9]
    assert screen_content(None, "ready").target is None
    cue = screen_content(item, "cue")
    assert cue.target is None
    assert cue.lines == (INSTRUCTIONS[item.condition],)
    for phase in ("settling", "sampling"):
        target = screen_content(item, phase)
        assert target.target == item.target
        assert target.lines == ()
    assert item.identity()["condition"] == item.condition
    with pytest.raises(ValueError):
        screen_content(schedule()[0], "cue")


def test_serialized_primitives_reconstruct_production_features():
    eye = synthetic_eye()
    saved = eye_record(eye)
    assert set(saved) == {
        "iris_ring",
        "iris_center",
        "corner_a",
        "corner_b",
        "upper_lid",
        "lower_lid",
        "contour_bounds",
    }
    assert len(saved["iris_ring"]) == 4
    metrics = geometry_metrics(saved, 1000, 1000)
    production = extract_eye_features(eye, 1000, 1000)
    assert metrics["vertical"] == pytest.approx(production.vertical)
    assert metrics["horizontal"] == pytest.approx(production.horizontal)
    assert metrics["aperture"] == pytest.approx(0.2)
    assert metrics["iris_x"] == pytest.approx(0.3)
    assert metrics["iris_y"] == pytest.approx(0.51)
    assert metrics["iris_local_vertical"] == pytest.approx(0.05)
    assert metrics["orientation_polarity"] == 1
    assert metrics["lid_mid_local_vertical"] == pytest.approx(0)
    assert metrics["iris_vs_lid_mid_vertical"] == pytest.approx(0.05)


def test_lid_motion_and_iris_motion_remain_distinguishable():
    baseline = geometry_metrics(eye_record(synthetic_eye()), 1000, 1000)
    open_lids = geometry_metrics(eye_record(synthetic_eye(upper_y=0.47, lower_y=0.53)), 1000, 1000)
    iris_moved = geometry_metrics(eye_record(synthetic_eye(iris_y=0.52)), 1000, 1000)
    shifted_lids = geometry_metrics(
        eye_record(synthetic_eye(upper_y=0.49, lower_y=0.53)), 1000, 1000
    )
    assert open_lids["aperture"] == pytest.approx(0.3)
    assert open_lids["vertical"] == pytest.approx(baseline["vertical"])
    assert iris_moved["vertical"] - baseline["vertical"] == pytest.approx(0.05)
    assert shifted_lids["aperture"] == pytest.approx(baseline["aperture"])
    assert shifted_lids["lid_mid_y"] - baseline["lid_mid_y"] == pytest.approx(0.01)
    assert shifted_lids["lid_mid_local_vertical"] == pytest.approx(0.05)
    assert shifted_lids["iris_vs_lid_mid_vertical"] == pytest.approx(0)


def synthetic_report():
    rows, presentations = [], []
    gaps = {
        "comfortably_narrow": 0.02,
        "slightly_narrow": 0.03,
        "natural": 0.04,
        "slightly_wide": 0.05,
        "comfortably_wide": 0.06,
    }
    iris_effects = {
        "comfortably_narrow": 0.002,
        "slightly_narrow": 0.001,
        "natural": 0,
        "slightly_wide": 0.001,
        "comfortably_wide": 0.002,
    }
    for item in schedule():
        values = []
        for sample in range(5):
            iris_y = 0.51 + iris_effects[item.condition] + (sample - 2) * 0.0002
            lid_gap = gaps[item.condition]
            eyes = {
                side: eye_record(
                    synthetic_eye(
                        iris_y=iris_y,
                        upper_y=0.5 - lid_gap / 2,
                        lower_y=0.5 + lid_gap / 2,
                        center_x=center_x,
                    )
                )
                for side, center_x in (("left", 0.3), ("right", 0.7))
            }
            metrics = {side: geometry_metrics(record, 1000, 1000) for side, record in eyes.items()}
            vertical = (metrics["left"]["vertical"] + metrics["right"]["vertical"]) / 2
            values.append(vertical)
            rows.append(
                {
                    "participant": "cagri",
                    "session": "live-1",
                    **item.identity(),
                    "presentation_order": item.order,
                    "sample_sequence": len(rows) + 1,
                    "monotonic_seconds": len(rows) / 30,
                    "timestamp_ns": len(rows) + 1,
                    "status": "usable",
                    "frame_width": 1000,
                    "frame_height": 1000,
                    "geometry": eyes,
                    "vertical": vertical,
                    "horizontal": (metrics["left"]["horizontal"] + metrics["right"]["horizontal"])
                    / 2,
                    "left_vertical": metrics["left"]["vertical"],
                    "right_vertical": metrics["right"]["vertical"],
                    "left_horizontal": metrics["left"]["horizontal"],
                    "right_horizontal": metrics["right"]["horizontal"],
                    "left_eye_opening": metrics["left"]["aperture"],
                    "right_eye_opening": metrics["right"]["aperture"],
                    "binocular_eye_opening": (
                        metrics["left"]["aperture"] + metrics["right"]["aperture"]
                    )
                    / 2,
                    "head_center_x": 0.5,
                    "head_center_y": 0.5,
                    "inter_eye_scale_px": 400,
                    "eye_line_angle_rad": 0,
                    "predicted_y": None if item.phase == "calibration" else 0.5,
                }
            )
        presentations.append(
            {
                "order": item.order,
                **item.identity(),
                "usable_count": 5,
                "unavailable_count": 0,
                "sampling_attempts": 5,
                "vertical_feature": median(values),
            }
        )
    return {
        "participant": "cagri",
        "session": "live-1",
        "protocol_name": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "ready_screen_used": True,
        "cue_seconds": CUE_SECONDS,
        "order_seed": ORDER_SEED,
        "settle_seconds": 0.8,
        "sample_seconds": 1.2,
        "minimum_usable_samples_per_presentation": 5,
        "mapping_coefficients": {"y_slope": 30.0, "y_intercept": 1.0},
        "camera_index": 1,
        "camera_resolution": [1000, 1000],
        "failed_camera_reads_including_settling": 0,
        "no_face_observations_including_settling": 0,
        "presentations": presentations,
        "rows": rows,
    }


def test_analysis_aggregates_geometry_and_actual_five_level_opening():
    report = synthetic_report()
    presentations = aggregate(report)
    result = analyze(report)
    assert len(presentations) == 54
    assert len(result["presentations"]) == 54
    assert result["manipulation_check"]["ordered_five_level_count"] == 9
    assert len(result["manipulation_check"]["triples"]) == 9
    assert len(result["condition_pairs"]) == 90
    first = next(p for p in presentations if p["phase"] == "diagnostic")
    assert first["left"]["iris_x"] == pytest.approx(0.3)
    assert first["right"]["iris_x"] == pytest.approx(0.7)
    assert first["head_center_y"] == pytest.approx(0.5)
    assert first["usable_count"] == 5


def test_fixed_target_geometry_pairs_preserve_nonlinearity_and_time():
    result = analyze(synthetic_report())
    pairs = [p for p in result["condition_pairs"] if p["target_id"] == "upper" and p["block"] == 1]
    wide = next(p for p in pairs if p["comparison"] == "comfortably_wide_minus_natural")
    narrow = next(p for p in pairs if p["comparison"] == "comfortably_narrow_minus_natural")
    assert wide["delta_binocular_opening"] == pytest.approx(0.1)
    assert narrow["delta_binocular_opening"] == pytest.approx(-0.1)
    assert wide["delta_vertical"] == pytest.approx(0.01)
    assert narrow["delta_vertical"] == pytest.approx(0.01)
    assert wide["delta_left"]["iris_y"] == pytest.approx(0.002)
    assert wide["delta_left"]["lid_mid_y"] == pytest.approx(0)
    assert wide["mapped_y_delta"] == pytest.approx(0.3)
    assert wide["first_order"] != wide["second_order"]
    assert wide["target_x"] == 0.5 and wide["target_y"] == 0.25


def test_analysis_rejects_old_or_incompatible_captures_and_corrupt_geometry():
    report = synthetic_report()
    report["protocol_version"] = 2
    with pytest.raises(ValueError, match="protocol"):
        aggregate(report)
    report = synthetic_report()
    del report["protocol_name"]
    with pytest.raises(ValueError, match="protocol"):
        aggregate(report)
    report = synthetic_report()
    report["rows"][0]["geometry"]["left"]["iris_center"] = [0.3, 0.9]
    with pytest.raises(ValueError, match="iris center"):
        aggregate(report)
    report = synthetic_report()
    report["presentations"][9]["target_y"] = 0.75
    with pytest.raises(ValueError, match="presentation"):
        aggregate(report)


def test_unavailable_sample_is_retained_without_inventing_geometry():
    report = synthetic_report()
    report["rows"][0]["status"] = "unavailable_geometry"
    report["rows"][0]["geometry"] = None
    report["presentations"][0]["usable_count"] = 4
    report["presentations"][0]["unavailable_count"] = 1
    with pytest.raises(ValueError, match="insufficient"):
        aggregate(report)
    report["minimum_usable_samples_per_presentation"] = 4
    report["presentations"][0]["vertical_feature"] = median(
        row["vertical"]
        for row in report["rows"]
        if row["presentation_order"] == 1 and row["status"] == "usable"
    )
    assert aggregate(report)[0]["unavailable_count"] == 1


def test_analyzer_rejects_inconsistent_head_geometry_and_preserves_unclipped_mapping():
    report = synthetic_report()
    report["rows"][0]["eye_line_angle_rad"] = 0.2
    with pytest.raises(ValueError, match="eye line angle"):
        aggregate(report)
    report = synthetic_report()
    report["mapping_coefficients"]["y_slope"] = 200
    pair = next(
        p
        for p in analyze(report)["condition_pairs"]
        if p["comparison"] == "comfortably_wide_minus_natural"
    )
    assert pair["mapped_y_delta"] == pytest.approx(2.0)
    assert pair["delta_head_center_y"] == pytest.approx(0)


def test_cue_precedes_target_collection_and_label_is_retained():
    item = schedule()[9]
    events = []

    def cue(presentation):
        events.append(("cue", presentation.condition))

    def collect(presentation):
        events.append(("target", presentation.phase))
        return presentation

    collected = collect_study_presentation(item, cue, collect)
    assert events == [("cue", item.condition), ("target", "diagnostic")]
    assert collected.phase == "diagnostic"
    assert item.identity()["condition"] == item.condition
    events.clear()
    collect_study_presentation(schedule()[0], cue, collect)
    assert events == [("target", "calibration")]


def test_capture_uses_existing_feature_extractor_and_keeps_primitive_geometry():
    landmarks = [point(0.5, 0.5) for _ in range(478)]
    for center_x, corner_a, corner_b, upper, lower, ring in (
        (0.3, 263, 362, 386, 374, (474, 475, 476, 477)),
        (0.7, 33, 133, 159, 145, (469, 470, 471, 472)),
    ):
        landmarks[corner_a] = point(center_x - 0.1, 0.5)
        landmarks[corner_b] = point(center_x + 0.1, 0.5)
        landmarks[upper] = point(center_x, 0.48)
        landmarks[lower] = point(center_x, 0.52)
        for index, offset in zip(ring, (-0.005, 0.005, 0, 0), strict=True):
            landmarks[index] = point(center_x + offset, 0.51)

    class Source:
        def read(self):
            return CameraFrame(object(), 1000, 1000, 123)

    class Extractor:
        def extract(self, frame):
            assert frame.timestamp_ns == 123
            return LandmarkObservation(123, tuple(landmarks))

    features, details = measure_geometry_once(Source(), Extractor(), None)
    assert details["status"] == "usable"
    assert details["frame_width"] == details["frame_height"] == 1000
    assert details["geometry"]["left"]["iris_center"] == pytest.approx([0.3, 0.51])
    assert details["geometry"]["right"]["iris_center"] == pytest.approx([0.7, 0.51])
    assert len(details["geometry"]["left"]["iris_ring"]) == 4
    assert details["head_center_x"] == pytest.approx(0.5)
    assert details["inter_eye_scale_px"] == pytest.approx(400)
    assert details["eye_line_angle_rad"] == pytest.approx(0)
    assert features.vertical == pytest.approx(details["vertical"])


def test_symmetric_decomposition_separates_iris_and_reference_changes():
    natural = {
        "iris_center": [0.3, 0.51],
        "corner_a": [0.2, 0.5],
        "corner_b": [0.4, 0.5],
        "upper_lid": [0.3, 0.48],
        "lower_lid": [0.3, 0.52],
    }
    moved_iris = {**natural, "iris_center": [0.3, 0.52]}
    iris_only = decompose_vertical(natural, moved_iris, 1000, 1000, 0.05)
    assert iris_only["iris_position_contribution"] == pytest.approx(0.05)
    assert iris_only["reference_frame_contribution"] == pytest.approx(0)
    assert iris_only["median_aggregation_residual"] == pytest.approx(0)

    moved_frame = {
        **natural,
        "corner_a": [0.2, 0.51],
        "corner_b": [0.4, 0.51],
        "upper_lid": [0.3, 0.49],
        "lower_lid": [0.3, 0.53],
    }
    frame_only = decompose_vertical(natural, moved_frame, 1000, 1000, -0.05)
    assert frame_only["iris_position_contribution"] == pytest.approx(0)
    assert frame_only["reference_frame_contribution"] == pytest.approx(-0.05)
    assert frame_only["median_aggregation_residual"] == pytest.approx(0)


def test_nonlinear_decomposition_sums_to_observed_feature_delta():
    natural = {
        "iris_center": [0.3, 0.51],
        "corner_a": [0.2, 0.5],
        "corner_b": [0.4, 0.5],
        "upper_lid": [0.3, 0.48],
        "lower_lid": [0.3, 0.52],
    }
    changed = {
        **natural,
        "iris_center": [0.3, 0.52],
        "corner_b": [0.45, 0.5],
        "lower_lid": [0.3, 0.53],
    }
    result = decompose_vertical(natural, changed, 1000, 1000, 0.037)
    assert sum(
        result[field]
        for field in (
            "iris_position_contribution",
            "reference_frame_contribution",
            "median_aggregation_residual",
        )
    ) == pytest.approx(0.037)
    assert result["median_aggregation_residual"] != 0


def test_real_pair_records_have_exact_reconstruction_and_separate_eyes():
    pair = next(
        item
        for item in analyze(synthetic_report())["condition_pairs"]
        if item["comparison"] == "comfortably_wide_minus_natural"
    )
    for side in ("left", "right"):
        pieces = pair[f"decomposition_{side}"]
        assert pieces["iris_position_contribution"] == pytest.approx(0.01)
        assert pieces["reference_frame_contribution"] == pytest.approx(0)
        assert sum(
            pieces[field]
            for field in (
                "iris_position_contribution",
                "reference_frame_contribution",
                "median_aggregation_residual",
            )
        ) == pytest.approx(pair[f"delta_{side}"]["vertical"])
