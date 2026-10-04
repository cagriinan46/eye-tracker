"""Hardware-free checks for the face-reference corner-stability protocol."""

import math
from collections import Counter

import pytest

from experiments.eye_geometry_decomposition_study.geometry import eye_record, geometry_metrics
from experiments.face_reference_corner_stability_study.analysis import (
    analyze,
    stabilized_reference_contrast,
    wrapped_angle_delta,
)
from experiments.face_reference_corner_stability_study.face_reference import (
    FACE_ANCHOR_INDICES,
    apply_similarity,
    calibration_template,
    enrich_usable_rows,
    fit_similarity,
)
from experiments.face_reference_corner_stability_study.protocol import (
    CONDITIONS,
    INSTRUCTIONS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGETS,
    schedule,
    screen_content,
)
from experiments.face_reference_corner_stability_study.run import (
    collect_study_presentation,
    measure_face_once,
    wait_for_ready,
)
from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint
from eye_tracker.vision.eye_features import EyeGeometry


def test_balanced_deterministic_36_presentation_schedule():
    plan = schedule()
    assert CONDITIONS == ("comfortably_narrow", "natural", "comfortably_wide")
    assert len(TARGETS) == 3
    assert ORDER_SEED == 20261005
    assert PROTOCOL_NAME == "face_reference_corner_stability"
    assert PROTOCOL_VERSION == 1
    assert plan == schedule()
    assert len(plan) == 36
    assert sum(p.phase == "calibration" for p in plan) == 9
    diagnostics = [p for p in plan if p.phase == "diagnostic"]
    assert len(diagnostics) == 27
    assert Counter((p.target.name, p.condition, p.block) for p in diagnostics) == {
        (t.name, c, b): 1 for t in TARGETS for c in CONDITIONS for b in (1, 2, 3)
    }
    for target in TARGETS:
        for condition in CONDITIONS:
            assert Counter(
                index
                for block in (1, 2, 3)
                for index, p in enumerate(
                    q for q in diagnostics if q.target == target and q.block == block
                )
                if p.condition == condition
            ) == {0: 1, 1: 1, 2: 1}


def test_ready_and_cue_content_are_disjoint_from_target():
    item = schedule()[9]
    assert screen_content(None, "ready").target is None
    cue = screen_content(item, "cue")
    assert cue.target is None
    assert cue.lines == (INSTRUCTIONS[item.condition],)
    for phase in ("settling", "sampling"):
        content = screen_content(item, phase)
        assert content.target == item.target
        assert content.lines == ()
    events = []
    collect_study_presentation(
        item,
        lambda p: events.append(("cue", p.condition)),
        lambda p: events.append(("target", p.phase)),
    )
    assert events == [("cue", item.condition), ("target", "diagnostic")]


def test_face_anchor_set_excludes_eye_iris_lid_brow_and_mouth():
    eye = {
        249,
        263,
        362,
        373,
        374,
        380,
        381,
        382,
        384,
        385,
        386,
        387,
        388,
        390,
        398,
        466,
        7,
        33,
        133,
        144,
        145,
        153,
        154,
        155,
        157,
        158,
        159,
        160,
        161,
        163,
        173,
        246,
        474,
        475,
        476,
        477,
        469,
        470,
        471,
        472,
    }
    brow = {
        276,
        283,
        282,
        295,
        285,
        300,
        293,
        334,
        296,
        336,
        46,
        53,
        52,
        65,
        55,
        70,
        63,
        105,
        66,
        107,
    }
    assert len(FACE_ANCHOR_INDICES) >= 6
    assert len(set(FACE_ANCHOR_INDICES)) == len(FACE_ANCHOR_INDICES)
    assert not set(FACE_ANCHOR_INDICES) & (eye | brow)
    assert FACE_ANCHOR_INDICES == (6, 197, 195, 5, 4, 1, 127, 234, 454, 356)


