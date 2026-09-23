"""Measure basic camera capture behavior on the development Mac."""

import argparse
import math
import statistics
import sys
import time

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument(
        "--duration", type=float, default=10.0, help="Run time in seconds (default: 10)"
    )
    parser.add_argument(
        "--preview", action="store_true", help="Show live frames; press q or Esc to stop"
    )
    args = parser.parse_args()
    if args.camera_index < 0:
        parser.error("--camera-index must be non-negative")
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration must be a positive, finite number")
    return args


def print_summary(
    camera_index: int,
    elapsed: float,
    resolution: tuple[int, int] | None,
    successful_frames: int,
    failed_reads: int,
    acquisition_times_ms: list[float],
) -> None:
    print("\nCamera capture baseline")
    print(f"Camera index: {camera_index}")
    print(f"Elapsed time: {elapsed:.3f} s")
    if resolution is None:
        print("Frame resolution: unavailable (no successful frames)")
    else:
        print(f"Frame resolution: {resolution[0]} x {resolution[1]}")
    print(f"Successful frames: {successful_frames}")
    print(f"Failed frame reads: {failed_reads}")
    print(
        f"Effective FPS: {successful_frames / elapsed:.2f}" if elapsed > 0 else "Effective FPS: N/A"
    )
    if acquisition_times_ms:
        ordered = sorted(acquisition_times_ms)
        p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
        print(f"Average frame acquisition: {statistics.mean(ordered):.3f} ms")
        print(f"Median frame acquisition: {statistics.median(ordered):.3f} ms")
        print(f"p95 frame acquisition: {p95:.3f} ms")
    else:
        print("Frame acquisition times: unavailable (no read attempts)")


def main() -> int:
    args = parse_args()
    camera = cv2.VideoCapture(args.camera_index)
    if not camera.isOpened():
        camera.release()
        print(f"Could not open camera index {args.camera_index}.", file=sys.stderr)
        return 1

    successful_frames = 0
    failed_reads = 0
    acquisition_times_ms: list[float] = []
    resolution: tuple[int, int] | None = None
    interrupted = False
    start = time.perf_counter()

    try:
        while time.perf_counter() - start < args.duration:
            read_start = time.perf_counter()
            ok, frame = camera.read()
            acquisition_times_ms.append((time.perf_counter() - read_start) * 1000)
            if not ok or frame is None:
                failed_reads += 1
                continue

            successful_frames += 1
            if resolution is None:
                height, width = frame.shape[:2]
                resolution = (width, height)

            if args.preview:
                cv2.imshow("Camera capture baseline", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted by user.", file=sys.stderr)
    except cv2.error as error:
        print(f"OpenCV capture error: {error}", file=sys.stderr)
        return 1
    finally:
        elapsed = time.perf_counter() - start
        camera.release()
        if args.preview:
            cv2.destroyAllWindows()

    print_summary(
        args.camera_index,
        elapsed,
        resolution,
        successful_frames,
        failed_reads,
        acquisition_times_ms,
    )
    if interrupted:
        return 130
    if successful_frames == 0:
        print("No frames were captured.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
