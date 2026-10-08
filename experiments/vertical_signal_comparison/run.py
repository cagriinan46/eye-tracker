"""Collect one full-screen Issue #77 vertical-signal session (derived numbers only)."""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.vertical_signal_comparison.capture import SignalExtractor, measure_signals
from experiments.vertical_signal_comparison.protocol import build_schedule
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import (
    MIN_USABLE_SAMPLES,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    Presentation,
    RecordingExtractor,
    RecordingSource,
    _draw_target,
    collect_presentation,
    open_target_window,
    parse_screen_size,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Pseudonymous participant ID")
    parser.add_argument("--session", required=True, choices=("A", "B"))
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--screen-size", type=parse_screen_size, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--seed", type=int, default=77)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if not args.participant.strip():
        parser.error("participant ID must not be blank")
    if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
        parser.error("derived numerical output must be inside the Git-ignored .venv directory")
    return args


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output.exists():
        print(f"Refusing to overwrite existing result: {args.output}", file=sys.stderr)
        return 1

    # Human-only imports keep CI hardware-free.
    import cv2
    import mediapipe
    import numpy as np

    window = f"Vertical signals {args.participant}/{args.session} - q / Esc"
    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window_created = False
    try:
        with SignalExtractor(args.model) as signals:
            recorded_extractor = RecordingExtractor(signals)
            source.open()
            window_created = True
            width, height = open_target_window(cv2, np, window, args.screen_size)
            order = build_schedule(seed=args.seed)
            rows: list[dict] = []
            counts: dict[str, dict] = {}
            started = time.monotonic()
            for position, presentation in enumerate(order, start=1):
                sampling_now = False

                def show(current: Presentation, sampling: bool, remaining: float) -> bool:
                    nonlocal sampling_now
                    sampling_now = sampling
                    canvas = _draw_target(
                        cv2, np, current, position, len(order), sampling, remaining, width, height
                    )
                    cv2.imshow(window, canvas)
                    return cv2.waitKey(1) & 0xFF in (ord("q"), 27)

                def measure():
                    result, details = measure_signals(recorded_source, recorded_extractor, signals)
                    if sampling_now:
                        rows.append(
                            {
                                "presentation": position,
                                "phase": presentation.phase,
                                "target_id": presentation.target.name,
                                "target_x": presentation.target.x,
                                "target_y": presentation.target.y,
                                "trial_number": presentation.trial,
                                "monotonic_seconds": time.monotonic() - started,
                                **details,
                            }
                        )
                    return result

                collected, presentation_counts = collect_presentation(presentation, measure, show)
                counts[f"{position}:{presentation.target.name}"] = {
                    "phase": presentation.phase,
                    "usable_samples": len(collected),
                    **presentation_counts,
                }
            report = {
                "experiment": "issue-77-vertical-signal-comparison",
                "participant": args.participant,
                "session": args.session,
                "condition": "normal comfortable posture; natural eye opening and blinking",
                "camera_index": args.camera_index,
                "camera_resolution": recorded_source.resolution,
                "window_image_area": [width, height],
                "requested_screen_size": list(args.screen_size),
                "mediapipe_version": mediapipe.__version__,
                "seed": args.seed,
                "elapsed_seconds": time.monotonic() - started,
                "settle_seconds": SETTLE_SECONDS,
                "sample_seconds": SAMPLE_SECONDS,
                "minimum_usable_samples_per_presentation": MIN_USABLE_SAMPLES,
                "camera_reads_including_settling": recorded_source.reads,
                "failed_camera_reads_including_settling": recorded_source.failed_reads,
                "no_face_observations_including_settling": recorded_extractor.no_face,
                "collection_counts": counts,
                "rows": rows,
            }
            text = json.dumps(report, indent=2, allow_nan=False)
            with args.output.open("x", encoding="utf-8") as destination:
                destination.write(text + "\n")
            print(f"Completed {len(order)} presentations; derived data: {args.output}")
            return 0
    except (KeyboardInterrupt, InterruptedError):
        print("Session cancelled; no result saved.", file=sys.stderr)
        return 130
    except (cv2.error, RuntimeError, ValueError, OSError) as error:
        print(f"Session failed: {error}", file=sys.stderr)
        return 1
    finally:
        source.close()
        if window_created:
            cv2.destroyWindow(window)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
