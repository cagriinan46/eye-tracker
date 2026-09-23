"""Compare local vertical eye features in a guided, camera-only experiment."""

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

LABELS = ("UP", "CENTER", "DOWN")
WINDOW = "Vertical gaze features - q / Esc to stop"
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 700
TARGETS = {"UP": 0.18, "CENTER": 0.50, "DOWN": 0.82}
METHODS = ("bbox", "local_axis", "lid_distances")
EYES = ("left", "right", "binocular")
BLINK_NAMES = ("eyeBlinkLeft", "eyeBlinkRight")


def connection_indices(connections):
    return sorted({index for edge in connections for index in (edge.start, edge.end)})


EYE_GEOMETRY = {
    "left": {
        "contour": connection_indices(FaceLandmarksConnections.FACE_LANDMARKS_LEFT_EYE),
        "iris": connection_indices(FaceLandmarksConnections.FACE_LANDMARKS_LEFT_IRIS),
        "corners": (263, 362),
        "upper": 386,
        "lower": 374,
    },
    "right": {
        "contour": connection_indices(FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_EYE),
        "iris": connection_indices(FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_IRIS),
        "corners": (33, 133),
        "upper": 159,
        "lower": 145,
    },
}
for geometry in EYE_GEOMETRY.values():
    assert set((*geometry["corners"], geometry["upper"], geometry["lower"])) <= set(
        geometry["contour"]
    )
REQUIRED_LANDMARKS = (
    max(
        index
        for geometry in EYE_GEOMETRY.values()
        for index in (*geometry["contour"], *geometry["iris"])
    )
    + 1
)
CANDIDATES = tuple(f"{eye}_vertical_{method}" for method in METHODS for eye in EYES)
CSV_FIELDS = (
    "timestamp_s",
    "target_label",
    "trial_number",
    "condition",
    "face_detected",
    "geometry_valid",
    *CANDIDATES,
    "left_horizontal_control",
    "right_horizontal_control",
    "binocular_horizontal_control",
    "left_eye_opening",
    "right_eye_opening",
    "binocular_eye_opening",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "binocular_blink",
    "head_center_y",
)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


def pixel_point(landmark, frame_width, frame_height):
    return landmark.x * frame_width, landmark.y * frame_height


def measure_eye(landmarks, geometry, frame_width, frame_height):
    """Return baseline and three vertical candidates, or None for invalid geometry."""
    needed = set((*geometry["contour"], *geometry["iris"]))
    if not all(
        math.isfinite(landmarks[index].x) and math.isfinite(landmarks[index].y) for index in needed
    ):
        return None

    contour = [pixel_point(landmarks[i], frame_width, frame_height) for i in geometry["contour"]]
    iris_points = [pixel_point(landmarks[i], frame_width, frame_height) for i in geometry["iris"]]
    iris = (
        statistics.fmean(p[0] for p in iris_points),
        statistics.fmean(p[1] for p in iris_points),
    )
    corner_a, corner_b = (
        pixel_point(landmarks[i], frame_width, frame_height) for i in geometry["corners"]
    )
    upper = pixel_point(landmarks[geometry["upper"]], frame_width, frame_height)
    lower = pixel_point(landmarks[geometry["lower"]], frame_width, frame_height)

    x_min, x_max = min(p[0] for p in contour), max(p[0] for p in contour)
    y_min, y_max = min(p[1] for p in contour), max(p[1] for p in contour)
    eye_axis = subtract(corner_b, corner_a)
    eye_width = math.hypot(*eye_axis)
    if eye_width <= 1e-6 or x_max - x_min <= 1e-6 or y_max - y_min <= 1e-6:
        return None

    normal = (-eye_axis[1] / eye_width, eye_axis[0] / eye_width)
    lid_gap = dot(subtract(lower, upper), normal)
    if lid_gap < 0:
        normal = (-normal[0], -normal[1])
        lid_gap = -lid_gap
    upper_distance = math.dist(iris, upper)
    lower_distance = math.dist(iris, lower)
    if lid_gap <= 1e-6 or upper_distance + lower_distance <= 1e-6:
        return None

    corner_midpoint = ((corner_a[0] + corner_b[0]) / 2, (corner_a[1] + corner_b[1]) / 2)
    return {
        "vertical_bbox": (iris[1] - y_min) / (y_max - y_min),
        "vertical_local_axis": dot(subtract(iris, corner_midpoint), normal) / eye_width,
        "vertical_lid_distances": (upper_distance - lower_distance)
        / (upper_distance + lower_distance),
        "horizontal_control": (iris[0] - x_min) / (x_max - x_min),
        "eye_opening": lid_gap / eye_width,
        "head_center_y": corner_midpoint[1] / frame_height,
    }


