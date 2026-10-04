"""Collect one fixed-target, face-referenced numerical eye-geometry session."""

import argparse
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from statistics import median

from experiments.eye_geometry_decomposition_study.run import invalid_path, measure_geometry_once
from experiments.eye_opening_controlled_study.protocol import ready_key_action
from experiments.eye_opening_controlled_study.run import draw_screen
from experiments.face_reference_corner_stability_study.face_reference import (
    FACE_ANCHOR_INDICES,
    FACE_REFERENCE_METHOD,
    anchor_record,
    calibration_template,
    enrich_usable_rows,
)
from experiments.face_reference_corner_stability_study.protocol import (
    CUE_SECONDS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    StudyPresentation,
    schedule,
    screen_content,
)
from eye_tracker.vision.camera import OpenCVCameraSource
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor
from validation.real_calibration import (
    CALIBRATION_TARGETS,
    MIN_USABLE_SAMPLES,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    RecordingExtractor,
    RecordingSource,
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


def wait_for_ready(cv2, np, window: str, width: int, height: int) -> None:
    canvas = draw_screen(cv2, np, screen_content(None, "ready"), width, height)
    while True:
        cv2.imshow(window, canvas)
        action = ready_key_action(cv2.waitKey(30))
        if action == "start":
            return
        if action == "abort":
            raise InterruptedError("run cancelled at READY screen")


def show_cue(cv2, np, window: str, item: StudyPresentation, width: int, height: int) -> None:
    canvas = draw_screen(cv2, np, screen_content(item, "cue"), width, height)
    began = time.monotonic()
    while time.monotonic() - began < CUE_SECONDS:
        cv2.imshow(window, canvas)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            raise InterruptedError("run cancelled during condition cue")


def collect_study_presentation(
    item: StudyPresentation,
    cue: Callable[[StudyPresentation], None],
    collect: Callable,
):
    if item.phase == "diagnostic":
        cue(item)
    return collect(item.capture_presentation())


def measure_face_once(source, extractor, mapping):
    """Reuse the old production-path eye tap and add ten non-eye anchors."""

    class ExtractorTap:
        observation = None

        def extract(self, frame):
            self.observation = extractor.extract(frame)
            return self.observation

    tapped = ExtractorTap()
    result, details = measure_geometry_once(source, tapped, mapping)
    details["face_anchors"] = (
        anchor_record(tapped.observation) if details["status"] == "usable" else None
    )
    details["face_alignment"] = None
    details["image_eye_geometry"] = None
    details["face_normalized_geometry"] = None
    return result, details


def collect_session(args: argparse.Namespace) -> dict:
    import cv2
    import numpy as np

    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window = f"Face reference {args.participant}/{args.session} - q / Esc"
    window_created = False
    rows: list[dict] = []
    presentations: list[dict] = []
    calibration_observations = []
    mapping = None
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
            wait_for_ready(cv2, np, window, width, height)
            started = time.monotonic()
            for item in schedule():
                sampling_now = False
                first_row = len(rows)

                def show(current, sampling: bool, remaining: float) -> bool:
                    nonlocal sampling_now
                    sampling_now = sampling
                    phase = "sampling" if sampling else "settling"
                    cv2.imshow(
                        window, draw_screen(cv2, np, screen_content(item, phase), width, height)
                    )
                    return cv2.waitKey(1) & 0xFF in (ord("q"), 27)

                def measure():
                    result, details = measure_face_once(
                        recorded_source, recorded_extractor, mapping
                    )
                    if sampling_now:
                        rows.append(
                            {
                                "participant": args.participant,
                                "session": args.session,
                                **item.identity(),
                                "presentation_order": item.order,
                                "sample_sequence": len(rows) + 1,
                                "monotonic_seconds": time.monotonic() - started,
                                **details,
                            }
                        )
                    return result

                collected, counts = collect_study_presentation(
                    item,
                    lambda current: show_cue(cv2, np, window, current, width, height),
                    lambda current: collect_presentation(current, measure, show),
                )
                recorded = rows[first_row:]
                usable = [row for row in recorded if row["status"] == "usable"]
                if len(usable) != len(collected):
                    raise RuntimeError("usable sample count disagrees with capture")
                presentations.append(
                    {
                        "order": item.order,
                        **item.identity(),
                        "usable_count": len(usable),
                        "unavailable_count": len(recorded) - len(usable),
                        "sampling_attempts": counts["sampling_attempts"],
                        "vertical_feature": median(row["vertical"] for row in usable),
                        "binocular_eye_opening": median(
                            row["binocular_eye_opening"] for row in usable
                        ),
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
            resolution = recorded_source.resolution
            if resolution is None:
                raise RuntimeError("camera resolution unavailable")
            frame_width, frame_height = resolution
            template = calibration_template(rows, frame_width, frame_height)
            enrich_usable_rows(rows, template, frame_width, frame_height)
            return {
                "participant": args.participant,
                "session": args.session,
                "protocol_name": PROTOCOL_NAME,
                "protocol_version": PROTOCOL_VERSION,
                "order_seed": ORDER_SEED,
                "cue_seconds": CUE_SECONDS,
                "ready_screen_used": True,
                "camera_index": args.camera_index,
                "camera_resolution": resolution,
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
                "face_landmark_indices": list(FACE_ANCHOR_INDICES),
                "face_reference_method": FACE_REFERENCE_METHOD,
                "face_reference_template_px": template,
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
