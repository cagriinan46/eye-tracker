"""Guided, local-only directional eye-feature experiment (not gaze calibration)."""

import argparse
import csv
import math
import random
import statistics
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarksConnections

LABELS = ("CENTER", "LEFT", "RIGHT", "UP", "DOWN")
WINDOW = "Directional eye features - q / Esc to stop"
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 700
TARGETS = {
    "CENTER": (0.50, 0.50),
    "LEFT": (0.18, 0.50),
    "RIGHT": (0.82, 0.50),
    "UP": (0.50, 0.18),
    "DOWN": (0.50, 0.82),
}
CSV_FIELDS = (
    "timestamp_s",
    "target_label",
    "trial_number",
    "face_detected",
    "left_horizontal",
    "right_horizontal",
    "combined_horizontal",
    "left_vertical",
    "right_vertical",
    "combined_vertical",
    "head_center_x",
    "head_center_y",
)


def indices(connections):
    """Take unique landmark indices from MediaPipe's published connection sets."""
    return sorted({index for edge in connections for index in (edge.start, edge.end)})


LEFT_EYE = indices(FaceLandmarksConnections.FACE_LANDMARKS_LEFT_EYE)
RIGHT_EYE = indices(FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_EYE)
LEFT_IRIS = indices(FaceLandmarksConnections.FACE_LANDMARKS_LEFT_IRIS)
RIGHT_IRIS = indices(FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_IRIS)
REQUIRED_LANDMARKS = max(LEFT_EYE + RIGHT_EYE + LEFT_IRIS + RIGHT_IRIS) + 1


def eye_features(landmarks, eye_indices, iris_indices):
    """Return iris position in its eye-contour bounding box and the eye center."""
    eye_x = [landmarks[index].x for index in eye_indices]
    eye_y = [landmarks[index].y for index in eye_indices]
    iris_x = statistics.fmean(landmarks[index].x for index in iris_indices)
    iris_y = statistics.fmean(landmarks[index].y for index in iris_indices)
    values = eye_x + eye_y + [iris_x, iris_y]
    if not all(math.isfinite(value) for value in values):
        return None

    x_min, x_max = min(eye_x), max(eye_x)
    y_min, y_max = min(eye_y), max(eye_y)
    if x_max - x_min <= 1e-6 or y_max - y_min <= 1e-6:
        return None
    return (
        (iris_x - x_min) / (x_max - x_min),
        (iris_y - y_min) / (y_max - y_min),
        (x_min + x_max) / 2,
        (y_min + y_max) / 2,
    )


def features(landmarks):
    if len(landmarks) < REQUIRED_LANDMARKS:
        return None
    left = eye_features(landmarks, LEFT_EYE, LEFT_IRIS)
    right = eye_features(landmarks, RIGHT_EYE, RIGHT_IRIS)
    if left is None or right is None:
        return None
    return {
        "left_horizontal": left[0],
        "right_horizontal": right[0],
        "combined_horizontal": (left[0] + right[0]) / 2,
        "left_vertical": left[1],
        "right_vertical": right[1],
        "combined_vertical": (left[1] + right[1]) / 2,
        "head_center_x": (left[2] + right[2]) / 2,
        "head_center_y": (left[3] + right[3]) / 2,
    }


