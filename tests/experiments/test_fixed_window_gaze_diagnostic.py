"""Deterministic fixed-window recording and representation diagnostics."""

from copy import deepcopy

import pytest

from experiments.fixed_window_gaze_diagnostic.analysis import (
    analyze_session,
    compare_sessions,
    summarize_trial,
)
from experiments.fixed_window_gaze_diagnostic.protocol import (
    CALIBRATION_TARGETS,
    CUE_SECONDS,
    TARGET_SECONDS,
    TRANSITION_SECONDS,
    configuration,
    schedule,
    screen_content,
)
from experiments.fixed_window_gaze_diagnostic.run import collect_window


def sample(t, h, v, x=None, y=None):
    return {
        "trial_relative_seconds": t,
        "feature_status": "usable" if h is not None else "unavailable",
        "horizontal_feature": h,
        "vertical_feature": v,
        "gaze_status": "usable"
        if x is not None
        else "not_calibrated"
        if h is not None
        else "unavailable",
        "predicted_x": x,
        "predicted_y": y,
        "unavailable_reason": None if h is not None else "missing_features",
    }


def capture(shift=0.0):
    """Analytic h=x, v=-y calibration with controlled validation block drift."""
    cal = []
    for order, target in enumerate(CALIBRATION_TARGETS, 1):
        rows = [sample(0.8 + n * 0.2, target.x, -target.y) for n in range(5)]
        for row in rows:
            row.update(
                monotonic_timestamp_seconds=order * 2.0 + row["trial_relative_seconds"],
                target_id=target.name,
                target_x=target.x,
                target_y=target.y,
                block=0,
            )
        cal.append(
            {
                "order": order,
                "target_id": target.name,
                "target_x": target.x,
                "target_y": target.y,
                "onset_monotonic_seconds": order * 2.0,
                "end_monotonic_seconds": order * 2.0 + 2.0,
                "samples": rows,
            }
        )
    trials = []
    for trial in schedule():
        v = -trial.target.y + shift + 0.01 * (trial.block - 1)
        onset = 30 + trial.order * 4.25
        rows = [
            sample(t, trial.target.x, v, trial.target.x, -v) for t in (0.1, 0.8, 1.4, 1.5, 2.0, 2.9)
        ]
        for row in rows:
            row.update(
                monotonic_timestamp_seconds=onset + row["trial_relative_seconds"],
                **trial.identity(),
            )
        trials.append(
            {
                **trial.identity(),
                "cue_onset_monotonic_seconds": onset - 0.75,
                "onset_monotonic_seconds": onset,
                "end_monotonic_seconds": onset + 3.0,
                "samples": rows,
            }
        )
    return {
        **configuration(),
        "participant": "synthetic",
        "session": "diagnostic-1",
        "status": "completed",
        "ready_screen_used": True,
        "camera_index": 1,
        "camera_resolution": [1920, 1080],
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": -1.0,
            "y_intercept": 0.0,
        },
        "failed_camera_reads": 0,
        "no_face_observations": 0,
        "calibration_presentations": cal,
        "trials": trials,
    }


def test_schedule_and_target_only_screens():
    trials = schedule()
    assert len(CALIBRATION_TARGETS) == 9
    assert len(trials) == 27 and trials == schedule()
    for block in (1, 2, 3):
        assert len({t.target.name for t in trials if t.block == block}) == 9
    assert CUE_SECONDS == 0.75 and TARGET_SECONDS == 3 and TRANSITION_SECONDS == 0.5
    for trial in trials:
        assert (trial.cue_x, trial.cue_y) != (trial.target.x, trial.target.y)
        for phase in ("cue", "target"):
            content = screen_content(phase, trial)
            assert content.target is not None and not content.lines
        assert screen_content("transition").target is None
    assert "SPACE" in screen_content("ready").lines[0]
    for phase in ("success", "timeout", "reset_failed"):
        with pytest.raises(ValueError):
            screen_content(phase)


class Clock:
    now = 10.0

    def __call__(self):
        return self.now


