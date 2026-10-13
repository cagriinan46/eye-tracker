"""Collect one Issue #90 session from two cameras at once (derived numbers only).

Each loop reads the top camera and then the bottom camera, each through its own
unchanged Issue #77 signal path and MediaPipe detector, while one full-screen
Issue #77 schedule is shown. Rows are tagged with their camera; no images are kept.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.vertical_signal_comparison.capture import SignalExtractor, measure_signals
from experiments.vertical_signal_comparison.protocol import build_schedule
from experiments.vertical_signal_comparison.run import IGNORED_OUTPUT_DIRS
from eye_tracker.gaze.estimator import GazeUnavailable
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

CAMERAS = ("top", "bottom")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Pseudonymous participant ID")
    parser.add_argument("--session", required=True, choices=("A", "B"))
    parser.add_argument("--top-index", type=int, required=True, help="Camera above the screen")
    parser.add_argument("--bottom-index", type=int, required=True, help="Camera below the screen")
    parser.add_argument("--screen-size", type=parse_screen_size, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--seed", type=int, default=77)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if min(args.top_index, args.bottom_index) < 0:
        parser.error("camera indices must be nonnegative")
    if args.top_index == args.bottom_index:
        parser.error("top and bottom camera indices must differ")
    if not args.participant.strip():
        parser.error("participant ID must not be blank")
    output = args.output.resolve()
    if not any(output.is_relative_to(Path(d).resolve()) for d in IGNORED_OUTPUT_DIRS):
        parser.error(
            "derived numerical output must be inside a Git-ignored directory: .venv or validation/results"
        )
    return args


def first_usable(results: list) -> object:
    """Count a loop as usable for the protocol when either camera produced features."""
    for result in results:
        if not isinstance(result, GazeUnavailable):
            return result
    return results[-1]


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

    window = f"Dual camera {args.participant}/{args.session} - q / Esc"
    indices = {"top": args.top_index, "bottom": args.bottom_index}
    sources = {name: OpenCVCameraSource(indices[name]) for name in CAMERAS}
    recorded_sources = {name: RecordingSource(sources[name]) for name in CAMERAS}
    window_created = False
    try:
        with SignalExtractor(args.model) as top_signals, SignalExtractor(args.model) as bottom:
            signals = {"top": top_signals, "bottom": bottom}
            recorded_extractors = {name: RecordingExtractor(signals[name]) for name in CAMERAS}
            for name in CAMERAS:
                sources[name].open()
            window_created = True
            width, height = open_target_window(cv2, np, window, args.screen_size)
            order = build_schedule(seed=args.seed)
            rows: list[dict] = []
            counts: dict[str, dict] = {}
            loop = 0
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
                    nonlocal loop
                    loop += 1
                    results = []
                    for name in CAMERAS:
                        result, details = measure_signals(
                            recorded_sources[name], recorded_extractors[name], signals[name]
                        )
                        results.append(result)
                        if sampling_now:
                            rows.append(
                                {
                                    "camera": name,
                                    "loop": loop,
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
                    return first_usable(results)

                collected, presentation_counts = collect_presentation(presentation, measure, show)
                counts[f"{position}:{presentation.target.name}"] = {
                    "phase": presentation.phase,
                    "usable_loops": len(collected),
                    **presentation_counts,
                }
            report = {
                "experiment": "issue-90-dual-camera-vertical",
                "participant": args.participant,
                "session": args.session,
                "condition": "normal comfortable posture; natural eye opening and blinking",
                "cameras": {
                    name: {
                        "index": indices[name],
                        "resolution": recorded_sources[name].resolution,
                        "reads_including_settling": recorded_sources[name].reads,
                        "failed_reads_including_settling": recorded_sources[name].failed_reads,
                        "no_face_including_settling": recorded_extractors[name].no_face,
                    }
                    for name in CAMERAS
                },
                "window_image_area": [width, height],
                "requested_screen_size": list(args.screen_size),
                "mediapipe_version": mediapipe.__version__,
                "seed": args.seed,
                "elapsed_seconds": time.monotonic() - started,
                "settle_seconds": SETTLE_SECONDS,
                "sample_seconds": SAMPLE_SECONDS,
                "minimum_usable_samples_per_presentation": MIN_USABLE_SAMPLES,
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
        for source in sources.values():
            source.close()
        if window_created:
            cv2.destroyWindow(window)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