@pytest.mark.parametrize(
    ("scale", "angle", "tx", "ty"),
    (
        (1.0, 0.0, 35.0, -26.0),
        (1.2, 0.0, 0.0, 0.0),
        (1.0, 0.17, 0.0, 0.0),
        (1.2, 0.17, 35.0, -26.0),
    ),
)
def test_similarity_alignment_reverses_translation_scale_and_rotation(scale, angle, tx, ty):
    width, height = 1000, 800
    template = [(200.0, 200.0), (500.0, 160.0), (700.0, 300.0), (450.0, 550.0)]
    current = []
    for x, y in template:
        current.append(
            [
                (scale * (math.cos(angle) * x - math.sin(angle) * y) + tx) / width,
                (scale * (math.sin(angle) * x + math.cos(angle) * y) + ty) / height,
            ]
        )
    fitted = fit_similarity(current, template, width, height)
    assert fitted["scale"] == pytest.approx(1 / scale)
    assert fitted["rotation_rad"] == pytest.approx(-angle)
    assert fitted["translation_x_px"] == pytest.approx(
        -(math.cos(angle) * tx + math.sin(angle) * ty) / scale
    )
    assert fitted["translation_y_px"] == pytest.approx(
        -(-math.sin(angle) * tx + math.cos(angle) * ty) / scale
    )
    assert fitted["rms_px"] == pytest.approx(0, abs=1e-9)
    for point, expected in zip(current, template, strict=True):
        result = apply_similarity(point, fitted, width, height)
        assert result == pytest.approx([expected[0] / width, expected[1] / height])


def _eye(x, gap=0.04):
    def p(a, b):
        return NormalizedPoint(a, b)

    return EyeGeometry(
        contour=(p(x - 0.1, 0.5), p(x + 0.1, 0.5), p(x, 0.5 - gap / 2), p(x, 0.5 + gap / 2)),
        iris_ring=(p(x - 0.005, 0.51), p(x + 0.005, 0.51), p(x, 0.505), p(x, 0.515)),
        corner_a=p(x - 0.1, 0.5),
        corner_b=p(x + 0.1, 0.5),
        upper_lid=p(x, 0.5 - gap / 2),
        lower_lid=p(x, 0.5 + gap / 2),
    )


def _sample(order, phase, anchors, opening_shift=0.0):
    geometry = {"left": eye_record(_eye(0.3)), "right": eye_record(_eye(0.7))}
    metrics = {side: geometry_metrics(record, 1000, 800) for side, record in geometry.items()}
    return {
        "presentation_order": order,
        "phase": phase,
        "status": "usable",
        "face_anchors": anchors,
        "frame_width": 1000,
        "frame_height": 800,
        "geometry": geometry,
        "vertical": (metrics["left"]["vertical"] + metrics["right"]["vertical"]) / 2,
        "binocular_eye_opening": (metrics["left"]["aperture"] + metrics["right"]["aperture"]) / 2
        + opening_shift,
    }


def test_calibration_only_template_and_face_normalized_eye_fields():
    anchors = [
        [x / 1000, y / 800]
        for x, y in (
            (500, 100),
            (500, 150),
            (500, 200),
            (500, 250),
            (500, 300),
            (500, 350),
            (200, 250),
            (250, 250),
            (750, 250),
            (800, 250),
        )
    ]
    rows = [
        _sample(1, "calibration", anchors),
        _sample(10, "diagnostic", [[x + 0.01, y] for x, y in anchors]),
    ]
    template = calibration_template(rows, 1000, 800)
    for actual, expected in zip(template, anchors, strict=True):
        assert actual == pytest.approx([expected[0] * 1000, expected[1] * 800])
    enrich_usable_rows(rows, template, 1000, 800)
    assert rows[0]["face_alignment"]["rms_px"] == pytest.approx(0)
    assert rows[1]["face_alignment"]["translation_x_px"] == pytest.approx(-10)
    for side in ("left", "right"):
        image = rows[1]["image_eye_geometry"][side]
        face = rows[1]["face_normalized_geometry"][side]
        for name in (
            "corner_a",
            "corner_b",
            "corner_midpoint",
            "iris_center",
            "upper_lid",
            "lower_lid",
            "lid_midpoint",
            "corner_span_px",
            "corner_angle_rad",
            "eye_opening",
            "vertical",
            "iris_local_parallel",
            "iris_local_vertical",
        ):
            assert name in image and name in face
        assert image["iris_local_parallel"] == pytest.approx(0)
        assert face["corner_midpoint"][0] == pytest.approx(image["corner_midpoint"][0] - 0.01)
        assert face["vertical"] == pytest.approx(image["vertical"])


def test_analysis_rejects_incompatible_protocol():
    with pytest.raises(ValueError, match="protocol"):
        analyze({"protocol_name": "eye_geometry_decomposition", "protocol_version": 1})
    with pytest.raises(ValueError, match="protocol"):
        analyze({"protocol_name": PROTOCOL_NAME, "protocol_version": 2})


