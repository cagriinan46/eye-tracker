"""Synthetic same-result numerical instrumentation; no optional vision imports."""

from dataclasses import asdict
from types import SimpleNamespace

import pytest

from experiments.fixed_window_gaze_diagnostic.protocol import schedule as original_schedule
from experiments.fixed_window_gaze_diagnostic.run import collect_window
from experiments.raw_geometry_gaze_diagnostic.analysis import inspect_capture
from experiments.raw_geometry_gaze_diagnostic.geometry import (
    EYES,
    FACE_ANCHOR_INDICES,
    REQUIRED_INDICES,
    SELECTED_INDICES,
    GeometryExtractor,
    geometry_record,
    reconstruct_r0,
)
from experiments.raw_geometry_gaze_diagnostic.protocol import (
    CALIBRATION_TARGETS,
    REPRESENTATIONS,
    SESSION_ROLES,
    configuration,
    schedule,
    screen_content,
)
from experiments.raw_geometry_gaze_diagnostic.run import geometry_sample_row, parse_args
from eye_tracker.vision.contracts import CameraFrame
from eye_tracker.vision.eye_features import extract_binocular_features
from eye_tracker.vision.eye_topology import eye_geometry_from_observation
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor
from validation.real_calibration import fit_session_calibration


def detector_result(x=0.5, y=0.5, depth=True):
    points = [SimpleNamespace(x=0.45 + n * 0.0001, y=0.4, z=-0.05) for n in range(478)]
    for side, center in (("left", 0.65), ("right", 0.35)):
        eye = EYES[side]
        for index in eye["contour"]:
            points[index] = SimpleNamespace(x=center, y=0.5, z=-0.03)
        points[eye["corner_a"]].x = center - 0.04
        points[eye["corner_b"]].x = center + 0.04
        points[eye["upper_lid"]].y = 0.48
        points[eye["lower_lid"]].y = 0.52
        ix = center - 0.04 + 0.08 * x
        iy = 0.5 + 0.08 * 1920 / 1080 * 0.2 * (y - 0.5)
        for index, (dx, dy) in zip(
            eye["iris_ring"], ((-0.002, 0), (0, -0.002), (0.002, 0), (0, 0.002)), strict=True
        ):
            points[index] = SimpleNamespace(x=ix + dx, y=iy + dy, z=-0.02)
        points[eye["detector_iris_center"]] = SimpleNamespace(x=ix, y=iy, z=-0.02)
    if not depth:
        for point in points:
            del point.z
    return SimpleNamespace(face_landmarks=[points], facial_transformation_matrixes=[])


