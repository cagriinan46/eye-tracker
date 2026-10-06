"""Record fixed target windows, never grading or displaying production gaze output."""

import argparse
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from queue import Empty, SimpleQueue
from threading import Event, Thread

from eye_tracker.app.gaze_pipeline import process_gaze_frame
from eye_tracker.gaze.estimator import GazeEstimate, GazeUnavailable
from eye_tracker.vision.camera import OpenCVCameraSource
from eye_tracker.vision.eye_features import extract_binocular_features
from eye_tracker.vision.eye_topology import eye_geometry_from_observation
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor
from validation.real_calibration import (
    RecordingExtractor,
    RecordingSource,
    collect_features_once,
    fit_session_calibration,
)

from .analysis import summarize_trial, validate_capture
from .protocol import (
    CALIBRATION_TARGETS,
    CUE_SECONDS,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    TARGET_SECONDS,
    TRANSITION_SECONDS,
    Trial,
    configuration,
    schedule,
    screen_content,
)


def collect_window(
    onset, duration, sample_start, measure, poll, end_display, clock=time.monotonic, rows=None
):
    """Use a nonblocking measurement queue so camera work cannot gate display timing.

    Record completed observations from the nominal interval only. A frame begun
    before sampling onset is excluded, even if its processing completes later.
    """
    rows = [] if rows is None else rows
    deadline = onset + duration

    def append(row):
        if row is None:
            return
        observed_at = row.get("monotonic_timestamp_seconds", clock())
        started_at = row.get("measurement_started_monotonic_seconds", observed_at)
        if onset + sample_start <= started_at <= observed_at < deadline:
            rows.append(
                {
                    **row,
                    "monotonic_timestamp_seconds": observed_at,
                    "trial_relative_seconds": observed_at - onset,
                }
            )

    while clock() < deadline:
        poll()
        if clock() >= deadline:
            break
        append(measure())
    end_display()
    ended = clock()
    # Drain observations already completed before the deadline; do not wait for
    # in-flight camera work. Synchronous test callbacks omit this queue drain.
    if hasattr(measure, "drain"):
        for row in measure.drain():
            append(row)
    return rows, ended


class FeatureTap:
    """Observe exactly the frame used by production; do not change its result."""

    def __init__(self, extractor):
        self.extractor = extractor
        self.features = None

    def extract(self, frame):
        self.features = None
        observation = self.extractor.extract(frame)
        try:
            geometry = eye_geometry_from_observation(observation)
            if geometry is not None:
                self.features = extract_binocular_features(*geometry, frame.width, frame.height)
        except ValueError:
            pass  # Production process_gaze_frame reports the unavailable reason.
        return observation


def sample_row(result, source, tap):
    features = tap.features if source.last_frame is not None else None
    unavailable = result.reason.value if isinstance(result, GazeUnavailable) else None
    prediction = result if isinstance(result, GazeEstimate) else None
    frame = source.last_frame
    return {
        "feature_status": "usable" if features is not None else "unavailable",
        "gaze_status": "usable"
        if prediction
        else "unavailable"
        if unavailable
        else "not_calibrated",
        "unavailable_reason": unavailable,
        "horizontal_feature": features.horizontal if features else None,
        "vertical_feature": features.vertical if features else None,
        "predicted_x": prediction.x if prediction else None,
        "predicted_y": prediction.y if prediction else None,
        "frame_timestamp_ns": frame.timestamp_ns if frame else None,
        "camera_frame_available": frame is not None,
    }


class MeasurementWorker:
    """One camera/production pipeline owner; GUI receives nonblocking numerical rows."""

    def __init__(self, source, tap):
        self.source, self.tap = source, tap
        self.mapping = None
        self.queue = SimpleQueue()
        self.stopping = Event()
        self.thread = Thread(target=self._run, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

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
                        **sample_row(result, self.source, self.tap),
                        "measurement_started_monotonic_seconds": started,
                        "monotonic_timestamp_seconds": time.monotonic(),
                    }
                )
                # Prevent a disconnected camera from producing a busy spin.
                self.stopping.wait(0.001)
        except Exception as error:
            self.queue.put(error)

    def __call__(self):
        try:
            row = self.queue.get_nowait()
        except Empty:
            return None
        if isinstance(row, Exception):
            raise RuntimeError(f"camera/pipeline worker failed: {row}") from row
        return row

    def drain(self):
        while (row := self()) is not None:
            yield row

    def __exit__(self, *exc):
        self.stopping.set()
        self.thread.join(timeout=1)
        if self.thread.is_alive():
            self.source.source.close()
            self.thread.join(timeout=1)
        if self.thread.is_alive():
            raise RuntimeError("camera worker did not stop; capture is incomplete")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for value in (args.participant, args.session):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
            parser.error("participant/session must be simple nonempty identifiers")
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if (
        not args.output.resolve().is_relative_to(Path(".venv").resolve())
        or args.output.suffix != ".json"
    ):
        parser.error("output must be a JSON path under ignored .venv")
    return args


def draw_screen(cv2, np, content, width, height):
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    if content.target is not None:
        point = (round(content.target.x * width), round(content.target.y * height))
        cv2.circle(canvas, point, 20, (240, 240, 240), 2)
        cv2.circle(canvas, point, 5, (0, 190, 255), -1)
    else:
        for index, line in enumerate(content.lines):
            scale = min(0.7, width / max(len(line) * 22, 1))
            text_width = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)[0][0]
            cv2.putText(
                canvas,
                line,
                ((width - text_width) // 2, height // 2 + (index - len(content.lines) // 2) * 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                (225, 225, 225),
                2,
            )
    return canvas


def poll_key(cv2, delay=1):
    key = cv2.waitKey(delay) & 0xFF
    if key in (ord("q"), 27):
        raise InterruptedError("run cancelled")
    return key


def wait_ready(cv2, show):
    """No camera or measurement starts until SPACE; q/Esc remain available."""
    show()
    while poll_key(cv2, 30) != ord(" "):
        pass


def wait_fixed(duration, poll, clock=time.monotonic):
    onset = clock()
    while clock() - onset < duration:
        poll()
    return onset


def collect_session(args, report):
    # Optional vision dependencies stay lazy so core-only CI can collect these tests.
    import cv2
    import numpy as np

    window = f"Fixed-window measurement {args.participant}/{args.session}"
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
        with MediaPipeFaceLandmarkExtractor(args.model) as detector:
            detector_counts = RecordingExtractor(detector)
            tap = FeatureTap(detector_counts)
            source.open()
            with MeasurementWorker(recorded, tap) as worker:
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
                            target_id=target.name, target_x=target.x, target_y=target.y, block=0
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
                        row.update(trial.identity())
                    item["display_deadline_overrun_seconds"] = max(0, end - onset - TARGET_SECONDS)
                    item["summary"] = summarize_trial(
                        item["samples"], trial.target.x, trial.target.y
                    )
                    wait_fixed(TRANSITION_SECONDS, lambda: poll_key(cv2))
                report["elapsed_seconds"] = time.monotonic() - began
                report["status"] = "completed"
    finally:
        report.update(
            camera_resolution=recorded.resolution,
            camera_reads=recorded.reads,
            failed_camera_reads=recorded.failed_reads,
            no_face_observations=detector_counts.no_face if detector_counts else 0,
        )
        source.close()
        if window_created:
            cv2.destroyWindow(window)
    validate_capture(report)
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
