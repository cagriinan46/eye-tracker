"""Hardware-free checks for the Issue #42 validation protocol and calculations."""

import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from eye_tracker.gaze.estimator import GazeEstimate, GazeUnavailable, UnavailableReason
from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint
from eye_tracker.vision.eye_features import EyeFeatures


def harness():
    assert importlib.util.find_spec("validation") is not None
    assert importlib.util.find_spec("validation.real_calibration") is not None
    return importlib.import_module("validation.real_calibration")


def test_harness_import_resolves_to_repository_file() -> None:
    root = Path(__file__).resolve().parents[2]
    package_spec = importlib.util.find_spec("validation")
    try:
        module_spec = importlib.util.find_spec("validation.real_calibration")
    except ModuleNotFoundError:
        module_spec = None

    assert module_spec is not None, f"validation={package_spec!r}; sys.path={sys.path!r}"
    assert Path(module_spec.origin).resolve() == root / "validation" / "real_calibration.py"


def test_experiment_006_targets_are_distinct_and_validation_repeats_are_shuffled() -> None:
    module = harness()
    order = module.build_presentations(seed=42)

    assert len(order) == 25
    assert [(item.target.x, item.target.y) for item in order[:9]] == [
        (x, y) for y in (0.20, 0.50, 0.80) for x in (0.20, 0.50, 0.80)
    ]
    expected_validation = {
        (0.35, 0.35),
        (0.65, 0.35),
        (0.35, 0.65),
        (0.65, 0.65),
        (0.50, 0.35),
        (0.65, 0.50),
        (0.50, 0.65),
        (0.35, 0.50),
    }
    assert {(item.target.x, item.target.y) for item in order[9:]} == expected_validation
    assert all(
        sum(item.target == target for item in order[9:]) == 2
        for target in {item.target for item in order[9:]}
    )
    assert order == module.build_presentations(seed=42)
    assert order[9:] != module.build_presentations(seed=43)[9:]
    assert not expected_validation.intersection(
        {(item.target.x, item.target.y) for item in order[:9]}
    )


def test_calibration_uses_existing_per_axis_medians_and_fitter() -> None:
    module = harness()
    observations = []
    for item in module.build_presentations()[:9]:
        x, y = item.target.x, item.target.y
        observations.append((item.target, [(x - 0.01, y + 0.01)] * 4 + [(x + 0.2, y - 0.2)]))

    mapping, samples = module.fit_session_calibration(observations)

    assert len(samples) == 9
    assert samples[0].horizontal_feature == pytest.approx(0.19)
    assert samples[0].vertical_feature == pytest.approx(0.21)
    assert (samples[0].target_x, samples[0].target_y) == (0.2, 0.2)
    assert mapping.predict(0.34, 0.66) == pytest.approx((0.35, 0.65))


def test_calibration_rejects_protocol_insufficient_samples() -> None:
    module = harness()
    target = module.build_presentations()[0].target

    with pytest.raises(ValueError, match="five usable"):
        module.fit_session_calibration([(target, [(0.2, 0.3)] * 4)])


def test_held_out_metrics_use_separate_trials_and_experiment_error_definitions() -> None:
    module = harness()
    target = module.build_presentations()[9].target
    trial = module.TrialEstimate(target, 1, (GazeEstimate(0.40, 0.30),) * 5)

    report = module.summarize_held_out([trial], window_width=1000, window_height=500)

    item = report["trials"][0]
    assert item["target_x"] == target.x
    assert item["target_y"] == target.y
    assert item["horizontal_absolute_error"] == pytest.approx(abs(0.40 - target.x))
    assert item["vertical_absolute_error"] == pytest.approx(abs(0.30 - target.y))
    assert item["normalized_error"] == pytest.approx(
        ((0.40 - target.x) ** 2 + (0.30 - target.y) ** 2) ** 0.5
    )
    assert item["pixel_equivalent_error"] == pytest.approx(
        (((0.40 - target.x) * 1000) ** 2 + ((0.30 - target.y) * 500) ** 2) ** 0.5
    )
    assert report["summary"]["mean_signed_x_bias"] == pytest.approx(0.40 - target.x)
    assert report["summary"]["mean_signed_y_bias"] == pytest.approx(0.30 - target.y)


