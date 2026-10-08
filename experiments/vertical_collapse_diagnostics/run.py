"""Collect one controlled, session-local vertical-gaze diagnostic run."""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.vertical_collapse_diagnostics.capture import measure_once
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
    build_presentations,
    collect_presentation,
    fit_session_calibration,
    open_target_window,
    parse_screen_size,
    summarize_calibration_fit,
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
    parser.add_argument(
        "--screen-size",
        type=parse_screen_size,
        help="Logical display size WIDTHxHEIGHT; draws targets over the full screen",
    )
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if not args.participant.strip():
        parser.error("participant ID must not be blank")
    ignored_root = Path(".venv").resolve()
    if not args.output.resolve().is_relative_to(ignored_root):
        parser.error("derived numerical output must be inside the Git-ignored .venv directory")
    return args


def _calibration_samples(
    samples: tuple[CalibrationSample, ...], targets: list[Target]
) -> list[dict]:
    return [
        {
            "target_id": target.name,
            "target_x": target.x,
            "target_y": target.y,
            "horizontal_feature": sample.horizontal_feature,
            "vertical_feature": sample.vertical_feature,
        }
        for target, sample in zip(targets, samples, strict=True)
    ]


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output.exists():
        print(f"Refusing to overwrite existing result: {args.output}", file=sys.stderr)
        return 1

    # Human-only imports keep CI hardware-free.
    import cv2
    import numpy as np

    window = f"Vertical gaze diagnostics {args.participant}/{args.session} - q / Esc"
    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window_created = False
    try:
        with MediaPipeFaceLandmarkExtractor(args.model) as detector:
            recorded_extractor = RecordingExtractor(detector)
            source.open()
            window_created = True
            width, height = open_target_window(cv2, np, window, args.screen_size)

            order = build_presentations(seed=args.seed)
            calibration_observations: list[tuple[Target, list[tuple[float, float]]]] = []
            held_out: list[TrialEstimate] = []
            rows: list[dict] = []
            collection_counts: dict[str, dict] = {}
            mapping = None
            samples: tuple[CalibrationSample, ...] = ()
            started = time.monotonic()
            for position, presentation in enumerate(order, start=1):
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
                            len(order),
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
                                "sample_sequence": len(rows) + 1,
                                "monotonic_seconds": time.monotonic() - started,
                                **details,
                            }
                        )
                    return result

                collected, counts = collect_presentation(presentation, measure, show)
                collection_counts[f"{presentation.target.name}/{presentation.trial}"] = {
                    "phase": presentation.phase,
                    "sampling_attempts": counts["sampling_attempts"],
                    "usable_samples": len(collected),
                    "unavailable": counts["unavailable"],
                }
                if presentation.phase == "calibration":
                    calibration_observations.append(
                        (
                            presentation.target,
                            [(item.horizontal, item.vertical) for item in collected],
                        )
                    )
                    if len(calibration_observations) == len(CALIBRATION_TARGETS):
                        mapping, samples = fit_session_calibration(calibration_observations)
                else:
                    held_out.append(
                        TrialEstimate(presentation.target, presentation.trial, collected)
                    )

            if mapping is None:
                raise RuntimeError("session calibration was not fitted")
            report = {
                "participant": args.participant,
                "session": args.session,
                "condition": "normal comfortable posture; natural eye opening and blinking",
                "camera_index": args.camera_index,
                "camera_resolution": recorded_source.resolution,
                "window_image_area": [width, height],
                "requested_screen_size": list(args.screen_size) if args.screen_size else None,
                "elapsed_seconds": time.monotonic() - started,
                "seed": args.seed,
                "settle_seconds": SETTLE_SECONDS,
                "sample_seconds": SAMPLE_SECONDS,
                "minimum_usable_samples_per_presentation": MIN_USABLE_SAMPLES,
                "camera_reads_including_settling": recorded_source.reads,
                "failed_camera_reads_including_settling": recorded_source.failed_reads,
                "no_face_observations_including_settling": recorded_extractor.no_face,
                "collection_counts": collection_counts,
                "rows": rows,
                "calibration_samples": _calibration_samples(
                    samples, [target for target, _ in calibration_observations]
                ),
                "mapping_coefficients": {
                    "x_slope": mapping.x_slope,
                    "x_intercept": mapping.x_intercept,
                    "y_slope": mapping.y_slope,
                    "y_intercept": mapping.y_intercept,
                },
                "calibration_fit": summarize_calibration_fit(
                    mapping, calibration_observations, samples, width, height
                ),
                "held_out_validation": summarize_held_out(held_out, width, height),
                "protocol_difference": (
                    "Experiment 006's experimental blink gate is omitted; the production path "
                    "has no validated blink filter. Blink blendshape scores are unavailable in "
                    "the current vendor-neutral LandmarkObservation contract."
                ),
            }
            from experiments.vertical_collapse_diagnostics.analysis import summarize_session

            summary = summarize_session(report)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as destination:
                json.dump(report, destination, indent=2)
                destination.write("\n")
            print(json.dumps(summary, indent=2))
            print(f"Local derived-numerical dataset: {args.output}")
            return 0
    except KeyboardInterrupt:
        print("Diagnostic run interrupted; no complete result saved.", file=sys.stderr)
        return 130
    except InterruptedError:
        print("Diagnostic run cancelled; no complete result saved.", file=sys.stderr)
        return 130
    except (cv2.error, RuntimeError, ValueError, OSError) as error:
        print(f"Diagnostic run failed: {error}", file=sys.stderr)
        return 1
    finally:
        source.close()
        if window_created:
            cv2.destroyWindow(window)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
