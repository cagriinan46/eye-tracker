"""Hardware-free checks for Issue #92's eye-sphere head frame, lock, angles and analysis."""

import json
from math import cos, radians, sin
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.sphere_gaze_vertical import analysis, capture
from experiments.vertical_signal_comparison import protocol

# Capture


def _rotation_x(angle: float) -> np.ndarray:
    c, s = cos(angle), sin(angle)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _nose_cloud() -> np.ndarray:
    """Anisotropic cloud so PCA axes are well defined: spreads 30 > 20 > 5 along x, y, z."""
    generator = np.random.default_rng(0)
    return generator.normal(size=(24, 3)) * np.array([30.0, 20.0, 5.0])


def test_nose_frame_is_right_handed_and_sign_stable() -> None:
    points = _nose_cloud()
    center, rotation = capture.nose_frame(points, None)
    assert np.allclose(center, points.mean(axis=0))
    assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-9)
    assert np.linalg.det(rotation) == pytest.approx(1.0)
    turned = points @ _rotation_x(radians(10)).T
    _, rotation_turned = capture.nose_frame(turned, rotation)
    for axis in range(3):
        assert np.dot(rotation_turned[:, axis], rotation[:, axis]) > 0.9


def test_nose_scale_is_mean_pairwise_distance() -> None:
    triangle = np.array([[0.0, 0, 0], [3, 0, 0], [0, 4, 0]])
    assert capture.nose_scale(triangle) == pytest.approx(4.0)


def _landmarks(offset_y: float = 0.0) -> list[SimpleNamespace]:
    cloud = _nose_cloud() / 1000 + 0.5
    points = [SimpleNamespace(x=0.5, y=0.5, z=0.0) for _ in range(478)]
    for index, (x, y, z) in zip(capture.NOSE_INDICES, cloud):
        points[index] = SimpleNamespace(x=x, y=y, z=z)
    points[capture.LEFT_IRIS] = SimpleNamespace(x=0.45, y=0.45 + offset_y, z=-0.01)
    points[capture.RIGHT_IRIS] = SimpleNamespace(x=0.55, y=0.45 + offset_y, z=-0.01)
    return points


def test_sphere_numbers_are_finite_derived_values_or_none() -> None:
    numbers, rotation = capture.sphere_numbers(_landmarks(), 640, 480, None)
    assert set(numbers) == set(capture.SPHERE_FIELDS)
    assert all(np.isfinite(value) for value in numbers.values())
    assert rotation.shape == (3, 3)
    assert capture.sphere_numbers(_landmarks()[:400], 640, 480, None) is None
    broken = _landmarks()
    broken[capture.LEFT_IRIS] = SimpleNamespace(x=float("nan"), y=0.4, z=0.0)
    assert capture.sphere_numbers(broken, 640, 480, None) is None


def test_extractor_adds_sphere_fields_and_keeps_first_frame_reference() -> None:
    extractor = object.__new__(capture.SphereSignalExtractor)
    extractor._reference = None
    extractor._frame_size = (640, 480)
    extractor._observe(SimpleNamespace(face_landmarks=[_landmarks()]))
    first = extractor._reference.copy()
    assert all(extractor.last_signals[name] is not None for name in capture.SPHERE_FIELDS)
    extractor._observe(SimpleNamespace(face_landmarks=[_landmarks(0.01)]))
    assert np.array_equal(extractor._reference, first)
    extractor._observe(SimpleNamespace(face_landmarks=[]))
    assert all(extractor.last_signals[name] is None for name in capture.SPHERE_FIELDS)
    json.dumps(extractor.last_signals, allow_nan=False)


def test_runner_passes_the_sphere_extractor_to_the_issue_77_collector(monkeypatch) -> None:
    from experiments.sphere_gaze_vertical import run

    seen = {}
    monkeypatch.setattr(run.collector, "run", lambda args, **kwargs: seen.update(kwargs) or 0)
    argv = ["--participant", "fatih-sphere", "--session", "A", "--camera-index", "0"]
    argv += ["--screen-size", "1512x982", "--output", "validation/results/sphere-fatih-A.json"]
    assert run.main(argv) == 0
    assert seen == {
        "signal_extractor": capture.SphereSignalExtractor,
        "experiment": "issue-92-sphere-gaze-vertical",
    }


# Analysis


def test_preregistered_constants() -> None:
    assert analysis.PROTOTYPE_RADIUS_PX == 20.0 and analysis.PROTOTYPE_FRAME_WIDTH == 640
    assert analysis.PROTOTYPE_PITCH_HALF_RANGE_DEG == 5.0
    assert analysis.LOCK_TARGET == "K-center"
    assert (analysis.SPHERE_BETTER_MARGIN, analysis.COMBO_BETTER_MARGIN) == (0.02, 0.01)
    assert analysis.SPHERE_CANDIDATES == {
        "SPHERE": ("sphere_pitch",),
        "SPHERE_COMBO": ("sphere_pitch", "opening", "blend", "pitch"),
    }