def test_ready_gate_waits_for_space(monkeypatch):
    import experiments.face_reference_corner_stability_study.run as runner

    monkeypatch.setattr(runner, "draw_screen", lambda *args: "canvas")

    class CV2:
        keys = iter((0, 0, ord(" ")))
        displays = 0

        def imshow(self, window, canvas):
            assert canvas == "canvas"
            self.displays += 1

        def waitKey(self, delay):
            return next(self.keys)

    cv = CV2()
    wait_for_ready(cv, object(), "study", 1000, 800)
    assert cv.displays == 3


def test_measurement_tap_keeps_independent_face_anchors_and_eye_primitives():
    landmarks = [NormalizedPoint(0.5, 0.5) for _ in range(478)]
    for index in FACE_ANCHOR_INDICES:
        landmarks[index] = NormalizedPoint(0.2 + index / 2000, 0.4 + index / 3000)
    for center, ca, cb, upper, lower, ring in (
        (0.3, 263, 362, 386, 374, (474, 475, 476, 477)),
        (0.7, 33, 133, 159, 145, (469, 470, 471, 472)),
    ):
        landmarks[ca] = NormalizedPoint(center - 0.1, 0.5)
        landmarks[cb] = NormalizedPoint(center + 0.1, 0.5)
        landmarks[upper] = NormalizedPoint(center, 0.48)
        landmarks[lower] = NormalizedPoint(center, 0.52)
        for index, offset in zip(ring, (-0.005, 0.005, 0, 0), strict=True):
            landmarks[index] = NormalizedPoint(center + offset, 0.51)

    class Source:
        def read(self):
            return CameraFrame(object(), 1000, 800, 123)

    class Extractor:
        def extract(self, frame):
            return LandmarkObservation(frame.timestamp_ns, tuple(landmarks))

    feature, details = measure_face_once(Source(), Extractor(), None)
    assert details["status"] == "usable"
    assert len(details["face_anchors"]) == len(FACE_ANCHOR_INDICES)
    assert details["face_anchors"][0] == pytest.approx([landmarks[6].x, landmarks[6].y])
    assert details["geometry"]["left"]["corner_a"] == pytest.approx([0.2, 0.5])
    assert feature.vertical == pytest.approx(details["vertical"])


def synthetic_report():
    anchors = [
        [x / 1000, y / 800]
        for x, y in (
            (500, 100),
            (500, 150),
            (500, 200),
            (500, 250),
            (500, 300),
            (500, 350),
            (200, 250),
            (250, 250),
            (750, 250),
            (800, 250),
        )
    ]
    rows = []
    presentations = []
    gaps = {"comfortably_narrow": 0.02, "natural": 0.04, "comfortably_wide": 0.06}
    for item in schedule():
        for _ in range(5):
            geometry = {
                side: eye_record(_eye(x, gaps[item.condition]))
                for side, x in (("left", 0.3), ("right", 0.7))
            }
            metrics = {
                side: geometry_metrics(record, 1000, 800) for side, record in geometry.items()
            }
            rows.append(
                {
                    "participant": "cagri",
                    "session": "live-1",
                    **item.identity(),
                    "presentation_order": item.order,
                    "status": "usable",
                    "monotonic_seconds": len(rows) / 30,
                    "timestamp_ns": len(rows) + 1,
                    "frame_width": 1000,
                    "frame_height": 800,
                    "geometry": geometry,
                    "face_anchors": anchors,
                    "vertical": (metrics["left"]["vertical"] + metrics["right"]["vertical"]) / 2,
                    "horizontal": (metrics["left"]["horizontal"] + metrics["right"]["horizontal"])
                    / 2,
                    "binocular_eye_opening": (
                        metrics["left"]["aperture"] + metrics["right"]["aperture"]
                    )
                    / 2,
                    "head_center_x": 0.5,
                    "head_center_y": 0.5,
                    "inter_eye_scale_px": 400,
                    "eye_line_angle_rad": 0,
                    **{
                        f"{side}_{field}": metrics[side][key]
                        for side in ("left", "right")
                        for field, key in (
                            ("vertical", "vertical"),
                            ("horizontal", "horizontal"),
                            ("eye_opening", "aperture"),
                        )
                    },
                }
            )
        group = rows[-5:]
        presentations.append(
            {
                "order": item.order,
                **item.identity(),
                "usable_count": 5,
                "unavailable_count": 0,
                "sampling_attempts": 5,
                "vertical_feature": group[0]["vertical"],
                "binocular_eye_opening": group[0]["binocular_eye_opening"],
            }
        )
    template = calibration_template(rows, 1000, 800)
    enrich_usable_rows(rows, template, 1000, 800)
    return {
        "participant": "cagri",
        "session": "live-1",
        "protocol_name": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "order_seed": ORDER_SEED,
        "ready_screen_used": True,
        "cue_seconds": 1.5,
        "settle_seconds": 0.8,
        "sample_seconds": 1.2,
        "camera_index": 1,
        "camera_resolution": [1000, 800],
        "minimum_usable_samples_per_presentation": 5,
        "mapping_coefficients": {"y_slope": 20, "y_intercept": 1},
        "face_landmark_indices": list(FACE_ANCHOR_INDICES),
        "face_reference_method": "calibration_median_pixel_anchors_to_2d_similarity_v1",
        "face_reference_template_px": template,
        "presentations": presentations,
        "rows": rows,
    }