def draw_target(label, trial, total_trials, phase, remaining):
    canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH, 3), 24, dtype=np.uint8)
    x, y = TARGETS[label]
    point = (round(x * CANVAS_WIDTH), round(y * CANVAS_HEIGHT))
    cv2.circle(canvas, point, 22, (255, 255, 255), 3)
    cv2.circle(canvas, point, 6, (0, 200, 255), -1)
    cv2.putText(
        canvas,
        f"Look at the target: {label}",
        (35, 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        canvas,
        f"Trial {trial}/{total_trials} | {phase} | {remaining:.1f}s | q/Esc: cancel",
        (35, CANVAS_HEIGHT - 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (180, 220, 180) if phase == "SAMPLING" else (180, 180, 255),
        2,
    )
    return canvas


def describe(values):
    if not values:
        return "n=0"
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return (
        f"n={len(values)}, mean={statistics.fmean(values):.4f}, "
        f"std={std:.4f}, range=[{min(values):.4f}, {max(values):.4f}]"
    )


def print_summary(rows, order, counts, resolution, elapsed):
    usable = [row for row in rows if row.get("combined_horizontal") is not None]
    print("\nDirectional eye-feature experiment summary")
    print(f"Elapsed: {elapsed:.2f} s | Input resolution: {resolution or 'unavailable'}")
    print(f"Trial order: {', '.join(order)}")
    print(
        f"Sampling frames: {len(rows)} | Usable samples: {len(usable)} | "
        f"No-face frames: {counts['no_face']} | Invalid geometry: {counts['invalid']} | "
        f"Failed camera reads: {counts['read_failures']}"
    )
    print(
        f"Tracking-loss events: {counts['tracking_loss']} | "
        f"Longest no-face streak: {counts['longest_no_face']} sampling frames"
    )
    for label in LABELS:
        selected = [row for row in usable if row["target_label"] == label]
        horizontal = [row["combined_horizontal"] for row in selected]
        vertical = [row["combined_vertical"] for row in selected]
        print(f"{label}: horizontal {describe(horizontal)}; vertical {describe(vertical)}")
        for eye in ("left", "right"):
            eye_h = [row[f"{eye}_horizontal"] for row in selected]
            eye_v = [row[f"{eye}_vertical"] for row in selected]
            print(f"  {eye} eye: horizontal {describe(eye_h)}; vertical {describe(eye_v)}")
        for trial in sorted({row["trial_number"] for row in rows if row["target_label"] == label}):
            trial_rows = [row for row in selected if row["trial_number"] == trial]
            trial_h = [row["combined_horizontal"] for row in trial_rows]
            trial_v = [row["combined_vertical"] for row in trial_rows]
            if trial_rows:
                print(
                    f"  trial {trial}: n={len(trial_rows)}, "
                    f"horizontal mean={statistics.fmean(trial_h):.4f}, "
                    f"vertical mean={statistics.fmean(trial_v):.4f}"
                )
            else:
                print(f"  trial {trial}: n=0")

    for axis, pairs in (
        ("horizontal", (("LEFT", "CENTER"), ("RIGHT", "CENTER"), ("LEFT", "RIGHT"))),
        ("vertical", (("UP", "CENTER"), ("DOWN", "CENTER"), ("UP", "DOWN"))),
    ):
        key = f"combined_{axis}"
        print(
            f"{axis.capitalize()} directional comparisons (signed mean delta; raw-range overlap):"
        )
        for first, second in pairs:
            a = [row[key] for row in usable if row["target_label"] == first]
            b = [row[key] for row in usable if row["target_label"] == second]
            if not a or not b:
                print(f"  {first} - {second}: unavailable")
                continue
            overlap = max(min(a), min(b)) <= min(max(a), max(b))
            print(
                f"  {first} - {second}: {statistics.fmean(a) - statistics.fmean(b):+.4f}; "
                f"ranges overlap: {'yes' if overlap else 'no'}"
            )
    print("These are descriptive single-user measurements, not significance tests.")


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, default=1)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--trials", type=int, default=3, help="Repetitions per direction")
    parser.add_argument("--sample-seconds", type=float, default=2.0)
    parser.add_argument("--transition-seconds", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, help="Optional new CSV path for derived values only")
    args = parser.parse_args()
    if args.trials < 1 or args.sample_seconds <= 0 or args.transition_seconds < 0:
        parser.error("trials must be positive, sample-seconds > 0, transition-seconds >= 0")
    return args


def run(args):
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output and args.output.exists():
        print(f"Refusing to overwrite existing data: {args.output}", file=sys.stderr)
        return 1

    order = list(LABELS) * args.trials
    random.Random(args.seed).shuffle(order)
    trial_numbers = dict.fromkeys(LABELS, 0)
    rows = []
    counts = {
        "no_face": 0,
        "invalid": 0,
        "read_failures": 0,
        "tracking_loss": 0,
        "longest_no_face": 0,
    }
    resolution = None
    cancelled = False
    previous_face = None
    no_face_streak = 0
    started = time.monotonic()
    camera = cv2.VideoCapture(args.camera_index)
    if not camera.isOpened():
        camera.release()
        print(f"Could not open camera index {args.camera_index}", file=sys.stderr)
        return 1

    try:
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(args.model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
        )
        with mp.tasks.vision.FaceLandmarker.create_from_options(options) as landmarker:
            cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW, CANVAS_WIDTH, CANVAS_HEIGHT)
            last_timestamp_ms = -1
            for position, label in enumerate(order, start=1):
                trial_numbers[label] += 1
                trial = trial_numbers[label]
                began = time.monotonic()
                end = args.transition_seconds + args.sample_seconds
                while (now := time.monotonic()) - began < end:
                    elapsed = now - began
                    sampling = elapsed >= args.transition_seconds
                    phase = "SAMPLING" if sampling else "TRANSITION"
                    remaining = end - elapsed if sampling else args.transition_seconds - elapsed
                    cv2.imshow(WINDOW, draw_target(label, position, len(order), phase, remaining))
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):
                        cancelled = True
                        break

                    ok, frame = camera.read()
                    if not ok:
                        counts["read_failures"] += 1
                        continue
                    if resolution is None:
                        resolution = f"{frame.shape[1]} x {frame.shape[0]}"
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    timestamp_ms = max(int(time.monotonic() * 1000), last_timestamp_ms + 1)
                    last_timestamp_ms = timestamp_ms
                    result = landmarker.detect_for_video(image, timestamp_ms)
                    if not sampling:
                        continue

                    row = {
                        "timestamp_s": round(time.monotonic() - started, 6),
                        "target_label": label,
                        "trial_number": trial,
                        "face_detected": int(bool(result.face_landmarks)),
                    }
                    if not result.face_landmarks:
                        counts["no_face"] += 1
                        if previous_face:
                            counts["tracking_loss"] += 1
                        no_face_streak += 1
                        counts["longest_no_face"] = max(counts["longest_no_face"], no_face_streak)
                    else:
                        no_face_streak = 0
                        measured = features(result.face_landmarks[0])
                        if measured is None:
                            counts["invalid"] += 1
                        else:
                            row.update(measured)
                    previous_face = bool(result.face_landmarks)
                    rows.append(row)
                if cancelled:
                    break
    except KeyboardInterrupt:
        cancelled = True
    except (cv2.error, RuntimeError, ValueError, OSError) as error:
        print(f"Experiment failed: {error}", file=sys.stderr)
        return 1
    finally:
        camera.release()
        cv2.destroyAllWindows()

    print_summary(rows, order, counts, resolution, time.monotonic() - started)
    if args.output:
        try:
            write_csv(args.output, rows)
        except OSError as error:
            print(f"Could not write derived CSV: {error}", file=sys.stderr)
            return 1
        print(f"Derived numerical CSV: {args.output}")
    if cancelled:
        print("Experiment cancelled before completion; do not draw a final conclusion.")
        return 130
    if not any(row.get("combined_horizontal") is not None for row in rows):
        print("No usable eye-feature samples were obtained.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run(parse_args()))