def _identity_row(iris_y: float) -> dict:
    row = {name: float(value) for name, value in zip(capture.ROTATION_FIELDS, np.eye(3).ravel())}
    row["nose_scale_px"] = 50.0
    for eye, x in (("left", -0.3), ("right", 0.3)):
        row.update(
            {f"{eye}_iris_local_x": x, f"{eye}_iris_local_y": iris_y, f"{eye}_iris_local_z": 0.0}
        )
    return row


def test_lower_iris_gives_negative_pitch_like_the_prototype() -> None:
    rows = [{**_identity_row(0.0), "target_id": "K-center", "presentation": 2} for _ in range(5)]
    lock = analysis.lock_offsets(rows, 640)
    assert lock["presentation"] == 2
    assert np.allclose(lock["offsets"]["left"], [-0.3, 0.0, 20.0 / 50.0])
    assert analysis.gaze_angles(_identity_row(0.0), lock["offsets"]) == pytest.approx((0.0, 0.0))
    down, _ = analysis.gaze_angles(_identity_row(0.05), lock["offsets"])
    up, _ = analysis.gaze_angles(_identity_row(-0.05), lock["offsets"])
    assert down < 0 < up
    assert analysis.lock_offsets(rows[:4], 640) is None


def _report(
    session: str = "A", sphere_gain: float = 0.08, noise: float = 0.0, seed: int = 1
) -> dict:
    generator = np.random.default_rng(seed)
    rows = []
    for position, item in enumerate(protocol.build_schedule(), start=1):
        x, y = item.target.x, item.target.y
        error = generator.normal(0.0, noise)
        for frame in range(6):
            jitter = (frame - 3) * 1e-4
            rows.append(
                {
                    "presentation": position,
                    "phase": item.phase,
                    "target_id": item.target.name,
                    "target_x": x,
                    "target_y": y,
                    "trial_number": item.trial,
                    "status": "usable",
                    "horizontal": 0.2 + 0.6 * x + jitter,
                    "vertical": -0.05 + 0.001 * x * y + jitter,
                    "binocular_eye_opening": 0.40 + 0.01 * (x - y) ** 2 + jitter,
                    "look_up_left": 0.3,
                    "look_up_right": 0.3,
                    "look_down_left": 0.1 + 0.02 * x,
                    "look_down_right": 0.1 + 0.02 * x,
                    "blink_left": 0.05,
                    "blink_right": 0.0,
                    "head_pitch_deg": 2.0 + 0.3 * x * x,
                    "extract_ms": 7.0,
                    **_identity_row(sphere_gain * (y - 0.5 + error) + jitter),
                }
            )
    return {
        "participant": "synthetic",
        "session": session,
        "camera_resolution": [1920, 1080],
        "rows": rows,
    }


def test_sphere_feature_that_tracks_rows_passes_and_beats_weak_r0() -> None:
    result = analysis.analyze_session(_report())
    assert result["valid"] and result["lock"] == {"presentation": 2, "frames": 6}
    sphere = result["sphere"]
    assert sphere["SPHERE"]["passes"] and sphere["SPHERE"]["mae"] < 0.01
    assert not result["frozen"]["candidates"]["R0"]["passes"]
    medians = sphere["pitch_range_deg_descriptive"]["validation_row_medians"]
    assert medians["0.2"] > medians["0.8"]
    assert "mae" in sphere["AS_PUBLISHED_descriptive"]
    json.dumps(result, allow_nan=False)


def test_rows_missing_sphere_numbers_leave_every_candidate_and_invalidate_when_too_few() -> None:
    report = _report()
    for row in report["rows"]:
        if row["phase"] == "validation" and row["presentation"] <= 34:
            row["left_iris_local_y"] = None
    result = analysis.analyze_session(report)
    assert result["frozen"]["validation_presentations"] == 13
    assert not result["valid"] and result["sphere"] == {}


def test_missing_lock_invalidates_the_session() -> None:
    report = _report()
    report["rows"] = [row for row in report["rows"] if row["target_id"] != "K-center"]
    result = analysis.analyze_session(report)
    assert result["lock"] is None and not result["valid"]


def test_combine_applies_the_preregistered_rule_and_cli(tmp_path, capsys) -> None:
    sessions = [
        analysis.analyze_session(_report(s, noise=0.02, seed=i)) for i, s in enumerate("AB")
    ]
    combined = analysis.combine(sessions)
    assert combined["complete"]
    assert combined["sphere_better_than_r0_primary"] is True
    assert combined["vertical_solved_by_sphere"] is True
    assert isinstance(combined["sphere_combo_better_than_combo_secondary"], bool)
    with pytest.raises(ValueError):
        analysis.combine([sessions[0], sessions[0]])
    paths = []
    for session in "AB":
        path = tmp_path / f"{session}.json"
        path.write_text(json.dumps(_report(session)), encoding="utf-8")
        paths.append(str(path))
    assert analysis.main(paths) == 0
    assert json.loads(capsys.readouterr().out)["combined"]["complete"]
