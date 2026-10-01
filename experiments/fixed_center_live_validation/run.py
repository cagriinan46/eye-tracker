"""Capture one fresh calibration, one CENTER anchor, and unchanged held-out trials."""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.fixed_center_live_validation.analysis import compare_predictions, derive_offset
from experiments.fixed_center_live_validation.protocol import CENTER, build_schedule
from eye_tracker.app.gaze_pipeline import process_gaze_frame
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
    collect_features_once,
    collect_presentation,
    fit_session_calibration,
    summarize_calibration_fit,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Pseudonymous participant ID")
    parser.add_argument("--session", required=True, help="Unique local session label")
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if not args.participant.strip() or not args.session.strip():
        parser.error("participant and session labels must not be blank")
    if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
        parser.error("derived numerical output must be inside Git-ignored .venv")
    return args


def collect_session(args: argparse.Namespace) -> dict:
    """Run the human-only UI; persist a report only after full completion."""
    # UI imports are deferred so the deterministic test suite needs no camera or window.
    import cv2
    import numpy as np

    window = f"Fixed CENTER live validation {args.participant}/{args.session} - q / Esc"
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

            schedule = build_schedule(seed=args.seed)
            calibration_observations: list[tuple[Target, list[tuple[float, float]]]] = []
            calibration_samples: tuple[CalibrationSample, ...] = ()
            anchor_observations: tuple[tuple[float, float], ...] | None = None
            held_out: list[TrialEstimate] = []
            collection_counts: list[dict] = []
            mapping = None
            started = time.monotonic()
            for position, presentation in enumerate(schedule, start=1):

                def show(current: Presentation, sampling: bool, remaining: float) -> bool:
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
                    if presentation.phase in ("calibration", "anchor"):
                        return collect_features_once(recorded_source, recorded_extractor)
                    if mapping is None or anchor_observations is None:
                        raise RuntimeError(
                            "held-out collection requires calibration and CENTER anchor"
                        )
                    return process_gaze_frame(recorded_source, recorded_extractor, mapping)

                collected, counts = collect_presentation(presentation, measure, show)
                collection_counts.append(
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
                        mapping, calibration_samples = fit_session_calibration(
                            calibration_observations
                        )
                elif presentation.phase == "anchor":
                    if mapping is None or anchor_observations is not None:
                        raise RuntimeError("CENTER anchor must occur once, after calibration")
                    anchor_observations = tuple(
                        (item.horizontal, item.vertical) for item in collected
                    )
                    # Establish the fixed correction before any held-out target is shown.
                    derive_offset(mapping, anchor_observations)
                else:
                    held_out.append(
                        TrialEstimate(presentation.target, presentation.trial, collected)
                    )

            if mapping is None or anchor_observations is None:
                raise RuntimeError("calibration or CENTER anchor was not completed")
            calibration_center = next(
                sample
                for sample in calibration_samples
                if (sample.target_x, sample.target_y) == (CENTER.x, CENTER.y)
            )
            comparison = compare_predictions(
                mapping,
                calibration_center,
                anchor_observations,
                held_out,
                width,
                height,
            )
            return {
                "participant": args.participant,
                "session": args.session,
                "intended_condition": "normal posture, natural eye opening/blinking; fresh calibration",
                "camera_index": args.camera_index,
                "camera_resolution": recorded_source.resolution,
                "window_image_area": [width, height],
                "elapsed_seconds": time.monotonic() - started,
                "seed": args.seed,
                "settle_seconds": SETTLE_SECONDS,
                "sample_seconds": SAMPLE_SECONDS,
                "minimum_usable_samples_per_presentation": MIN_USABLE_SAMPLES,
                "calibration_target_count": len(calibration_observations),
                "center_anchor_count": 1,
                "held_out_trial_count": len(held_out),
                "camera_reads_including_settling": recorded_source.reads,
                "successful_camera_reads_including_settling": (
                    recorded_source.reads - recorded_source.failed_reads
                ),
                "failed_camera_reads_including_settling": recorded_source.failed_reads,
                "no_face_observations_including_settling": recorded_extractor.no_face,
                "collection_counts": collection_counts,
                "calibration_fit": summarize_calibration_fit(
                    mapping, calibration_observations, calibration_samples, width, height
                ),
                **comparison,
                "protocol_difference": (
                    "One post-calibration CENTER anchor precedes the unchanged 16 held-out trials. "
                    "The production path has no experimental blink gate or smoothing. "
                    "The vertical offset is fixed and applied only in experimental evaluation."
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
        print(json.dumps(report, indent=2))
        print(f"Local derived-numerical report: {args.output}")
        return 0
    except KeyboardInterrupt:
        print("Validation interrupted; no completed result saved.", file=sys.stderr)
        return 130
    except InterruptedError:
        print("Validation cancelled; no completed result saved.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError, OSError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
