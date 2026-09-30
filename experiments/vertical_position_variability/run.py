"""Collect balanced, derived-numerical position/repeat diagnostics on a Mac."""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.vertical_collapse_diagnostics.capture import measure_once
from experiments.vertical_position_variability.protocol import build_schedule
from eye_tracker.vision.camera import OpenCVCameraSource
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
    _draw_target,
    collect_presentation,
    fit_session_calibration,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Pseudonymous participant ID")
    parser.add_argument("--session", required=True, help="Session identifier")
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0 or not args.participant.strip() or not args.session.strip():
        parser.error("camera index must be nonnegative and participant/session must be nonblank")
    if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
        parser.error("derived numerical output must be inside Git-ignored .venv")
    return args


def collect_session(args: argparse.Namespace) -> dict:
    """Run only the human target UI; return no frame or facial imagery."""
    import cv2
    import numpy as np

    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window = f"Vertical position diagnostics {args.participant}/{args.session} - q / Esc"
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
                raise RuntimeError("Could not determine target-window image area")

            rows: list[dict] = []
            calibration_observations: list[tuple[Target, list[tuple[float, float]]]] = []
            mapping = None
            schedule = build_schedule()
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

                def measure():
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
                                "checkpoint": None,
                                "sample_sequence": len(rows) + 1,
                                "monotonic_seconds": time.monotonic() - started,
                                **details,
                            }
                        )
                    return result

                collected, _ = collect_presentation(presentation, measure, show)
                if presentation.phase == "calibration":
                    calibration_observations.append(
                        (
                            presentation.target,
                            [(item.horizontal, item.vertical) for item in collected],
                        )
                    )
                    if len(calibration_observations) == len(CALIBRATION_TARGETS):
                        mapping, _ = fit_session_calibration(calibration_observations)
            if mapping is None:
                raise RuntimeError("session calibration was not fitted")
            return {
                "participant": args.participant,
                "session": args.session,
                "condition": "normal comfortable posture; natural eye opening and blinking",
                "camera_index": args.camera_index,
                "camera_resolution": recorded_source.resolution,
                "window_image_area": [width, height],
                "elapsed_seconds": time.monotonic() - started,
                "settle_seconds": SETTLE_SECONDS,
                "sample_seconds": SAMPLE_SECONDS,
                "minimum_usable_samples_per_presentation": MIN_USABLE_SAMPLES,
                "camera_reads_including_settling": recorded_source.reads,
                "failed_camera_reads_including_settling": recorded_source.failed_reads,
                "no_face_observations_including_settling": recorded_extractor.no_face,
                "rows": rows,
                "mapping_coefficients": {
                    "x_slope": mapping.x_slope,
                    "x_intercept": mapping.x_intercept,
                    "y_slope": mapping.y_slope,
                    "y_intercept": mapping.y_intercept,
                },
                "protocol_difference": (
                    "Experiment 006's experimental blink gate is absent; this run adds two "
                    "reversed-order diagnostic passes at the nine grid coordinates."
                ),
            }
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
        print(f"Completed {len(build_schedule())} presentations; numerical data: {args.output}")
        return 0
    except (KeyboardInterrupt, InterruptedError):
        print("Diagnostic cancelled; no complete result saved.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError, OSError) as error:
        print(f"Diagnostic failed: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