def measure_features(landmarks, frame_width, frame_height):
    if len(landmarks) < REQUIRED_LANDMARKS:
        return None
    left = measure_eye(landmarks, EYE_GEOMETRY["left"], frame_width, frame_height)
    right = measure_eye(landmarks, EYE_GEOMETRY["right"], frame_width, frame_height)
    if left is None or right is None:
        return None
    measured = {}
    for method in METHODS:
        key = f"vertical_{method}"
        measured[f"left_{key}"] = left[key]
        measured[f"right_{key}"] = right[key]
        measured[f"binocular_{key}"] = (left[key] + right[key]) / 2
    for key in ("horizontal_control", "eye_opening"):
        measured[f"left_{key}"] = left[key]
        measured[f"right_{key}"] = right[key]
        measured[f"binocular_{key}"] = (left[key] + right[key]) / 2
    measured["head_center_y"] = (left["head_center_y"] + right["head_center_y"]) / 2
    return measured


def blink_scores(result):
    if not result.face_blendshapes or not result.face_blendshapes[0]:
        return {}
    scores = {
        category.category_name: category.score
        for category in result.face_blendshapes[0]
        if category.category_name in BLINK_NAMES and category.score is not None
    }
    if len(scores) == len(BLINK_NAMES):
        scores["binocular_blink"] = statistics.fmean(scores.values())
    return scores