def test_analyzer_keeps_exact_target_pairs_and_face_geometry():
    report = synthetic_report()
    result = analyze(report)
    assert len(result["presentations"]) == 36
    assert len(result["condition_pairs"]) == 18
    assert result["manipulation_check"]["strict_order_count"] == 9
    pair = result["condition_pairs"][0]
    assert pair["target_id"] in {"upper", "center", "lower"}
    assert pair["delta_binocular_eye_opening"] < 0
    assert pair["eyes"]["left"]["face_normalized_geometry"]["corner_midpoint"] == pytest.approx(
        [0, 0]
    )
    assert pair["eyes"]["right"]["face_normalized_geometry"]["iris_center"] == pytest.approx([0, 0])
    assert pair["delta_face_alignment"]["scale"] == pytest.approx(0)


def test_analyzer_rejects_changed_template_and_missing_geometry():
    report = synthetic_report()
    report["face_reference_template_px"][0][0] += 1
    with pytest.raises(ValueError, match="template"):
        analyze(report)
    report = synthetic_report()
    report["rows"][0]["face_normalized_geometry"] = None
    with pytest.raises(ValueError, match="face_normalized_geometry"):
        analyze(report)


def test_corner_angle_difference_wraps_at_pi():
    assert wrapped_angle_delta(3.13, -3.13) == pytest.approx(2 * math.pi - 6.26)
    assert wrapped_angle_delta(-3.13, 3.13) == pytest.approx(-(2 * math.pi - 6.26))


def test_matched_natural_reference_removes_corner_only_feature_shift():
    natural = {
        "corner_a": [0.2, 0.5],
        "corner_b": [0.4, 0.5],
        "iris_center": [0.3, 0.51],
        "upper_lid": [0.3, 0.48],
        "lower_lid": [0.3, 0.52],
    }
    changed = {
        **natural,
        "corner_a": [0.19, 0.5],
        "corner_b": [0.41, 0.5],
    }
    result = stabilized_reference_contrast([natural], [changed], 1000, 1000)
    assert result["stabilized_delta"] == pytest.approx(0)
    assert result["natural_fixed_feature"] == pytest.approx(0.05)
    assert result["condition_fixed_feature"] == pytest.approx(0.05)


def test_matched_natural_reference_keeps_iris_only_feature_shift():
    natural = {
        "corner_a": [0.2, 0.5],
        "corner_b": [0.4, 0.5],
        "iris_center": [0.3, 0.51],
        "upper_lid": [0.3, 0.48],
        "lower_lid": [0.3, 0.52],
    }
    changed = {**natural, "iris_center": [0.3, 0.52]}
    result = stabilized_reference_contrast([natural], [changed], 1000, 1000)
    assert result["stabilized_delta"] == pytest.approx(0.05)


def test_analyzer_includes_one_counterfactual_per_matched_contrast():
    result = analyze(synthetic_report())
    assert len(result["stabilized_reference_pairs"]) == 18
    assert all(
        pair["stabilized_binocular_delta"] == pytest.approx(pair["actual_binocular_delta"])
        for pair in result["stabilized_reference_pairs"]
    )
