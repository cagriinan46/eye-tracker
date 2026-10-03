"""Collect one geometry-rich, comfortable eye-opening session as numerical JSON."""

import argparse
import json
import sys
import time
from collections.abc import Callable
from math import atan2, hypot
from pathlib import Path
from statistics import median

from experiments.eye_geometry_decomposition_study.geometry import eye_record
from experiments.eye_geometry_decomposition_study.protocol import (
    CUE_SECONDS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    StudyPresentation,
    schedule,
    screen_content,
)
from experiments.eye_opening_controlled_study.protocol import ready_key_action
from experiments.eye_opening_controlled_study.run import draw_screen
from experiments.vertical_collapse_diagnostics.capture import measure_once
from eye_tracker.vision.camera import OpenCVCameraSource
from eye_tracker.vision.eye_topology import eye_geometry_from_observation
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


def invalid_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.invalid.json")


def wait_for_ready(cv2, np, window: str, width: int, height: int) -> None:
    """Start collection only after the participant sees the full-screen window."""
    canvas = draw_screen(cv2, np, screen_content(None, "ready"), width, height)
    while True:
        cv2.imshow(window, canvas)
        action = ready_key_action(cv2.waitKey(30))
        if action == "start":
            return
        if action == "abort":
            raise InterruptedError("run cancelled at ready screen")


def show_cue(cv2, np, window: str, item, width: int, height: int) -> None:
    """Present the condition before the target; capture no frames during this phase."""
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
    """Finish the diagnostic cue before any target settling or measurement."""
    if item.phase == "diagnostic":
        cue(item)
    return collect(item.capture_presentation())


def measure_geometry_once(source, extractor, mapping):
    """Reuse the existing feature path, then retain its minimal source geometry."""

    class SourceTap:
        frame = None

        def read(self):
            self.frame = source.read()
            return self.frame

    class ExtractorTap:
        observation = None

        def extract(self, frame):
            self.observation = extractor.extract(frame)
            return self.observation

    source_tap, extractor_tap = SourceTap(), ExtractorTap()
    result, details = measure_once(source_tap, extractor_tap, mapping)
    details.update(
        frame_width=None,
        frame_height=None,
        geometry=None,
        head_center_x=None,
        inter_eye_scale_px=None,
        eye_line_angle_rad=None,
    )
    if details["status"] != "usable":
        return result, details
    frame = source_tap.frame
    eyes = eye_geometry_from_observation(extractor_tap.observation)
    if frame is None or eyes is None:
        raise RuntimeError("usable feature has no source geometry")
    left, right = eyes
    left_mid = ((left.corner_a.x + left.corner_b.x) / 2, (left.corner_a.y + left.corner_b.y) / 2)
    right_mid = (
        (right.corner_a.x + right.corner_b.x) / 2,
        (right.corner_a.y + right.corner_b.y) / 2,
    )
    delta_x = (right_mid[0] - left_mid[0]) * frame.width
    delta_y = (right_mid[1] - left_mid[1]) * frame.height
    details.update(
        frame_width=frame.width,
        frame_height=frame.height,
        geometry={"left": eye_record(left), "right": eye_record(right)},
        head_center_x=(left_mid[0] + right_mid[0]) / 2,
        inter_eye_scale_px=hypot(delta_x, delta_y),
        eye_line_angle_rad=atan2(delta_y, delta_x),
    )
    return result, details


def collect_session(args: argparse.Namespace) -> dict:
    """Reuse production geometry and the established capture timing/calibration."""
    import cv2
    import numpy as np

    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window = f"Eye geometry {args.participant}/{args.session} - q / Esc"
    window_created = False
    plan = schedule()
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
            for item in plan:
                sampling_now = False
                first_row = len(rows)

                def show(current, sampling: bool, remaining: float) -> bool:
                    nonlocal sampling_now
                    sampling_now = sampling
                    phase = "sampling" if sampling else "settling"
                    canvas = draw_screen(cv2, np, screen_content(item, phase), width, height)
                    cv2.imshow(window, canvas)
                    return cv2.waitKey(1) & 0xFF in (ord("q"), 27)

                def measure():
                    result, details = measure_geometry_once(
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
                "protocol_name": PROTOCOL_NAME,
                "protocol_version": PROTOCOL_VERSION,
                "order_seed": ORDER_SEED,
                "cue_seconds": CUE_SECONDS,
                "ready_screen_used": True,
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