def draw_target(label, position, total, phase, remaining, condition):
    canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH, 3), 24, dtype=np.uint8)
    point = (CANVAS_WIDTH // 2, round(TARGETS[label] * CANVAS_HEIGHT))
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
        f"Trial {position}/{total} | {phase} | {remaining:.1f}s | {condition} | q/Esc: cancel",
        (35, CANVAS_HEIGHT - 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (180, 220, 180) if phase == "SAMPLING" else (180, 180, 255),
        2,
    )
    return canvas


def describe(values):
    if not values:
        return "n=0"
    deviation = statistics.stdev(values) if len(values) > 1 else 0.0
    return (
        f"n={len(values)}, mean={statistics.fmean(values):.4f}, "
        f"std={deviation:.4f}, range=[{min(values):.4f}, {max(values):.4f}]"
    )


def within_label_correlation(rows, feature, confound):
    """Descriptive correlation after centering both signals within each label."""
    centered = []
    for label in LABELS:
        pairs = [
            (row[feature], row[confound])
            for row in rows
            if row["target_label"] == label
            and isinstance(row.get(feature), (int, float))
            and isinstance(row.get(confound), (int, float))
        ]
        if len(pairs) < 2:
            continue
        feature_mean = statistics.fmean(pair[0] for pair in pairs)
        confound_mean = statistics.fmean(pair[1] for pair in pairs)
        centered.extend((x - feature_mean, y - confound_mean) for x, y in pairs)
    if len(centered) < 3:
        return None
    numerator = sum(x * y for x, y in centered)
    feature_variance = sum(x * x for x, _ in centered)
    confound_variance = sum(y * y for _, y in centered)
    if feature_variance <= 1e-12 or confound_variance <= 1e-12:
        return None
    return numerator / math.sqrt(feature_variance * confound_variance)


def print_summary(rows, order, counts, resolution, elapsed, condition, trials):
    usable = [row for row in rows if row.get("geometry_valid") == 1]
    print("\nVertical gaze feature experiment summary")
    print(f"Condition: {condition} | Elapsed: {elapsed:.2f} s")
    print(f"Input resolution: {resolution or 'unavailable'} | Trial order: {', '.join(order)}")
    print(
        f"Sampling frames: {len(rows)} | Usable: {len(usable)} | "
        f"No face: {counts['no_face']} | Invalid geometry: {counts['invalid']} | "
        f"Failed camera reads: {counts['read_failures']} | "
        f"Missing blink scores: {counts['missing_blink']}"
    )
    print(f"Tracking-loss events: {counts['tracking_loss']}")
    for candidate in CANDIDATES:
        print(f"\n{candidate}")
        values_by_label = {}
        for label in LABELS:
            selected = [row for row in usable if row["target_label"] == label]
            values = [row[candidate] for row in selected]
            values_by_label[label] = values
            print(f"  {label}: {describe(values)}")
            for trial in range(1, trials + 1):
                trial_values = [row[candidate] for row in selected if row["trial_number"] == trial]
                trial_mean = f"{statistics.fmean(trial_values):.4f}" if trial_values else "N/A"
                print(f"    trial {trial}: n={len(trial_values)}, mean={trial_mean}")
        for first, second in (("UP", "CENTER"), ("CENTER", "DOWN"), ("UP", "DOWN")):
            a, b = values_by_label[first], values_by_label[second]
            if a and b:
                overlap = max(min(a), min(b)) <= min(max(a), max(b))
                print(
                    f"  {first} - {second}: mean delta={statistics.fmean(a) - statistics.fmean(b):+.4f}; "
                    f"raw ranges overlap: {'yes' if overlap else 'no'}"
                )
            else:
                print(f"  {first} - {second}: unavailable")

        eye = candidate.split("_", 1)[0]
        blink = {"left": "eyeBlinkLeft", "right": "eyeBlinkRight"}.get(eye, "binocular_blink")
        for confound in (blink, f"{eye}_eye_opening", "head_center_y"):
            correlation = within_label_correlation(usable, candidate, confound)
            value = f"{correlation:+.3f}" if correlation is not None else "N/A"
            print(f"  Within-label correlation with {confound}: {value}")

    print("\nConfounding signals by direction (descriptive only):")
    for label in LABELS:
        selected = [row for row in usable if row["target_label"] == label]
        print(f"  {label}:")
        for key in (
            "eyeBlinkLeft",
            "eyeBlinkRight",
            "left_eye_opening",
            "right_eye_opening",
            "head_center_y",
            "binocular_horizontal_control",
        ):
            values = [row[key] for row in selected if isinstance(row.get(key), (int, float))]
            print(f"    {key}: {describe(values)}")
    print("Correlations and overlaps are exploratory, not causal or significance tests.")


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, default=1)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--sample-seconds", type=float, default=2.0)
    parser.add_argument("--transition-seconds", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--condition", choices=("stable", "small-head-motion"), default="stable")
    parser.add_argument("--output", type=Path, help="Optional new CSV path for numerical data only")
    args = parser.parse_args()
    if args.camera_index < 0 or args.trials < 1:
        parser.error("camera-index must be non-negative and trials must be positive")
    if not all(math.isfinite(value) for value in (args.sample_seconds, args.transition_seconds)):
        parser.error("sampling and transition durations must be finite")
    if args.sample_seconds <= 0 or args.transition_seconds < 0:
        parser.error("sample-seconds must be positive and transition-seconds non-negative")
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
        "missing_blink": 0,
        "tracking_loss": 0,
    }
    resolution = None
    previous_face = None
    cancelled = False
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
            output_face_blendshapes=True,
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
                    cv2.imshow(
                        WINDOW,
                        draw_target(label, position, len(order), phase, remaining, args.condition),
                    )
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        cancelled = True
                        break

                    ok, frame = camera.read()
                    if not ok or frame is None:
                        counts["read_failures"] += 1
                        time.sleep(0.01)
                        continue
                    height, width = frame.shape[:2]
                    if resolution is None:
                        resolution = f"{width} x {height}"
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

                    face = bool(result.face_landmarks)
                    row = {
                        "timestamp_s": round(time.monotonic() - started, 6),
                        "target_label": label,
                        "trial_number": trial,
                        "condition": args.condition,
                        "face_detected": int(face),
                        "geometry_valid": 0,
                    }
                    if not face:
                        counts["no_face"] += 1
                        if previous_face:
                            counts["tracking_loss"] += 1
                    else:
                        scores = blink_scores(result)
                        row.update(scores)
                        if not all(name in scores for name in BLINK_NAMES):
                            counts["missing_blink"] += 1
                        measured = measure_features(result.face_landmarks[0], width, height)
                        if measured is None:
                            counts["invalid"] += 1
                        else:
                            row.update(measured)
                            row["geometry_valid"] = 1
                    previous_face = face
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

    print_summary(
        rows, order, counts, resolution, time.monotonic() - started, args.condition, args.trials
    )
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
    if not any(row.get("geometry_valid") == 1 for row in rows):
        print("No usable eye-feature samples were obtained.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