def record(x=0.5, y=0.5, stamp=123):
    return geometry_record(detector_result(x, y), 1920, 1080, stamp, stamp // 1_000_000)


def capture(session="geometry-1"):
    report = {
        **configuration(),
        "participant": "synthetic",
        "session": session,
        "session_role": SESSION_ROLES[session],
        "status": "completed",
        "ready_screen_used": True,
        "camera_index": 1,
        "camera_resolution": [1920, 1080],
        "camera_reads": 207,
        "failed_camera_reads": 0,
        "no_face_observations": 0,
        "elapsed_seconds": 134.0,
        "detector": {
            "mediapipe_version": "synthetic",
            "model_sha256": "0" * 64,
            "options_policy": "production_defaults_unchanged",
            "camera_intrinsics": None,
        },
        "calibration_presentations": [],
        "trials": [],
    }

    def rows(target, times, onset, block, order, mapping=None):
        output = []
        for t in times:
            stamp = round((onset + t - 0.01) * 1e9)
            geometry = record(target.x, target.y, stamp)
            features = reconstruct_r0(geometry)
            x, y = (
                mapping.predict(features.horizontal, features.vertical) if mapping else (None, None)
            )
            output.append(
                {
                    "trial_relative_seconds": t,
                    "monotonic_timestamp_seconds": onset + t,
                    "measurement_started_monotonic_seconds": onset + t - 0.02,
                    "target_id": target.name,
                    "target_x": target.x,
                    "target_y": target.y,
                    "block": block,
                    "presentation_order": order,
                    "phase": "validation" if block else "calibration",
                    "camera_frame_available": True,
                    "frame_timestamp_ns": stamp,
                    "camera_resolution": [1920, 1080],
                    "feature_status": "usable",
                    "gaze_status": "usable" if mapping else "not_calibrated",
                    "horizontal_feature": features.horizontal,
                    "vertical_feature": features.vertical,
                    "predicted_x": x,
                    "predicted_y": y,
                    "unavailable_reason": None,
                    "raw_geometry": geometry,
                    "geometry_error": None,
                }
            )
        return output

    observations = []
    for order, target in enumerate(CALIBRATION_TARGETS, 1):
        onset = order * 2.0
        samples = rows(target, [0.8 + n * 0.2 for n in range(5)], onset, 0, order)
        report["calibration_presentations"].append(
            {
                "order": order,
                "target_id": target.name,
                "target_x": target.x,
                "target_y": target.y,
                "onset_monotonic_seconds": onset,
                "end_monotonic_seconds": onset + 2,
                "samples": samples,
            }
        )
        observations.append(
            (target, [(s["horizontal_feature"], s["vertical_feature"]) for s in samples])
        )
    mapping, _ = fit_session_calibration(observations)
    report["mapping_coefficients"] = asdict(mapping)
    for trial in schedule():
        onset = 30 + trial.order * 4.25
        samples = rows(
            trial.target, (0.1, 0.8, 1.4, 1.5, 2, 2.9), onset, trial.block, trial.order, mapping
        )
        for row in samples:
            row.update(trial.identity())
        report["trials"].append(
            {
                **trial.identity(),
                "onset_monotonic_seconds": onset,
                "cue_onset_monotonic_seconds": onset - 0.75,
                "end_monotonic_seconds": onset + 3,
                "samples": samples,
            }
        )
    return report


def test_schedule_identity_and_non_gated_screens():
    assert schedule() == original_schedule()
    assert len(CALIBRATION_TARGETS) == 9 and len(schedule()) == 27
    for block in (1, 2, 3):
        assert len({t.target.name for t in schedule() if t.block == block}) == 9
    config = configuration()
    assert config["cue_seconds"] == 0.75 and config["target_seconds"] == 3.0
    assert config["transition_seconds"] == 0.5
    assert (
        config["calibration_settle_seconds"] == 0.8 and config["calibration_sample_seconds"] == 1.2
    )
    for trial in schedule():
        expected = (
            (0.2, 0.2)
            if (trial.target.x, trial.target.y) == (0.5, 0.5)
            else (1 - trial.target.x, 1 - trial.target.y)
        )
        assert (trial.cue_x, trial.cue_y) == pytest.approx(expected)
        assert not screen_content("target", trial).lines
        assert not screen_content("cue", trial).lines
    for state in ("success", "timeout", "reset_failed"):
        with pytest.raises(ValueError):
            screen_content(state)


@pytest.mark.parametrize("usable", (True, False))
def test_full_window_is_independent_of_gaze_and_preserves_sidecar(usable):
    now = [10.0]

    def measure():
        now[0] += 0.5
        return {
            "feature_status": "usable" if usable else "unavailable",
            "raw_geometry": {"marker": 1},
        }

    rows, end = collect_window(10, 3, 0, measure, lambda: None, lambda: None, lambda: now[0])
    assert end == 13 and len(rows) == 5
    assert all(r["raw_geometry"] == {"marker": 1} for r in rows)
    assert not any("success" in r or "timeout" in r for r in rows)


def test_selected_schema_and_exact_r0_reconstruction():
    geometry = record(0.2, 0.8)
    assert len(SELECTED_INDICES) == 54 and len(REQUIRED_INDICES) == 52
    assert set(geometry["landmarks"]) == {str(i) for i in SELECTED_INDICES}
    assert set(geometry["face_anchors"]) == {str(i) for i in FACE_ANCHOR_INDICES}
    features = reconstruct_r0(geometry)
    assert features.horizontal == pytest.approx(0.2)
    assert features.vertical == pytest.approx(0.06)
    left = geometry["eyes"]["left"]
    assert left["iris_center"]["z"] == pytest.approx(-0.02)
    assert left["corner_midpoint"]["x"] == pytest.approx(0.65)
    assert left["corner_span_px"] == pytest.approx(153.6)
    assert left["production_vertical"] == pytest.approx(features.vertical)
    assert left["outer_corner"] == geometry["landmarks"]["263"]
    assert left["inner_corner"] == geometry["landmarks"]["362"]
    assert not set(FACE_ANCHOR_INDICES) & set(
        i for eye in EYES.values() for i in eye["contour"] + eye["iris_ring"]
    )
    # Whitelisted numerical fields, no detector result/frame payload/478-point dump.
    assert set(geometry) == {
        "schema_version",
        "frame_timestamp_ns",
        "detector_timestamp_ms",
        "camera_resolution",
        "landmarks",
        "face_anchors",
        "eyes",
        "interocular_distance_px",
        "missing_required_indices",
        "missing_optional_indices",
        "missing_z_indices",
        "facial_transformation_matrix",
        "pose_transform_status",
    }


@pytest.mark.parametrize("depth", (True, False))
def test_depth_availability_is_explicit_and_optional(depth):
    native = detector_result(depth=depth)
    geometry = geometry_record(native, 1920, 1080, 100, 0)
    assert len(geometry["missing_z_indices"]) == (0 if depth else 54)
    assert (geometry["eyes"]["left"]["iris_center"]["z"] is not None) == depth
    assert reconstruct_r0(geometry).vertical == pytest.approx(0)
    assert geometry["facial_transformation_matrix"] is None
    assert geometry["pose_transform_status"] == "not_exposed"


def test_partial_optional_and_required_geometry_is_not_invented():
    native = detector_result()
    native.face_landmarks[0][473] = SimpleNamespace(x=float("nan"), y=0.5)
    native.face_landmarks[0][6] = SimpleNamespace(x=float("nan"), y=0.5)
    geometry = geometry_record(native, 1920, 1080, 100, 0)
    assert geometry["missing_optional_indices"] == [473]
    assert geometry["missing_required_indices"] == [6]
    assert geometry["landmarks"]["6"] is None
    assert geometry["eyes"]["left"]["detector_iris_center"] is None
    assert geometry_record(SimpleNamespace(face_landmarks=[]), 1920, 1080, 100, 0) is None


def test_optional_transform_is_copied_numerically_without_enabling_it():
    native = detector_result()
    native.facial_transformation_matrixes = [
        [[1 if a == b else 0 for b in range(4)] for a in range(4)]
    ]
    geometry = geometry_record(native, 1920, 1080, 100, 0)
    native.facial_transformation_matrixes[0][0][0] = 9
    assert geometry["facial_transformation_matrix"][0][0] == 1
    assert geometry["pose_transform_status"] == "available"


def test_same_native_result_reaches_production_conversion_once(monkeypatch):
    native = detector_result(0.8, 0.2)
    detectors = []

    def initialize(self, path):
        class Detector:
            calls = []

            def detect_for_video(self, image, timestamp):
                self.calls.append(timestamp)
                return native

            def close(self):
                pass

        detector = Detector()
        detector.calls = []
        detectors.append(detector)
        self._landmarker = detector
        self._last_timestamp_ms = -1
        self._cv2 = SimpleNamespace(COLOR_BGR2RGB=1, cvtColor=lambda payload, mode: payload)
        self._mp = SimpleNamespace(Image=lambda **kw: kw, ImageFormat=SimpleNamespace(SRGB=1))

    monkeypatch.setattr(MediaPipeFaceLandmarkExtractor, "__init__", initialize)
    baseline = MediaPipeFaceLandmarkExtractor("unused")
    tap = GeometryExtractor("unused")
    frame = CameraFrame(object(), 1920, 1080, 123_000_000)
    expected, actual = baseline.extract(frame), tap.extract(frame)
    assert actual == expected and detectors[0].calls == detectors[1].calls == [123]
    features = extract_binocular_features(*eye_geometry_from_observation(actual), 1920, 1080)
    assert features == reconstruct_r0(tap.last_geometry)
    native.face_landmarks = []
    assert tap.extract(frame).landmarks is None and tap.last_geometry is None
    assert detectors[1].calls == [123, 124]
    tap.close()


def test_frame_failure_does_not_reuse_previous_geometry():
    from eye_tracker.gaze.estimator import GazeUnavailable, UnavailableReason

    tap = SimpleNamespace(features=None, geometry=record(), geometry_error=None)
    row = geometry_sample_row(
        GazeUnavailable(UnavailableReason.MISSING_FEATURES), SimpleNamespace(last_frame=None), tap
    )
    assert row["raw_geometry"] is None and row["camera_resolution"] is None


def test_complete_capture_inspection_and_holdout_schema_only():
    report = capture()
    result = inspect_capture(report)
    assert result["session_role"] == "development"
    assert result["calibration_geometry_frames"] == 45
    assert result["validation_geometry_frames"] == 162
    assert result["complete_z_frames"] == 207 and result["pose_transform_frames"] == 0
    assert inspect_capture(report) == result
    holdout = capture("geometry-2")
    assert inspect_capture(holdout)["session_role"] == "holdout"
    assert "y_mae" not in inspect_capture(holdout)
    assert REPRESENTATIONS == ("R0", "R1", "R2")
    assert SESSION_ROLES == {"geometry-1": "development", "geometry-2": "holdout"}


@pytest.mark.parametrize(
    "mutation",
    ("protocol", "version", "trial", "short", "geometry", "raw", "r0", "timestamp", "role"),
)
def test_rejects_incompatible_incomplete_or_unreconstructable_capture(mutation):
    report = capture()
    row = report["trials"][0]["samples"][0]
    if mutation == "protocol":
        report["protocol_name"] = "fixed_window_gaze_diagnostic"
    if mutation == "version":
        report["protocol_version"] = 9
    if mutation == "trial":
        report["trials"].pop()
    if mutation == "short":
        report["trials"][0]["end_monotonic_seconds"] -= 0.01
    if mutation == "geometry":
        row["raw_geometry"] = None
    if mutation == "raw":
        row["raw_geometry"]["landmarks"]["6"] = None
    if mutation == "r0":
        row["raw_geometry"]["landmarks"]["474"]["x"] += 0.01
    if mutation == "timestamp":
        row["raw_geometry"]["frame_timestamp_ns"] += 1
    if mutation == "role":
        report["session_role"] = "holdout"
    with pytest.raises(ValueError):
        inspect_capture(report)


def test_absent_depth_does_not_silently_invalidate_capture():
    report = capture()
    for item in report["calibration_presentations"] + report["trials"]:
        for row in item["samples"]:
            g = row["raw_geometry"]
            for p in g["landmarks"].values():
                p["z"] = None
            # Re-extract derived copies so optional-field flags remain consistent.
            native = detector_result(item["target_x"], item["target_y"], depth=False)
            row["raw_geometry"] = geometry_record(
                native, 1920, 1080, row["frame_timestamp_ns"], g["detector_timestamp_ms"]
            )
    assert inspect_capture(report)["missing_z_frames"] == 207


def test_cli_only_predeclared_sessions_and_preregistration():
    args = parse_args(
        [
            "--participant",
            "cagri",
            "--session",
            "geometry-2",
            "--camera-index",
            "1",
            "--output",
            ".venv/new-geometry.json",
        ]
    )
    assert args.session == "geometry-2"
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--participant",
                "cagri",
                "--session",
                "live-1",
                "--camera-index",
                "1",
                "--output",
                ".venv/new-geometry.json",
            ]
        )
    from pathlib import Path

    prereg = Path("experiments/raw_geometry_gaze_diagnostic/PREREGISTRATION.md").read_text()
    assert all(f"## {name} —" in prereg for name in REPRESENTATIONS)
    assert "## R3" not in prereg
    assert "20%" in prereg and "25%" in prereg and "15%" in prereg