def test_trial_aggregation_uses_median_and_requires_five_available_estimates() -> None:
    module = harness()
    target = module.build_presentations()[9].target
    trial = module.TrialEstimate(
        target,
        1,
        tuple(
            GazeEstimate(x, y) for x, y in ((0.1, 0.9), (0.2, 0.8), (0.3, 0.7), (0.4, 0.6), (9, -9))
        ),
    )

    report = module.summarize_held_out([trial], 1000, 500)

    assert report["trials"][0]["predicted_x"] == pytest.approx(0.3)
    assert report["trials"][0]["predicted_y"] == pytest.approx(0.7)
    with pytest.raises(ValueError, match="five usable"):
        module.summarize_held_out([module.TrialEstimate(target, 1, trial.estimates[:4])], 1000, 500)


def test_percentile_and_spatial_ordering_match_experiment_006_definitions() -> None:
    module = harness()
    assert module.percentile([0, 10, 20, 30, 40], 95) == pytest.approx(38)
    target_a = module.Target("A", 0.35, 0.35)
    target_b = module.Target("B", 0.65, 0.65)
    report = module.summarize_held_out(
        [
            module.TrialEstimate(target_a, 1, (GazeEstimate(0.4, 0.4),) * 5),
            module.TrialEstimate(target_a, 2, (GazeEstimate(0.3, 0.3),) * 5),
            module.TrialEstimate(target_b, 1, (GazeEstimate(0.7, 0.7),) * 5),
            module.TrialEstimate(target_b, 2, (GazeEstimate(0.6, 0.6),) * 5),
        ],
        1000,
        500,
    )

    assert report["spatial_ordering"] == {
        "x": {"consistent_pairs": 1, "total_pairs": 1},
        "y": {"consistent_pairs": 1, "total_pairs": 1},
    }


def test_calibration_feature_collection_composes_existing_vision_functions() -> None:
    module = harness()
    from eye_tracker.vision.eye_topology import _LEFT_CONTOUR, _RIGHT_CONTOUR

    points = [NormalizedPoint(0.5, 0.5) for _ in range(478)]
    for contour, center_x, corners, upper, lower, iris in (
        (_LEFT_CONTOUR, 0.3, (263, 362), 386, 374, (474, 475, 476, 477)),
        (_RIGHT_CONTOUR, 0.7, (33, 133), 159, 145, (469, 470, 471, 472)),
    ):
        for index in contour:
            points[index] = NormalizedPoint(center_x, 0.3)
        points[corners[0]] = NormalizedPoint(center_x - 0.1, 0.3)
        points[corners[1]] = NormalizedPoint(center_x + 0.1, 0.3)
        points[upper] = NormalizedPoint(center_x, 0.28)
        points[lower] = NormalizedPoint(center_x, 0.32)
        for index in iris:
            points[index] = NormalizedPoint(center_x, 0.3)

    class Source:
        def read(self):
            return CameraFrame(object(), 1000, 500, 123)

    class Extractor:
        def extract(self, frame):
            assert frame.width == 1000
            return LandmarkObservation(123, tuple(points))

    result = module.collect_features_once(Source(), Extractor())

    assert result.horizontal == pytest.approx(0.5)
    assert result.vertical == pytest.approx(0.0)


def test_calibration_feature_collection_keeps_missing_frame_unavailable() -> None:
    module = harness()

    class Source:
        def read(self):
            return None

    class Extractor:
        def extract(self, frame):
            pytest.fail("extractor must not run without a frame")

    assert module.collect_features_once(Source(), Extractor()) == GazeUnavailable(
        UnavailableReason.MISSING_FEATURES
    )


def test_collection_discards_settling_frames_and_counts_unavailable_samples() -> None:
    module = harness()
    presentation = module.build_presentations()[0]
    ticks = iter(i * 0.1 for i in range(50))
    calls = 0

    def measure():
        nonlocal calls
        calls += 1
        if calls == 10:
            return GazeUnavailable(UnavailableReason.MISSING_FEATURES)
        return EyeFeatures(float(calls), 0.0)

    samples, counts = module.collect_presentation(
        presentation,
        measure,
        lambda _presentation, _sampling, _remaining: False,
        clock=lambda: next(ticks),
    )

    assert all(item.horizontal >= 8 for item in samples)
    assert counts["sampling_attempts"] == len(samples) + 1
    assert counts["unavailable"]["missing_features"] == 1
    assert len(samples) >= 5