@pytest.mark.parametrize("available", [True, False])
def test_fixed_window_never_ends_on_prediction(available):
    clock = Clock()
    ended = []

    def measure():
        clock.now += 0.5
        return sample(0, 0.5 if available else None, 0.5 if available else None)

    rows, end = collect_window(
        10.0, 3.0, 0.0, measure, lambda: None, lambda: ended.append(clock.now), clock
    )
    assert clock.now == 13.0 and end == 13.0 and ended == [13.0]
    assert [r["trial_relative_seconds"] for r in rows] == [0.5, 1, 1.5, 2, 2.5]
    assert all("outcome" not in r for r in rows)


def test_recording_overshoot_is_observed_not_used_to_extend_window():
    clock = Clock()

    def measure():
        clock.now += 2
        return sample(0, 0.5, 0.5)

    rows, end = collect_window(10, 3, 0, measure, lambda: None, lambda: None, clock)
    assert len(rows) == 1 and end == 14


def test_robust_summary_and_halves_keep_raw_unclipped_values():
    rows = [
        sample(t, h, v, h, v) for t, h, v in ((0.2, 1, 2), (1.0, 2, 4), (1.5, 3, 6), (2.9, 4, 8))
    ]
    result = summarize_trial(rows, 0.5, 0.5)
    assert result["features"]["horizontal"]["median"] == 2.5
    assert result["features"]["horizontal"]["mad"] == 1
    assert result["features"]["horizontal"]["iqr"] == 1.5
    assert result["temporal"]["vertical"]["half_shift"] == 4
    assert result["screen"]["median_predicted_y"] == 5
    assert result["screen"]["y_mae"] == 4.5
    assert (
        summarize_trial([sample(0.2, None, None)], 0.5, 0.5)["features"]["vertical"]["median"]
        is None
    )


def test_transfer_order_repeatability_and_groups():
    result = analyze_session(capture(0.03))
    assert result["feature_levels"]["vertical"]["calibration_direction"] == -1
    assert all(row["ordered"] for row in result["feature_levels"]["vertical"]["validation"])
    assert len(result["transfer"]) == 9
    assert result["transfer"][0]["vertical"]["signed_shift"] == pytest.approx(0.04)
    assert result["repeatability"][0]["vertical"]["maximum_shift"] == pytest.approx(0.02)
    assert result["repeatability"][0]["vertical"]["directional"] is True
    assert result["mapping_residuals"]["all"]["y_mae"] == pytest.approx(0.04)
    assert len(result["mapping_residuals"]["by_target"]) == 9
    assert len(result["mapping_residuals"]["by_row"]) == 3
    assert len(result["mapping_residuals"]["by_column"]) == 3
    assert len(result["mapping_residuals"]["by_block"]) == 3
    assert analyze_session(capture(0.03)) == result


def test_session_comparison_keeps_sessions_separate():
    first, second = capture(0.03), capture(0.05)
    second["session"] = "diagnostic-2"
    comparison = compare_sessions([first, second])
    assert len(comparison["sessions"]) == 2 and len(comparison["target_differences"]) == 9
    assert comparison["target_differences"][0]["vertical_median_delta"] == pytest.approx(0.02)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(protocol_version=2),
        lambda r: r.update(protocol_name="intentional_gaze_targeting"),
        lambda r: r.update(status="invalid_incomplete_run"),
        lambda r: r["trials"].pop(),
        lambda r: r["trials"].__setitem__(1, deepcopy(r["trials"][0])),
        lambda r: r["calibration_presentations"][0]["samples"].pop(),
        lambda r: r["trials"][0].update(end_monotonic_seconds=0),
        lambda r: r["trials"][0]["samples"][0].update(trial_relative_seconds=3),
        lambda r: r["trials"][0]["samples"][0].update(predicted_y=0),
        lambda r: r.update(
            mapping_coefficients={"x_slope": 2, "x_intercept": 0, "y_slope": -1, "y_intercept": 0}
        ),
    ],
)
def test_rejects_incomplete_or_incompatible_capture(mutation):
    report = capture()
    mutation(report)
    with pytest.raises(ValueError):
        analyze_session(report)


