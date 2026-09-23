"""Measure Face Landmarker output from a live camera without saving frames."""

import argparse
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mediapipe as mp

DEFAULT_MODEL = Path(__file__).resolve().parents[2] / ".venv/models/face_landmarker.task"
BLINK_NAMES = ("eyeBlinkLeft", "eyeBlinkRight")


@dataclass
class Measurements:
    successful_reads: int = 0
    failed_reads: int = 0
    submitted_frames: int = 0
    processed_frames: int = 0
    frames_with_face: int = 0
    frames_without_face: int = 0
    tracking_loss_events: int = 0
    longest_no_face_streak: int = 0
    processing_times_ms: list[float] = field(default_factory=list)
    landmark_counts: set[int] = field(default_factory=set)
    blendshape_frames: int = 0
    blink_values: dict[str, list[float]] = field(
        default_factory=lambda: {name: [] for name in BLINK_NAMES}
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, default=1, help="Camera index (default: 1)")
    parser.add_argument(
        "--duration", type=float, default=15.0, help="Run time in seconds (default: 15)"
    )
    parser.add_argument(
        "--model", type=Path, default=DEFAULT_MODEL, help="Local Face Landmarker .task file"
    )
    parser.add_argument(
        "--preview", action="store_true", help="Show tracking overlay; q or Esc stops"
    )
    args = parser.parse_args()
    if args.camera_index < 0:
        parser.error("--camera-index must be non-negative")
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration must be a positive, finite number")
    return args