def test_runner_orchestration_preserves_geometry_and_json_resolution(monkeypatch):
    """Exercise all 9+27 presentations without camera/GUI/native dependencies."""
    import sys

    from experiments.raw_geometry_gaze_diagnostic import run as runner

    report = capture()
    report.update(
        calibration_presentations=[], trials=[], status="incomplete", ready_screen_used=False
    )
    now = [10.0]
    events = []
    monkeypatch.setattr(runner.time, "monotonic", lambda: now[0])
    cv = SimpleNamespace(
        WINDOW_NORMAL=1,
        WND_PROP_FULLSCREEN=2,
        WINDOW_FULLSCREEN=3,
        namedWindow=lambda *a: None,
        setWindowProperty=lambda *a: None,
        imshow=lambda *a: None,
        waitKey=lambda *a: ord(" "),
        getWindowImageRect=lambda *a: (0, 0, 1200, 700),
        destroyWindow=lambda *a: None,
    )
    monkeypatch.setitem(sys.modules, "cv2", cv)
    monkeypatch.setitem(
        sys.modules, "numpy", SimpleNamespace(full=lambda *a, **kw: None, uint8=int)
    )
    monkeypatch.setattr(runner, "draw_screen", lambda *a: None)
    monkeypatch.setattr(runner, "wait_ready", lambda *a: events.append("ready"))

    class Source:
        def __init__(self, index):
            pass

        def open(self):
            events.append("camera")

        def close(self):
            pass

    class Detector:
        def __init__(self, path):
            pass

        def __enter__(self):
            events.append("detector")
            return self

        def __exit__(self, *a):
            pass

    class Worker:
        def __init__(self, source, tap):
            self.source, self.mapping = source, None

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(runner, "OpenCVCameraSource", Source)
    monkeypatch.setattr(runner, "GeometryExtractor", Detector)
    monkeypatch.setattr(runner, "GeometryWorker", Worker)

    def collect(onset, duration, sample_start, worker, poll, end_display, rows):
        item = (
            report["calibration_presentations"][-1]
            if worker.mapping is None
            else report["trials"][-1]
        )
        for t in (sample_start + n * 0.2 for n in range(5)):
            stamp = round((onset + t - 0.01) * 1e9)
            geometry = record(item["target_x"], item["target_y"], stamp)
            features = reconstruct_r0(geometry)
            x, y = (
                worker.mapping.predict(features.horizontal, features.vertical)
                if worker.mapping
                else (None, None)
            )
            rows.append(
                {
                    "monotonic_timestamp_seconds": onset + t,
                    "trial_relative_seconds": t,
                    "measurement_started_monotonic_seconds": onset + t - 0.02,
                    "frame_timestamp_ns": stamp,
                    "camera_resolution": [1920, 1080],
                    "camera_frame_available": True,
                    "raw_geometry": geometry,
                    "geometry_error": None,
                    "feature_status": "usable",
                    "gaze_status": "usable" if worker.mapping else "not_calibrated",
                    "horizontal_feature": features.horizontal,
                    "vertical_feature": features.vertical,
                    "predicted_x": x,
                    "predicted_y": y,
                    "unavailable_reason": None,
                }
            )
            worker.source.reads += 1
            worker.source.resolution = (1920, 1080)  # Actual RecordingSource representation.
        now[0] = onset + duration
        end_display()
        return rows, now[0]

    def wait_fixed(duration, poll):
        onset = now[0]
        now[0] += duration
        return onset

    monkeypatch.setattr(runner, "collect_window", collect)
    monkeypatch.setattr(runner, "wait_fixed", wait_fixed)
    runner.collect_session(
        SimpleNamespace(
            participant="synthetic", session="geometry-1", camera_index=1, model="unused"
        ),
        report,
    )
    assert events[:3] == ["ready", "detector", "camera"]
    assert report["camera_resolution"] == [1920, 1080]
    assert inspect_capture(report)["validation_geometry_frames"] == 135
    assert len(report["trials"]) == 27 and all(
        t["end_monotonic_seconds"] - t["onset_monotonic_seconds"] == 3 for t in report["trials"]
    )