def test_nonblocking_empty_measurements_cannot_delay_target_end():
    clock = Clock()
    removed = []

    def poll():
        clock.now += 0.25

    rows, end = collect_window(
        10, 3, 0, lambda: None, poll, lambda: removed.append(clock.now), clock
    )
    assert not rows and end == 13 and removed == [13]


def test_queue_drain_keeps_completed_in_window_samples_only():
    clock = Clock()

    class Queue:
        def __call__(self):
            return None

        def drain(self):
            for started, completed in ((9.9, 10.2), (10.1, 10.5), (12.5, 13.1)):
                yield {
                    **sample(0, 0.5, 0.5),
                    "measurement_started_monotonic_seconds": started,
                    "monotonic_timestamp_seconds": completed,
                }

    def poll():
        clock.now += 0.5

    rows, _ = collect_window(10, 3, 0, Queue(), poll, lambda: None, clock)
    assert len(rows) == 1 and rows[0]["trial_relative_seconds"] == 0.5


def test_ready_gate_and_cancel():
    from experiments.fixed_window_gaze_diagnostic.run import wait_ready

    class Keys:
        def __init__(self, keys):
            self.keys = iter(keys)

        def waitKey(self, delay):
            return next(self.keys)

    shown = []
    wait_ready(Keys([0, ord(" ")]), lambda: shown.append(True))
    assert shown == [True]
    with pytest.raises(InterruptedError):
        wait_ready(Keys([27]), lambda: None)


def test_unavailable_mapping_has_no_invented_zero_error():
    report = capture()
    for row in report["trials"][0]["samples"]:
        row.update(
            feature_status="unavailable",
            horizontal_feature=None,
            vertical_feature=None,
            gaze_status="unavailable",
            predicted_x=None,
            predicted_y=None,
            unavailable_reason="missing_features",
        )
    result = analyze_session(report)
    assert result["trials"][0]["summary"]["screen"]["y_mae"] is None
    assert result["signal_limitations"] == [1]
    assert result["availability"]["unavailable"] == 6


def test_reversed_or_flat_calibration_does_not_invent_order_direction():
    report = capture()
    # Geometry remains fit-able but row medians are not monotonic.
    from dataclasses import asdict

    from validation.real_calibration import fit_session_calibration

    values = {0.2: 0.4, 0.5: 0.8, 0.8: 0.5}
    observations = []
    for item, target in zip(report["calibration_presentations"], CALIBRATION_TARGETS, strict=True):
        for row in item["samples"]:
            row["vertical_feature"] = values[target.y]
        observations.append((target, [(target.x, values[target.y])] * 5))
    mapping, _ = fit_session_calibration(observations)
    report["mapping_coefficients"] = asdict(mapping)
    for trial in report["trials"]:
        for row in trial["samples"]:
            row["predicted_x"], row["predicted_y"] = mapping.predict(
                row["horizontal_feature"], row["vertical_feature"]
            )
    result = analyze_session(report)
    assert result["feature_levels"]["vertical"]["calibration_direction"] is None
    assert all(row["ordered"] is None for row in result["feature_levels"]["vertical"]["validation"])


