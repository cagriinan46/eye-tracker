"""Capture one intentional gaze targeting session with a timed fixation cue."""

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import median

from experiments.coarse_gaze_targeting_validation.protocol import cursor_pixel
from experiments.intentional_gaze_targeting.analysis import (
    CueFlow,
    analyze_session,
    summarize_target,
)
from experiments.intentional_gaze_targeting.protocol import (
    CUE_ASSIGNMENT,
    FEEDBACK_SECONDS,
    FIXATION_CUE_SECONDS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGET_DWELL_SECONDS,
    TARGET_HALF_HEIGHT,
    TARGET_HALF_WIDTH,
    TARGET_TIMEOUT_SECONDS,
    TARGETS,
    ScreenContent,
    Trial,
    schedule,
    screen_content,
)
from eye_tracker.app.gaze_pipeline import process_gaze_frame
from eye_tracker.gaze.estimator import GazeEstimate, GazeUnavailable
from eye_tracker.vision.camera import OpenCVCameraSource
from eye_tracker.vision.eye_features import extract_binocular_features
from eye_tracker.vision.eye_topology import eye_geometry_from_observation
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor
from validation.real_calibration import (
    CALIBRATION_TARGETS,
    MIN_USABLE_SAMPLES,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    Presentation,
    RecordingExtractor,
    RecordingSource,
    collect_features_once,
    collect_presentation,
    fit_session_calibration,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", choices=("cagri",), required=True)
    parser.add_argument("--session", choices=("live-1", "live-2", "live-3"), required=True)
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if (
        not args.output.resolve().is_relative_to(Path(".venv").resolve())
        or args.output.suffix != ".json"
    ):
        parser.error("output must be a JSON path under ignored .venv")
    return args


def _invalid_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.invalid.json")


def _abort_key(key: int) -> bool:
    return key & 0xFF in (ord("q"), 27)


class ObservationTap:
    """Cache the observation consumed by the unchanged production gaze path."""

    def __init__(self, extractor: RecordingExtractor) -> None:
        self.extractor = extractor
        self.last_observation = None

    def extract(self, frame):
        self.last_observation = self.extractor.extract(frame)
        return self.last_observation


def draw_screen(cv2, np, content: ScreenContent, width: int, height: int, prediction=None):
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    if content.target is not None:
        point = content.target
        center = (round(point.x * width), round(point.y * height))
        if content.show_region:
            top_left = (
                round((point.x - TARGET_HALF_WIDTH) * width),
                round((point.y - TARGET_HALF_HEIGHT) * height),
            )
            bottom_right = (
                round((point.x + TARGET_HALF_WIDTH) * width),
                round((point.y + TARGET_HALF_HEIGHT) * height),
            )
            cv2.rectangle(canvas, top_left, bottom_right, (75, 105, 75), -1)
            cv2.rectangle(canvas, top_left, bottom_right, (100, 210, 100), 3)
        cv2.circle(canvas, center, 24, (255, 255, 255), 3)
        cv2.circle(canvas, center, 7, (0, 190, 255), -1)
        if content.show_cursor and prediction is not None:
            pixel = cursor_pixel(prediction.x, prediction.y, width, height)
            if pixel is not None:
                cv2.circle(canvas, pixel, 11, (255, 190, 0), -1)
                cv2.circle(canvas, pixel, 13, (255, 255, 255), 2)
    else:
        line_height = 48
        first_baseline = height // 2 - (len(content.lines) - 1) * line_height // 2
        for index, line in enumerate(content.lines):
            scale = 1.0 if len(content.lines) == 1 else 0.7
            text_width = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)[0][0]
            cv2.putText(
                canvas,
                line,
                (max(0, (width - text_width) // 2), first_baseline + index * line_height),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                (225, 225, 225),
                2,
            )
    return canvas


def _ready(cv2, np, window: str, width: int, height: int, phase: str) -> None:
    canvas = draw_screen(cv2, np, screen_content(phase), width, height)
    while True:
        cv2.imshow(window, canvas)
        key = cv2.waitKey(30) & 0xFF
        if key == ord(" "):
            return
        if _abort_key(key):
            raise InterruptedError("run cancelled at ready screen")


def _show(cv2, window: str, canvas, phase: str) -> None:
    cv2.imshow(window, canvas)
    if _abort_key(cv2.waitKey(1)):
        raise InterruptedError(f"run cancelled during {phase}")


def _feature_sidecar(recorded_source: RecordingSource, observation_tap: ObservationTap):
    frame = recorded_source.last_frame
    observation = observation_tap.last_observation
    if frame is None or observation is None:
        return None
    try:
        geometry = eye_geometry_from_observation(observation)
        if geometry is None:
            return None
        return extract_binocular_features(*geometry, frame.width, frame.height)
    except ValueError:
        return None


def _sample_row(args, trial, phase, began, observed_at, result, source, tap, state):
    frame = source.last_frame
    features = _feature_sidecar(source, tap)
    prediction = (result.x, result.y) if isinstance(result, GazeEstimate) else None
    inside, dwell = state.observe(observed_at, prediction)
    row = {
        "participant": args.participant,
        "session": args.session,
        **trial.identity(),
        "phase": phase,
        "monotonic_seconds": observed_at - began,
        "frame_timestamp_ns": frame.timestamp_ns if frame is not None else None,
        "frame_available": frame is not None,
        "status": "usable" if prediction is not None else "unavailable",
        "unavailable_reason": result.reason.value if isinstance(result, GazeUnavailable) else None,
        "raw_predicted_x": result.x if prediction is not None else None,
        "raw_predicted_y": result.y if prediction is not None else None,
        "horizontal_feature": features.horizontal if features is not None else None,
        "vertical_feature": features.vertical if features is not None else None,
        "active_dwell_seconds": dwell,
    }
    row[f"inside_{phase}"] = inside
    return row


def _capture_phase(
    cv2, np, window, dimensions, args, trial, phase, state, mapping, source, tap, began
):
    width, height = dimensions
    content = screen_content(phase, trial)
    rows = []
    previous_prediction = None
    while state.outcome is None:
        _show(cv2, window, draw_screen(cv2, np, content, width, height, previous_prediction), phase)
        if time.monotonic() >= state.onset + state.timeout_seconds:
            state.expire(time.monotonic())
            break
        result = process_gaze_frame(source, tap, mapping)
        observed_at = time.monotonic()
        if observed_at > state.onset + state.timeout_seconds:
            state.expire(observed_at)
            break
        rows.append(_sample_row(args, trial, phase, began, observed_at, result, source, tap, state))
        previous_prediction = result if isinstance(result, GazeEstimate) else None
    return rows


def _feedback(cv2, np, window, dimensions, outcome):
    width, height = dimensions
    canvas = draw_screen(cv2, np, screen_content(outcome), width, height)
    began = time.monotonic()
    while time.monotonic() - began < FEEDBACK_SECONDS:
        _show(cv2, window, canvas, "feedback")


def _target_record(target):
    return {"target_id": target.name, "target_x": target.x, "target_y": target.y}


def collect_session(args: argparse.Namespace) -> dict:
    """Use standard calibration and the unchanged production gaze processing path."""
    import cv2
    import numpy as np

    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window = f"Intentional gaze targeting {args.participant}/{args.session} - q / Esc"
    window_created = False
    calibration_presentations = []
    calibration_observations = []
    target_samples = []
    trials = []
    try:
        with MediaPipeFaceLandmarkExtractor(args.model) as detector:
            recorded_extractor = RecordingExtractor(detector)
            tap = ObservationTap(recorded_extractor)
            source.open()
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            window_created = True
            cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(window, np.full((700, 1200, 3), 24, dtype=np.uint8))
            cv2.waitKey(1)
            _, _, width, height = cv2.getWindowImageRect(window)
            if width <= 0 or height <= 0:
                raise RuntimeError("Could not determine target-window image area")
            dimensions = (width, height)
            _ready(cv2, np, window, width, height, "calibration_ready")
            began = time.monotonic()
            for position, target in enumerate(CALIBRATION_TARGETS, start=1):
                presentation = Presentation("calibration", target, 1)
                calibration_trial = Trial(0, 0, target, 0.0, 0.0)

                def show(current, sampling: bool, remaining: float) -> bool:
                    cv2.imshow(
                        window,
                        draw_screen(
                            cv2, np, screen_content("calibration", calibration_trial), width, height
                        ),
                    )
                    return _abort_key(cv2.waitKey(1))

                collected, counts = collect_presentation(
                    presentation,
                    lambda: collect_features_once(recorded_source, tap),
                    show,
                )
                calibration_observations.append(
                    (target, [(feature.horizontal, feature.vertical) for feature in collected])
                )
                calibration_presentations.append(
                    {
                        "order": position,
                        **_target_record(target),
                        "usable_samples": len(collected),
                        "sampling_attempts": counts["sampling_attempts"],
                        "unavailable": counts["unavailable"],
                        "median_horizontal_feature": median(item.horizontal for item in collected),
                        "median_vertical_feature": median(item.vertical for item in collected),
                    }
                )
            mapping, _ = fit_session_calibration(calibration_observations)
            _ready(cv2, np, window, width, height, "targeting_ready")
            for trial in schedule():
                cue_canvas = draw_screen(cv2, np, screen_content("cue", trial), width, height)
                _show(cv2, window, cue_canvas, "fixation cue")
                flow = CueFlow(trial, time.monotonic())
                while time.monotonic() < flow.cue_onset + FIXATION_CUE_SECONDS:
                    _show(cv2, window, cue_canvas, "fixation cue")
                cue_end = time.monotonic()
                target_content = screen_content("target", trial)
                _show(
                    cv2,
                    window,
                    draw_screen(cv2, np, target_content, width, height),
                    "target onset",
                )
                target_onset = time.monotonic()
                target_state = flow.begin_target(target_onset)
                target_rows = _capture_phase(
                    cv2,
                    np,
                    window,
                    dimensions,
                    args,
                    trial,
                    "target",
                    target_state,
                    mapping,
                    recorded_source,
                    tap,
                    began,
                )
                target_samples.extend(target_rows)
                trials.append(
                    {
                        **trial.identity(),
                        "cue_onset_monotonic_seconds": flow.cue_onset - began,
                        "cue_end_monotonic_seconds": cue_end - began,
                        "target_onset_monotonic_seconds": target_onset - began,
                        "target_end_monotonic_seconds": time.monotonic() - began,
                        "target_summary": summarize_target(trial, target_state, target_rows),
                        "outcome": target_state.outcome,
                    }
                )
                _feedback(cv2, np, window, dimensions, target_state.outcome)
            report = {
                "participant": args.participant,
                "session": args.session,
                "protocol_name": PROTOCOL_NAME,
                "protocol_version": PROTOCOL_VERSION,
                "order_seed": ORDER_SEED,
                "ready_screen_used": True,
                "second_ready_screen_used": True,
                "camera_index": args.camera_index,
                "camera_resolution": recorded_source.resolution,
                "window_image_area": [width, height],
                "elapsed_seconds": time.monotonic() - began,
                "calibration_settle_seconds": SETTLE_SECONDS,
                "calibration_sample_seconds": SAMPLE_SECONDS,
                "calibration_min_usable_samples": MIN_USABLE_SAMPLES,
                "target_centers": [_target_record(target) for target in TARGETS],
                "target_half_width": TARGET_HALF_WIDTH,
                "target_half_height": TARGET_HALF_HEIGHT,
                "target_dwell_seconds": TARGET_DWELL_SECONDS,
                "target_timeout_seconds": TARGET_TIMEOUT_SECONDS,
                "fixation_cue_seconds": FIXATION_CUE_SECONDS,
                "cue_assignment": CUE_ASSIGNMENT,
                "feedback_seconds": FEEDBACK_SECONDS,
                "mapping_coefficients": {
                    "x_slope": mapping.x_slope,
                    "x_intercept": mapping.x_intercept,
                    "y_slope": mapping.y_slope,
                    "y_intercept": mapping.y_intercept,
                },
                "camera_reads_including_calibration": recorded_source.reads,
                "failed_camera_reads_including_calibration": recorded_source.failed_reads,
                "no_face_observations_including_calibration": recorded_extractor.no_face,
                "calibration_presentations": calibration_presentations,
                "trials": trials,
                "target_samples": target_samples,
            }
            analyze_session(report)
            return report
    finally:
        source.close()
        if window_created:
            cv2.destroyWindow(window)


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    marker_path = _invalid_path(args.output)
    if args.output.exists() or marker_path.exists():
        print("Refusing to overwrite existing output or invalid marker", file=sys.stderr)
        return 1
    try:
        report = collect_session(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as destination:
            json.dump(report, destination, indent=2)
            destination.write("\n")
        print(f"Completed 9 calibration presentations and 27 target trials: {args.output}")
        return 0
    except (KeyboardInterrupt, InterruptedError, RuntimeError, ValueError, OSError) as error:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker = {
            "participant": args.participant,
            "session": args.session,
            "protocol_name": PROTOCOL_NAME,
            "protocol_version": PROTOCOL_VERSION,
            "status": "invalid_incomplete_run",
            "reason": str(error) or type(error).__name__,
            "planned_calibration_presentations": 9,
            "planned_targeting_trials": 27,
            "partial_measurements_available": False,
        }
        with marker_path.open("x", encoding="utf-8") as destination:
            json.dump(marker, destination, indent=2)
            destination.write("\n")
        print(f"Run invalid; reason saved: {marker_path}: {marker['reason']}", file=sys.stderr)
        return 130 if isinstance(error, (KeyboardInterrupt, InterruptedError)) else 1


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