def test_unavailable_validation_attempts_are_preserved_and_counted():
    report = capture()
    for row in report["trials"][0]["samples"][:2]:
        row.update(
            feature_status="unavailable",
            gaze_status="unavailable",
            horizontal_feature=None,
            vertical_feature=None,
            predicted_x=None,
            predicted_y=None,
            raw_geometry=None,
            unavailable_reason="missing_features",
        )
    report["no_face_observations"] = 2
    result = inspect_capture(report)
    assert result["unavailable_validation_samples"] == 2
    assert result["missing_geometry_attempts"] == 2
    assert result["no_face_observations"] == 2
    assert len(report["trials"]) == 27


def test_interocular_derived_copy_must_match_raw_primitives():
    report = capture()
    report["trials"][0]["samples"][0]["raw_geometry"]["interocular_distance_px"] += 100
    with pytest.raises(ValueError, match="interocular"):
        inspect_capture(report)


def test_mixed_depth_and_invalid_optional_pose_are_explicit():
    native = detector_result()
    native.face_landmarks[0][474].z = float("nan")
    native.facial_transformation_matrixes = [[[1, 2]]]
    geometry = geometry_record(native, 1920, 1080, 123, 0)
    assert geometry["missing_z_indices"] == [474]
    assert geometry["eyes"]["left"]["iris_center"]["z"] is None
    assert geometry["pose_transform_status"] == "malformed"
    assert geometry["facial_transformation_matrix"] is None
    assert reconstruct_r0(geometry).vertical == pytest.approx(0)