def test_complete_runner_uses_ready_before_camera_and_records_every_window(monkeypatch):
    """Exercise orchestration without importing OpenCV/NumPy or opening a camera."""
    import sys
    from types import SimpleNamespace

    from experiments.fixed_window_gaze_diagnostic import run as runner

    clock = Clock()
    events = []
    screen = SimpleNamespace(content=None)

    def imshow(window, canvas):
        screen.content = canvas
        if getattr(canvas, "lines", ()):
            events.append("ready")

    def wait_key(delay):
        clock.now += 0.01
        return ord(" ") if delay == 30 else -1

    cv2 = SimpleNamespace(
        WINDOW_NORMAL=0,
        WND_PROP_FULLSCREEN=0,
        WINDOW_FULLSCREEN=0,
        namedWindow=lambda *args: None,
        setWindowProperty=lambda *args: None,
        imshow=imshow,
        waitKey=wait_key,
        getWindowImageRect=lambda *args: (0, 0, 1200, 700),
        destroyWindow=lambda *args: None,
    )
    monkeypatch.setitem(sys.modules, "cv2", cv2)
    monkeypatch.setitem(
        sys.modules, "numpy", SimpleNamespace(full=lambda *args, **kw: None, uint8=int)
    )
    monkeypatch.setattr(runner, "draw_screen", lambda cv, np, content, w, h: content)
    monkeypatch.setattr(runner.time, "monotonic", clock)
    # Default arguments capture the original clock; replace only that dependency.
    original_collect, original_wait = runner.collect_window, runner.wait_fixed
    monkeypatch.setattr(
        runner, "collect_window", lambda *args, **kw: original_collect(*args, clock=clock, **kw)
    )
    monkeypatch.setattr(runner, "wait_fixed", lambda *args: original_wait(*args, clock=clock))

    class Camera:
        def __init__(self, index):
            pass

        def open(self):
            events.append("camera_open")

        def close(self):
            pass

    class Detector:
        def __init__(self, model):
            events.append("model_init")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Worker:
        def __init__(self, source, tap):
            self.source, self.mapping = source, None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __call__(self):
            target = screen.content.target
            self.source.resolution = (1920, 1080)
            self.source.reads += 1
            h, v = target.x, -target.y
            x, y = self.mapping.predict(h, v) if self.mapping else (None, None)
            return {
                **sample(0, h, v, x, y),
                "measurement_started_monotonic_seconds": clock.now,
                "monotonic_timestamp_seconds": clock.now,
            }

    monkeypatch.setattr(runner, "OpenCVCameraSource", Camera)
    monkeypatch.setattr(runner, "MediaPipeFaceLandmarkExtractor", Detector)
    monkeypatch.setattr(runner, "MeasurementWorker", Worker)
    report = {
        **configuration(),
        "participant": "synthetic",
        "session": "diagnostic-1",
        "camera_index": 1,
        "calibration_presentations": [],
        "trials": [],
    }
    runner.collect_session(
        SimpleNamespace(
            camera_index=1, model=None, participant="synthetic", session="diagnostic-1"
        ),
        report,
    )
    assert events[:3] == ["ready", "model_init", "camera_open"]
    assert len(report["calibration_presentations"]) == 9 and len(report["trials"]) == 27
    assert all(
        3 <= t["end_monotonic_seconds"] - t["onset_monotonic_seconds"] < 3.05
        for t in report["trials"]
    )
    assert all(len(t["samples"]) > 200 for t in report["trials"])
    assert all("outcome" not in t for t in report["trials"])
    assert abs(analyze_session(report)["mapping_residuals"]["all"]["y_mae"]) < 1e-12


def test_measurement_worker_queue_does_not_block_and_propagates_failure():
    from experiments.fixed_window_gaze_diagnostic.run import MeasurementWorker

    worker = MeasurementWorker(None, None)
    assert worker() is None
    row = sample(0.1, 0.2, 0.3)
    worker.queue.put(row)
    assert worker() == row
    worker.queue.put(RuntimeError("synthetic camera failure"))
    with pytest.raises(RuntimeError, match="camera/pipeline worker failed"):
        worker()


def test_sample_sidecar_does_not_reuse_features_after_failed_read():
    from types import SimpleNamespace

    from experiments.fixed_window_gaze_diagnostic.run import sample_row
    from eye_tracker.gaze.estimator import GazeUnavailable, UnavailableReason
    from eye_tracker.vision.eye_features import EyeFeatures

    row = sample_row(
        GazeUnavailable(UnavailableReason.MISSING_FEATURES),
        SimpleNamespace(last_frame=None),
        SimpleNamespace(features=EyeFeatures(0.1, 0.2)),
    )
    assert row["horizontal_feature"] is None and row["vertical_feature"] is None
    assert not row["camera_frame_available"] and row["feature_status"] == "unavailable"
