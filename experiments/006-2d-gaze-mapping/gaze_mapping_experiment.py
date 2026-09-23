"""Guided same-session 2D gaze-mapping feasibility capture; no computer control."""

import argparse
import csv
import importlib.util
import math
import random
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from analyze_mapping import analyze_rows, fit_models, print_report, quality_flags, target_summaries

PRIOR_SCRIPT = Path(__file__).parents[1] / "004-vertical-gaze" / "vertical_gaze_experiment.py"
SPEC = importlib.util.spec_from_file_location("vertical_gaze_experiment", PRIOR_SCRIPT)
prior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prior)

WINDOW = "2D gaze mapping feasibility - q / Esc to cancel"
CALIBRATION = tuple(
    (f"C-{row}-{column}", x, y)
    for row, y in enumerate((0.20, 0.50, 0.80), start=1)
    for column, x in enumerate((0.20, 0.50, 0.80), start=1)
)
VALIDATION = (
    ("V-1", 0.35, 0.35),
    ("V-2", 0.65, 0.35),
    ("V-3", 0.35, 0.65),
    ("V-4", 0.65, 0.65),
    ("V-5", 0.50, 0.35),
    ("V-6", 0.65, 0.50),
    ("V-7", 0.50, 0.65),
    ("V-8", 0.35, 0.50),
)
CSV_FIELDS = (
    "timestamp_s",
    "phase",
    "presentation_index",
    "target_id",
    "trial_number",
    "target_x",
    "target_y",
    "face_detected",
    "geometry_valid",
    "horizontal_feature",
    "vertical_feature",
    "left_horizontal",
    "right_horizontal",
    "left_vertical_local_axis",
    "right_vertical_local_axis",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "binocular_eye_opening",
    "head_center_y",
    "camera_width",
    "camera_height",
    "window_width",
    "window_height",
)


def build_order(seed, validation_repeats):
    order = [("calibration", *target, 1) for target in CALIBRATION]
    validation = [
        ("validation", *target, trial)
        for trial in range(1, validation_repeats + 1)
        for target in VALIDATION
    ]
    random.Random(seed).shuffle(validation)
    return order + validation


def draw_target(phase, target_id, x, y, position, total, sampling, remaining, width, height):
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    point = (round(x * width), round(y * height))
    cv2.circle(canvas, point, 24, (255, 255, 255), 3)
    cv2.circle(canvas, point, 7, (0, 190, 255), -1)
    label = "SAMPLING" if sampling else "SETTLING"
    for text, baseline, scale in (
        (f"{phase.upper()} {target_id} — look at the dot", 50, 0.8),
        (f"Target {position}/{total} | {label} | {remaining:.1f}s", 90, 0.65),
        ("Natural blinking; keep head approximately stable. q / Esc: cancel", height - 30, 0.55),
    ):
        cv2.putText(
            canvas,
            text,
            (30, baseline),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (225, 225, 225),
            2,
        )
    return canvas


def write_rows(path, rows):
    with path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def options_for(model):
    return mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True,
    )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, default=1)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--settle-seconds", type=float, default=0.8)
    parser.add_argument("--sample-seconds", type=float, default=1.2)
    parser.add_argument("--validation-repeats", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, help="New local CSV path for derived numbers only")
    parser.add_argument(
        "--check-model", action="store_true", help="Initialize model without camera"
    )
    args = parser.parse_args()
    if args.camera_index < 0 or args.validation_repeats < 2:
        parser.error("camera index must be nonnegative and validation repeats at least two")
    if not all(math.isfinite(value) for value in (args.settle_seconds, args.sample_seconds)):
        parser.error("durations must be finite")
    if args.settle_seconds <= 0 or args.sample_seconds <= 0:
        parser.error("settle/sample durations must be positive")
    return args