def draw_preview(frame, result, blink_scores: dict[str, float], fps: float) -> None:
    height, width = frame.shape[:2]
    if result.face_landmarks:
        for landmark in result.face_landmarks[0]:
            if 0 <= landmark.x <= 1 and 0 <= landmark.y <= 1:
                point = (int(landmark.x * width), int(landmark.y * height))
                cv2.circle(frame, point, 1, (0, 255, 0), -1)

    status = "Face detected" if result.face_landmarks else "No face detected"
    left = blink_scores.get("eyeBlinkLeft")
    right = blink_scores.get("eyeBlinkRight")
    left_text = f"{left:.3f}" if left is not None else "N/A"
    right_text = f"{right:.3f}" if right is not None else "N/A"
    lines = (
        status,
        f"eyeBlinkLeft: {left_text}  eyeBlinkRight: {right_text}",
        f"Effective FPS: {fps:.1f}",
    )
    for row, line in enumerate(lines):
        cv2.putText(frame, line, (12, 28 + row * 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imshow("Face landmark baseline", frame)


def print_summary(
    camera_index: int,
    model_path: Path,
    elapsed: float,
    resolution: tuple[int, int] | None,
    stats: Measurements,
) -> None:
    print("\nFace landmark baseline")
    print(f"Camera index: {camera_index}")
    print(f"Model: {model_path}")
    print(f"Elapsed time: {elapsed:.3f} s")
    print(
        f"Input resolution: {resolution[0]} x {resolution[1]}"
        if resolution
        else "Input resolution: unavailable"
    )
    print(f"Successful camera reads: {stats.successful_reads}")
    print(f"Failed camera reads: {stats.failed_reads}")
    print(f"Frames submitted: {stats.submitted_frames}")
    print(f"Frames processed: {stats.processed_frames}")
    print(f"Frames with detected face: {stats.frames_with_face}")
    print(f"Frames without detected face: {stats.frames_without_face}")
    if stats.processed_frames:
        success_rate = 100 * stats.frames_with_face / stats.processed_frames
        print(f"Face-detection success: {success_rate:.2f}%")
    else:
        print("Face-detection success: N/A")
    print(
        f"Effective processing FPS: {stats.processed_frames / elapsed:.2f}"
        if elapsed
        else "Effective processing FPS: N/A"
    )
    if stats.processing_times_ms:
        ordered = sorted(stats.processing_times_ms)
        p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
        print(f"Average processing/inference: {statistics.mean(ordered):.3f} ms")
        print(f"Median processing/inference: {statistics.median(ordered):.3f} ms")
        print(f"p95 processing/inference: {p95:.3f} ms")
    else:
        print("Processing/inference times: unavailable")
    counts = ", ".join(str(count) for count in sorted(stats.landmark_counts)) or "none observed"
    print(f"Observed landmark counts: {counts}")
    print(f"Frames with blendshape output: {stats.blendshape_frames}")
    for name in BLINK_NAMES:
        values = stats.blink_values[name]
        value_range = f"{min(values):.3f} to {max(values):.3f}" if values else "unavailable"
        print(f"{name} observed range: {value_range}")
    print(f"Tracking-loss events: {stats.tracking_loss_events}")
    print(f"Longest no-face streak: {stats.longest_no_face_streak} processed frames")


def main() -> int:
    args = parse_args()
    if not args.model.is_file():
        print(
            f"Model not found: {args.model}. See README.md for download instructions.",
            file=sys.stderr,
        )
        return 2

    camera = cv2.VideoCapture(args.camera_index)
    if not camera.isOpened():
        camera.release()
        print(f"Could not open camera index {args.camera_index}.", file=sys.stderr)
        return 1

    stats = Measurements()
    resolution: tuple[int, int] | None = None
    previous_face_detected = False
    no_face_streak = 0
    last_timestamp_ms = -1
    interrupted = False
    failure: str | None = None
    start: float | None = None

    try:
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(args.model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
        )
        with mp.tasks.vision.FaceLandmarker.create_from_options(options) as landmarker:
            start = time.perf_counter()
            while time.perf_counter() - start < args.duration:
                ok, frame = camera.read()
                if not ok or frame is None:
                    stats.failed_reads += 1
                    time.sleep(0.01)
                    continue

                stats.successful_reads += 1
                if resolution is None:
                    height, width = frame.shape[:2]
                    resolution = (width, height)

                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                )
                timestamp_ms = max(last_timestamp_ms + 1, int((time.perf_counter() - start) * 1000))
                last_timestamp_ms = timestamp_ms
                stats.submitted_frames += 1
                inference_start = time.perf_counter()
                result = landmarker.detect_for_video(image, timestamp_ms)
                stats.processing_times_ms.append((time.perf_counter() - inference_start) * 1000)
                stats.processed_frames += 1

                face_detected = bool(result.face_landmarks)
                blink_scores: dict[str, float] = {}
                if face_detected:
                    stats.frames_with_face += 1
                    stats.landmark_counts.add(len(result.face_landmarks[0]))
                    no_face_streak = 0
                    if result.face_blendshapes and result.face_blendshapes[0]:
                        stats.blendshape_frames += 1
                        blink_scores = {
                            category.category_name: category.score
                            for category in result.face_blendshapes[0]
                            if category.category_name in BLINK_NAMES and category.score is not None
                        }
                        for name, score in blink_scores.items():
                            stats.blink_values[name].append(score)
                else:
                    stats.frames_without_face += 1
                    no_face_streak += 1
                    stats.longest_no_face_streak = max(stats.longest_no_face_streak, no_face_streak)
                    if previous_face_detected:
                        stats.tracking_loss_events += 1
                previous_face_detected = face_detected

                if args.preview:
                    fps = stats.processed_frames / (time.perf_counter() - start)
                    draw_preview(frame, result, blink_scores, fps)
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        break
    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted by user.", file=sys.stderr)
    except (cv2.error, RuntimeError, ValueError) as error:
        failure = str(error)
        print(f"Face landmark experiment failed: {error}", file=sys.stderr)
    finally:
        elapsed = time.perf_counter() - start if start is not None else 0.0
        camera.release()
        if args.preview:
            cv2.destroyAllWindows()

    print_summary(args.camera_index, args.model, elapsed, resolution, stats)
    if interrupted:
        return 130
    if failure or not stats.processed_frames:
        if not failure:
            print("No frames were processed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