def test_collection_cancellation_does_not_return_partial_samples() -> None:
    module = harness()
    presentation = module.build_presentations()[0]
    ticks = iter(i * 0.1 for i in range(50))

    with pytest.raises(InterruptedError, match="cancelled"):
        module.collect_presentation(
            presentation,
            lambda: pytest.fail("measurement must not run after cancellation"),
            lambda _presentation, _sampling, _remaining: True,
            clock=lambda: next(ticks),
        )


def test_validation_cli_exposes_configurable_camera_without_hardware() -> None:
    root = Path(__file__).resolve().parents[2]
    environment = {**os.environ, "PYTHONPATH": str(root / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "validation.real_calibration", "--help"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--camera-index" in result.stdout
    assert "--model" in result.stdout


def test_missing_model_fails_before_camera_access(tmp_path) -> None:
    root = Path(__file__).resolve().parents[2]
    environment = {**os.environ, "PYTHONPATH": str(root / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "validation.real_calibration",
            "--camera-index",
            "1",
            "--model",
            str(tmp_path / "missing.task"),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "model not found" in result.stderr.lower()


def test_calibration_fit_is_reported_separately_from_held_out_trials() -> None:
    module = harness()
    observations = []
    for item in module.build_presentations()[:9]:
        target = item.target
        observations.append((target, [(target.x, target.y)] * 5))
    mapping, samples = module.fit_session_calibration(observations)

    result = module.summarize_calibration_fit(mapping, observations, samples, 1000, 500)

    assert len(result["trials"]) == 9
    assert result["summary"]["mean_normalized_error"] == pytest.approx(0.0, abs=1e-12)
    assert all(item["target_id"].startswith("C-") for item in result["trials"])


class _FakeWindowCv2:
    WINDOW_NORMAL = 0
    WND_PROP_FULLSCREEN = 1
    WINDOW_FULLSCREEN = 1

    def __init__(self, rect: tuple[int, int, int, int]) -> None:
        self.rect = rect
        self.shown = []
        self.waits = []

    def namedWindow(self, _window, _flags) -> None:
        pass

    def setWindowProperty(self, _window, _prop, _value) -> None:
        pass

    def imshow(self, _window, image) -> None:
        self.shown.append(image.shape)

    def waitKey(self, delay: int) -> int:
        self.waits.append(delay)
        return -1

    def getWindowImageRect(self, _window):
        return self.rect


def test_screen_size_parser_accepts_logical_points_only() -> None:
    module = harness()
    assert module.parse_screen_size("1512x982") == (1512, 982)
    assert module.parse_screen_size("1512X982") == (1512, 982)
    for text in ("1512", "0x982", "-1x982", "axb", "1x2x3"):
        with pytest.raises(module.argparse.ArgumentTypeError):
            module.parse_screen_size(text)
    assert module._parse_args(["--camera-index", "0"]).screen_size is None
    args = module._parse_args(["--camera-index", "0", "--screen-size", "1512x982"])
    assert args.screen_size == (1512, 982)
    with pytest.raises(SystemExit):
        module._parse_args(["--camera-index", "0", "--screen-size", "big"])


def test_target_window_keeps_legacy_canvas_without_screen_size() -> None:
    np = pytest.importorskip("numpy")
    module = harness()
    cv2 = _FakeWindowCv2((0, 0, 1200, 700))

    assert module.open_target_window(cv2, np, "w", None) == (1200, 700)
    assert cv2.shown == [(700, 1200, 3)]
    assert cv2.waits == [1]


def test_target_window_draws_requested_full_screen(monkeypatch) -> None:
    np = pytest.importorskip("numpy")
    module = harness()
    monkeypatch.setattr(module, "FULL_SCREEN_SETTLE_SECONDS", 0.0)
    cv2 = _FakeWindowCv2((0, 0, 1512, 982))

    assert module.open_target_window(cv2, np, "w", (1512, 982)) == (1512, 982)
    assert cv2.shown == [(982, 1512, 3)]


def test_target_window_rejects_partial_or_unknown_area(monkeypatch) -> None:
    np = pytest.importorskip("numpy")
    module = harness()
    monkeypatch.setattr(module, "FULL_SCREEN_SETTLE_SECONDS", 0.0)

    with pytest.raises(RuntimeError, match="not the requested"):
        module.open_target_window(_FakeWindowCv2((0, 0, 1200, 700)), np, "w", (1512, 982))
    with pytest.raises(RuntimeError, match="Could not determine"):
        module.open_target_window(_FakeWindowCv2((0, 0, 0, 0)), np, "w", None)
