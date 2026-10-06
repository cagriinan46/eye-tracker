"""Full fixed-window collection with same-result numerical geometry sidecars."""

import json
import sys
import time
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version

from experiments.fixed_window_gaze_diagnostic.analysis import summarize_trial
from experiments.fixed_window_gaze_diagnostic.run import (
    FeatureTap,
    MeasurementWorker,
    collect_window,
    draw_screen,
    poll_key,
    sample_row,
    wait_fixed,
    wait_ready,
)
from experiments.fixed_window_gaze_diagnostic.run import (
    parse_args as base_parse_args,
)
from eye_tracker.app.gaze_pipeline import process_gaze_frame
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import (
    RecordingExtractor,
    RecordingSource,
    collect_features_once,
    fit_session_calibration,
)

from .analysis import inspect_capture
from .geometry import GeometryExtractor
from .protocol import (
    CALIBRATION_TARGETS,
    CUE_SECONDS,
    SAMPLE_SECONDS,
    SESSION_ROLES,
    SETTLE_SECONDS,
    TARGET_SECONDS,
    TRANSITION_SECONDS,
    Trial,
    configuration,
    schedule,
    screen_content,
)


def parse_args(argv=None):
    args = base_parse_args(argv)
    if args.session not in SESSION_ROLES:
        raise SystemExit("--session must be geometry-1 or geometry-2")
    return args


class GeometryTap(FeatureTap):
    """R0 feature tap and geometry from the exact same production frame/result."""

    def __init__(self, extractor, detector):
        super().__init__(extractor)
        self.detector = detector
        self.geometry = None
        self.geometry_error = None

    def extract(self, frame):
        self.geometry = None
        self.geometry_error = None
        observation = super().extract(frame)
        self.geometry = self.detector.last_geometry
        self.geometry_error = self.detector.geometry_error
        return observation


def geometry_sample_row(result, source, tap):
    row = sample_row(result, source, tap)
    frame = source.last_frame
    geometry = tap.geometry if frame is not None else None
    if geometry is not None and geometry["frame_timestamp_ns"] != frame.timestamp_ns:
        raise ValueError("geometry sidecar belongs to a different camera frame")
    return {
        **row,
        "camera_resolution": [frame.width, frame.height] if frame else None,
        "raw_geometry": geometry,
        "geometry_error": tap.geometry_error if frame else None,
    }


class GeometryWorker(MeasurementWorker):
    """Reuse queue/lifecycle; attach a numerical snapshot before the next frame."""

    def _run(self):
        try:
            while not self.stopping.is_set():
                started = time.monotonic()
                mapping = self.mapping
                result = (
                    collect_features_once(self.source, self.tap)
                    if mapping is None
                    else process_gaze_frame(self.source, self.tap, mapping)
                )
                self.queue.put(
                    {
                        **geometry_sample_row(result, self.source, self.tap),
                        "measurement_started_monotonic_seconds": started,
                        "monotonic_timestamp_seconds": time.monotonic(),
                    }
                )
                self.stopping.wait(0.001)
        except Exception as error:
            self.queue.put(error)