def run(args):
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output and args.output.exists() and not args.check_model:
        print(f"Refusing to overwrite existing data: {args.output}", file=sys.stderr)
        return 1

    camera = None
    window_created = False
    try:
        with mp.tasks.vision.FaceLandmarker.create_from_options(
            options_for(args.model)
        ) as landmarker:
            if args.check_model:
                print(
                    f"Face Landmarker initialized: MediaPipe {mp.__version__}, "
                    f"OpenCV {cv2.__version__}, model {args.model}"
                )
                return 0

            camera = cv2.VideoCapture(args.camera_index)
            if not camera.isOpened():
                raise RuntimeError(f"Could not open camera index {args.camera_index}")

            cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
            window_created = True
            cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(WINDOW, np.full((700, 1200, 3), 24, dtype=np.uint8))
            cv2.waitKey(1)
            _, _, width, height = cv2.getWindowImageRect(WINDOW)
            if width <= 0 or height <= 0:
                raise RuntimeError("Could not determine target-window image-area dimensions")

            order = build_order(args.seed, args.validation_repeats)
            rows = []
            failed_reads = 0
            resolution = None
            started = time.monotonic()
            last_timestamp_ms = -1
            for position, (phase, target_id, x, y, trial) in enumerate(order, start=1):
                began = time.monotonic()
                duration = args.settle_seconds + args.sample_seconds
                while (now := time.monotonic()) - began < duration:
                    elapsed = now - began
                    sampling = elapsed >= args.settle_seconds
                    remaining = duration - elapsed if sampling else args.settle_seconds - elapsed
                    cv2.imshow(
                        WINDOW,
                        draw_target(
                            phase,
                            target_id,
                            x,
                            y,
                            position,
                            len(order),
                            sampling,
                            remaining,
                            width,
                            height,
                        ),
                    )
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        print("Experiment cancelled; no completed dataset was saved.")
                        return 130
                    ok, frame = camera.read()
                    if not ok or frame is None:
                        failed_reads += 1
                        time.sleep(0.01)
                        continue
                    frame_height, frame_width = frame.shape[:2]
                    if resolution is None:
                        resolution = (frame_width, frame_height)
                    image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                    )
                    timestamp_ms = max(
                        int((time.monotonic() - started) * 1000), last_timestamp_ms + 1
                    )
                    last_timestamp_ms = timestamp_ms
                    result = landmarker.detect_for_video(image, timestamp_ms)
                    if not sampling:
                        continue

                    row = {
                        "timestamp_s": round(time.monotonic() - started, 6),
                        "phase": phase,
                        "presentation_index": position,
                        "target_id": target_id,
                        "trial_number": trial,
                        "target_x": x,
                        "target_y": y,
                        "face_detected": int(bool(result.face_landmarks)),
                        "geometry_valid": 0,
                        "camera_width": frame_width,
                        "camera_height": frame_height,
                        "window_width": width,
                        "window_height": height,
                    }
                    if result.face_landmarks:
                        row.update(prior.blink_scores(result))
                        measured = prior.measure_features(
                            result.face_landmarks[0], frame_width, frame_height
                        )
                        if measured is not None:
                            row.update(
                                geometry_valid=1,
                                horizontal_feature=measured["binocular_horizontal_control"],
                                vertical_feature=measured["binocular_vertical_local_axis"],
                                left_horizontal=measured["left_horizontal_control"],
                                right_horizontal=measured["right_horizontal_control"],
                                left_vertical_local_axis=measured["left_vertical_local_axis"],
                                right_vertical_local_axis=measured["right_vertical_local_axis"],
                                binocular_eye_opening=measured["binocular_eye_opening"],
                                head_center_y=measured["head_center_y"],
                            )
                    rows.append(row)

                if phase == "calibration" and position == len(CALIBRATION):
                    calibration_rows = rows[:]
                    calibration_flags = quality_flags(calibration_rows)
                    summaries = target_summaries(calibration_rows, calibration_flags)
                    fit_models(summaries)
                    print(
                        "Calibration samples support both candidate fits; collecting held-out targets."
                    )

            analysis = analyze_rows(rows)
            print(
                f"Camera index {args.camera_index}, input resolution {resolution}, "
                f"window image area {width} x {height}, failed camera reads {failed_reads}, "
                f"elapsed {time.monotonic() - started:.2f}s"
            )
            print_report(analysis)
            if args.output:
                write_rows(args.output, rows)
                print(f"Local derived-numerical CSV: {args.output}")
            return 0
    except KeyboardInterrupt:
        print("Experiment interrupted; no completed dataset was saved.", file=sys.stderr)
        return 130
    except (cv2.error, RuntimeError, ValueError, OSError) as error:
        print(f"Experiment failed: {error}", file=sys.stderr)
        return 1
    finally:
        if camera is not None:
            camera.release()
        if window_created:
            cv2.destroyWindow(WINDOW)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
