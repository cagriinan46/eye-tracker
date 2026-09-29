"""Collect fixed-center checkpoints around an unchanged held-out gaze protocol."""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.vertical_collapse_diagnostics.capture import measure_once
from experiments.vertical_drift_diagnostics.analysis import summarize_checkpoints
from experiments.vertical_drift_diagnostics.protocol import build_checkpoint_schedule
from eye_tracker.gaze.calibration import CalibrationSample
from eye_tracker.gaze.estimator import GazeEstimate, GazeUnavailable
from eye_tracker.vision.camera import OpenCVCameraSource
from eye_tracker.vision.eye_features import EyeFeatures
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor
from validation.real_calibration import (
    CALIBRATION_TARGETS,
    MIN_USABLE_SAMPLES,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    Presentation,
    RecordingExtractor,
    RecordingSource,
    Target,
    TrialEstimate,
    _draw_target,
    collect_presentation,
    fit_session_calibration,
    summarize_held_out,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Pseudonymous participant ID")
    parser.add_argument("--session", required=True, choices=("A", "B"))
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if not args.participant.strip():
        parser.error("participant ID must not be blank")
    if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
        parser.error("derived numerical output must be inside Git-ignored .venv")
    return args


def _calibration_center(samples: tuple[CalibrationSample, ...]) -> float:
    centers = [
        sample.vertical_feature
        for target, sample in zip(CALIBRATION_TARGETS, samples, strict=True)
        if (target.x, target.y) == (0.5, 0.5)
    ]
    if len(centers) != 1:
        raise ValueError("one calibration-center sample is required")
    return centers[0]


def collect_session(args: argparse.Namespace) -> dict:
    """Run the human-only UI and return derived data; caller persists only on success."""
    # Import UI dependencies only for an actual human run; CI stays hardware-free.
    import cv2
    import numpy as np

    window = f"Vertical drift diagnostics {args.participant}/{args.session} - q / Esc"
    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window_created = False
    try:
        with MediaPipeFaceLandmarkExtractor(args.model) as detector:
            recorded_extractor = RecordingExtractor(detector)
            source.open()
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            window_created = True
            cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(window, np.full((700, 1200, 3), 24, dtype=np.uint8))
            cv2.waitKey(1)
            _, _, width, height = cv2.getWindowImageRect(window)
            if width <= 0 or height <= 0:
                raise RuntimeError("Could not determine target-window image-area dimensions")

            schedule = build_checkpoint_schedule(seed=args.seed)
            calibration_observations: list[tuple[Target, list[tuple[float, float]]]] = []
            held_out: list[TrialEstimate] = []
            rows: list[dict] = []
            counts_by_presentation: list[dict] = []
            mapping = None
            samples: tuple[CalibrationSample, ...] = ()
            started = time.monotonic()
            for position, presentation in enumerate(schedule, start=1):
                sampling_now = False

                def show(current: Presentation, sampling: bool, remaining: float) -> bool:
                    nonlocal sampling_now
                    sampling_now = sampling
                    cv2.imshow(
                        window,
                        _draw_target(
                            cv2,
                            np,
                            current,
                            position,
                            len(schedule),
                            sampling,
                            remaining,
                            width,
                            height,
                        ),
                    )
                    return cv2.waitKey(1) & 0xFF in (ord("q"), 27)

                def measure() -> EyeFeatures | GazeEstimate | GazeUnavailable:
                    result, details = measure_once(recorded_source, recorded_extractor, mapping)
                    if sampling_now:
                        rows.append(
                            {
                                "participant": args.participant,
                                "session": args.session,
                                "phase": presentation.phase,
                                "target_id": presentation.target.name,
                                "target_x": presentation.target.x,
                                "target_y": presentation.target.y,
                                "trial_number": presentation.trial,
                                "checkpoint": (
                                    presentation.trial
                                    if presentation.phase == "checkpoint"
                                    else None
                                ),
                                "sample_sequence": len(rows) + 1,
                                "monotonic_seconds": time.monotonic() - started,
                                **details,
                            }
                        )
                    return result

                collected, counts = collect_presentation(presentation, measure, show)
                counts_by_presentation.append(
                    {
                        "position": position,
                        "phase": presentation.phase,
                        "target_id": presentation.target.name,
                        "trial_number": presentation.trial,
                        "sampling_attempts": counts["sampling_attempts"],
                        "usable_samples": len(collected),
                        "unavailable": counts["unavailable"],
                    }
                )
                if presentation.phase == "calibration":
                    calibration_observations.append(
                        (
                            presentation.target,
                            [(item.horizontal, item.vertical) for item in collected],
                        )
                    )
                    if len(calibration_observations) == len(CALIBRATION_TARGETS):
                        mapping, samples = fit_session_calibration(calibration_observations)
                elif presentation.phase == "validation":
                    held_out.append(
                        TrialEstimate(presentation.target, presentation.trial, collected)
                    )

            if mapping is None:
                raise RuntimeError("session calibration was not fitted")
            center_feature = _calibration_center(samples)
            checkpoint_rows = [row for row in rows if row["phase"] == "checkpoint"]
            return {
                "participant": args.participant,
                "session": args.session,
                "condition": "normal posture, natural eye opening/blinking; fresh calibration",
                "camera_index": args.camera_index,
                "camera_resolution": recorded_source.resolution,
                "window_image_area": [width, height],
                "elapsed_seconds": time.monotonic() - started,
                "seed": args.seed,
                "settle_seconds": SETTLE_SECONDS,
                "sample_seconds": SAMPLE_SECONDS,
                "minimum_usable_samples_per_presentation": MIN_USABLE_SAMPLES,
                "camera_reads_including_settling": recorded_source.reads,
                "failed_camera_reads_including_settling": recorded_source.failed_reads,
                "no_face_observations_including_settling": recorded_extractor.no_face,
                "collection_counts": counts_by_presentation,
                "rows": rows,
                "calibration_center_vertical": center_feature,
                "mapping_coefficients": {
                    "x_slope": mapping.x_slope,
                    "x_intercept": mapping.x_intercept,
                    "y_slope": mapping.y_slope,
                    "y_intercept": mapping.y_intercept,
                },
                "checkpoint_summary": summarize_checkpoints(checkpoint_rows, center_feature),
                "held_out_validation": summarize_held_out(held_out, width, height),
                "protocol_difference": (
                    "Experiment 006's experimental blink gate is omitted; production has no "
                    "validated blink filter. The five repeated CENTER checkpoints extend "
                    "the unchanged nine-calibration-target/16-held-out-trial protocol. "
                    "Blink blendshape scores are unavailable in the current observation contract."
                ),
            }
    except cv2.error as error:
        raise RuntimeError(f"OpenCV window or camera operation failed: {error}") from error
    finally:
        source.close()
        if window_created:
            cv2.destroyWindow(window)


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output.exists():
        print(f"Refusing to overwrite existing result: {args.output}", file=sys.stderr)
        return 1
    try:
        report = collect_session(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as destination:
            json.dump(report, destination, indent=2)
            destination.write("\n")
        print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
        print(f"Local derived-numerical dataset: {args.output}")
        return 0
    except KeyboardInterrupt:
        print("Diagnostic run interrupted; no complete result saved.", file=sys.stderr)
        return 130
    except InterruptedError:
        print("Diagnostic run cancelled; no complete result saved.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError, OSError) as error:
        print(f"Diagnostic run failed: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