def collect_session(args, report):
    # Optional vision dependencies stay lazy so core-only CI can collect these tests.
    import cv2
    import numpy as np

    window = f"Raw-geometry measurement {args.participant}/{args.session}"
    source = OpenCVCameraSource(args.camera_index)
    recorded = RecordingSource(source)
    detector_counts = None
    window_created = False
    try:
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        window_created = True
        cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow(window, np.full((700, 1200, 3), 24, dtype=np.uint8))
        cv2.waitKey(1)
        _, _, width, height = cv2.getWindowImageRect(window)
        if width <= 0 or height <= 0:
            raise RuntimeError("could not determine target-window image area")
        report["window_image_area"] = [width, height]

        def show(phase, trial=None):
            cv2.imshow(window, draw_screen(cv2, np, screen_content(phase, trial), width, height))
            poll_key(cv2)

        # Deliberately before model initialization or camera.open().
        wait_ready(cv2, lambda: show("ready"))
        report["ready_screen_used"] = True
        with GeometryExtractor(args.model) as detector:
            detector_counts = RecordingExtractor(detector)
            tap = GeometryTap(detector_counts, detector)
            source.open()
            with GeometryWorker(recorded, tap) as worker:
                began = time.monotonic()
                observations = []
                for order, target in enumerate(CALIBRATION_TARGETS, 1):
                    trial = Trial(order, 0, target, 0, 0)
                    show("calibration", trial)
                    onset = time.monotonic()
                    item = {
                        "order": order,
                        "target_id": target.name,
                        "target_x": target.x,
                        "target_y": target.y,
                        "onset_monotonic_seconds": onset,
                        "samples": [],
                    }
                    report["calibration_presentations"].append(item)

                    _, end = collect_window(
                        onset,
                        SETTLE_SECONDS + SAMPLE_SECONDS,
                        SETTLE_SECONDS,
                        worker,
                        lambda: poll_key(cv2),
                        lambda: show("transition"),
                        rows=item["samples"],
                    )
                    item["end_monotonic_seconds"] = end
                    for row in item["samples"]:
                        row.update(
                            target_id=target.name,
                            target_x=target.x,
                            target_y=target.y,
                            block=0,
                            phase="calibration",
                            presentation_order=order,
                        )
                    item["summary"] = summarize_trial(item["samples"], target.x, target.y)
                    observations.append(
                        (
                            target,
                            [
                                (r["horizontal_feature"], r["vertical_feature"])
                                for r in item["samples"]
                                if r["feature_status"] == "usable"
                            ],
                        )
                    )
                mapping, _ = fit_session_calibration(observations)
                report["mapping_coefficients"] = asdict(mapping)
                worker.mapping = mapping
                for trial in schedule():
                    item = {**trial.identity(), "samples": []}
                    report["trials"].append(item)
                    show("cue", trial)
                    item["cue_onset_monotonic_seconds"] = wait_fixed(
                        CUE_SECONDS, lambda: poll_key(cv2)
                    )
                    show("target", trial)
                    onset = time.monotonic()
                    item["onset_monotonic_seconds"] = onset

                    _, end = collect_window(
                        onset,
                        TARGET_SECONDS,
                        0.0,
                        worker,
                        lambda: poll_key(cv2),
                        lambda: show("transition"),
                        rows=item["samples"],
                    )
                    item["end_monotonic_seconds"] = end
                    for row in item["samples"]:
                        row.update(
                            **trial.identity(), phase="validation", presentation_order=trial.order
                        )
                    item["display_deadline_overrun_seconds"] = max(0, end - onset - TARGET_SECONDS)
                    item["summary"] = summarize_trial(
                        item["samples"], trial.target.x, trial.target.y
                    )
                    wait_fixed(TRANSITION_SECONDS, lambda: poll_key(cv2))
                report["elapsed_seconds"] = time.monotonic() - began
                report["status"] = "completed"
    finally:
        report.update(
            camera_resolution=list(recorded.resolution) if recorded.resolution else None,
            camera_reads=recorded.reads,
            failed_camera_reads=recorded.failed_reads,
            no_face_observations=detector_counts.no_face if detector_counts else 0,
        )
        source.close()
        if window_created:
            cv2.destroyWindow(window)
    inspect_capture(report)
    return report


def run(args):
    invalid = args.output.with_name(f"{args.output.stem}.invalid.json")
    if args.output.exists() or invalid.exists():
        print("Refusing to overwrite an existing capture or invalid attempt", file=sys.stderr)
        return 1
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    report = {
        **configuration(),
        "participant": args.participant,
        "session": args.session,
        "session_role": SESSION_ROLES[args.session],
        "detector": {
            "mediapipe_version": version("mediapipe"),
            "model_sha256": sha256(args.model.read_bytes()).hexdigest(),
            "options_policy": "production_defaults_unchanged",
            "camera_intrinsics": None,
        },
        "camera_index": args.camera_index,
        "ready_screen_used": False,
        "status": "incomplete",
        "calibration_presentations": [],
        "trials": [],
    }
    destination = args.output
    result = 0
    try:
        collect_session(args, report)
    except (KeyboardInterrupt, InterruptedError, RuntimeError, ValueError, OSError) as error:
        report.update(status="invalid_incomplete_run", reason=str(error) or type(error).__name__)
        destination = invalid
        result = 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    print(f"{report['status']}: {destination}")
    return result


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
