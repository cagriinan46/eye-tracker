"""Collect one fresh, comfortable eye-opening session as derived numerical JSON."""

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import median

from experiments.eye_opening_controlled_study.protocol import INSTRUCTIONS, schedule
from experiments.vertical_collapse_diagnostics.capture import measure_once
from eye_tracker.vision.camera import OpenCVCameraSource
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor
from validation.real_calibration import (
    CALIBRATION_TARGETS,
    MIN_USABLE_SAMPLES,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    RecordingExtractor,
    RecordingSource,
    _draw_target,
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


def invalid_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.invalid.json")


def collect_session(args: argparse.Namespace) -> dict:
    """Reuse production geometry and the established capture timing/calibration."""
    import cv2
    import numpy as np

    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window = f"Eye opening {args.participant}/{args.session} - q / Esc"
    window_created = False
    plan = schedule()
    rows: list[dict] = []
    presentations: list[dict] = []
    calibration_observations = []
    mapping = None
    started = time.monotonic()
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
            for item in plan:
                sampling_now = False
                presentation = item.capture_presentation()
                first_row = len(rows)

                def show(current, sampling: bool, remaining: float) -> bool:
                    nonlocal sampling_now
                    sampling_now = sampling
                    canvas = _draw_target(
                        cv2, np, current, item.order, len(plan), sampling, remaining, width, height
                    )
                    cv2.putText(
                        canvas,
                        INSTRUCTIONS[item.condition],
                        (30, 145),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 220, 255),
                        2,
                    )
                    cv2.putText(
                        canvas,
                        "Keep looking at dot; change only eye opening comfortably.",
                        (30, 185),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.57,
                        (225, 225, 225),
                        2,
                    )
                    cv2.putText(
                        canvas,
                        "No strain or intentional head movement; natural blinking OK.",
                        (30, 220),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.57,
                        (225, 225, 225),
                        2,
                    )
                    cv2.imshow(window, canvas)
                    return cv2.waitKey(1) & 0xFF in (ord("q"), 27)

                def measure():
                    result, details = measure_once(recorded_source, recorded_extractor, mapping)
                    if sampling_now:
                        rows.append(
                            {
                                "participant": args.participant,
                                "session": args.session,
                                "phase": item.phase,
                                "target_id": item.target.name,
                                "target_x": item.target.x,
                                "target_y": item.target.y,
                                "condition": item.condition,
                                "block": item.block,
                                "presentation_order": item.order,
                                "sample_sequence": len(rows) + 1,
                                "monotonic_seconds": time.monotonic() - started,
                                **details,
                            }
                        )
                    return result

                collected, counts = collect_presentation(presentation, measure, show)
                recorded = rows[first_row:]
                usable = [row for row in recorded if row["status"] == "usable"]
                if len(usable) != len(collected):
                    raise RuntimeError("usable sample count disagrees with capture")
                presentations.append(
                    {
                        "order": item.order,
                        "phase": item.phase,
                        "target_id": item.target.name,
                        "target_x": item.target.x,
                        "target_y": item.target.y,
                        "condition": item.condition,
                        "block": item.block,
                        "usable_count": len(usable),
                        "unavailable_count": len(recorded) - len(usable),
                        "sampling_attempts": counts["sampling_attempts"],
                        "vertical_feature": median(row["vertical"] for row in usable),
                    }
                )
                if item.phase == "calibration":
                    calibration_observations.append(
                        (
                            item.target,
                            [(sample.horizontal, sample.vertical) for sample in collected],
                        )
                    )
                    if len(calibration_observations) == len(CALIBRATION_TARGETS):
                        mapping, _ = fit_session_calibration(calibration_observations)
            if mapping is None:
                raise RuntimeError("session calibration was not fitted")
            return {
                "participant": args.participant,
                "session": args.session,
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
                "mapping_coefficients": {
                    "x_slope": mapping.x_slope,
                    "x_intercept": mapping.x_intercept,
                    "y_slope": mapping.y_slope,
                    "y_intercept": mapping.y_intercept,
                },
                "presentations": presentations,
                "rows": rows,
            }
    finally:
        source.close()
        if window_created:
            cv2.destroyWindow(window)


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    marker_path = invalid_path(args.output)
    if args.output.exists() or marker_path.exists():
        print("Refusing to overwrite existing output or invalid marker", file=sys.stderr)
        return 1
    try:
        report = collect_session(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as destination:
            json.dump(report, destination, indent=2)
            destination.write("\n")
        print(f"Completed {len(schedule())} presentations; derived data: {args.output}")
        return 0
    except (KeyboardInterrupt, InterruptedError, RuntimeError, ValueError, OSError) as error:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker = {
            "participant": args.participant,
            "session": args.session,
            "camera_index": args.camera_index,
            "status": "invalid_incomplete_run",
            "reason": str(error) or type(error).__name__,
            "planned_presentations": len(schedule()),
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
