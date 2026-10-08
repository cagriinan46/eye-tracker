"""Run one full-screen Issue #81 coarse zone-targeting session (derived numbers only)."""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.coarse_vertical_targeting.online import (
    CUE_SECONDS,
    DWELL_SECONDS,
    FEEDBACK_SECONDS,
    SMOOTHING_FRAMES,
    SMOOTHING_MAX_AGE_SECONDS,
    TIMEOUT_SECONDS,
    DwellSelector,
    Smoother,
    cell_of,
    fit_mapping,
    frame_point,
)
from experiments.coarse_vertical_targeting.protocol import (
    Trial,
    calibration_schedule,
    trial_schedule,
)
from experiments.vertical_signal_comparison.capture import SignalExtractor, measure_signals
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import (
    Presentation,
    RecordingExtractor,
    RecordingSource,
    _draw_target,
    collect_presentation,
    open_target_window,
    parse_screen_size,
)

BACKGROUND = (24, 24, 24)
GRID = (90, 90, 90)
TARGET = (0, 190, 255)
CURRENT = (70, 70, 70)
SUCCESS = (60, 180, 60)
WRONG = (40, 40, 200)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Pseudonymous participant ID")
    parser.add_argument("--session", required=True, choices=("A", "B"))
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--screen-size", type=parse_screen_size, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--seed", type=int, default=81)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if not args.participant.strip():
        parser.error("participant ID must not be blank")
    if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
        parser.error("derived numerical output must be inside the Git-ignored .venv directory")
    return args


def _cell_rect(cell, rows, columns, width, height):
    row, column = cell
    return (
        (round(column * width / columns), round(row * height / rows)),
        (round((column + 1) * width / columns) - 1, round((row + 1) * height / rows) - 1),
    )


def draw_grid(
    cv2,
    np,
    trial: Trial,
    width,
    height,
    *,
    target=None,
    current=None,
    cue=None,
    progress=0.0,
    outcome=None,
    label="",
):
    canvas = np.full((height, width, 3), BACKGROUND, dtype=np.uint8)
    rows, columns = trial.rows, trial.columns
    if current is not None:
        top_left, bottom_right = _cell_rect(current, rows, columns, width, height)
        cv2.rectangle(canvas, top_left, bottom_right, CURRENT, -1)
    if outcome is not None:
        colour = SUCCESS if outcome[0] == "success" else WRONG
        top_left, bottom_right = _cell_rect(outcome[1], rows, columns, width, height)
        cv2.rectangle(canvas, top_left, bottom_right, colour, -1)
    for index in range(1, columns):
        x = round(index * width / columns)
        cv2.line(canvas, (x, 0), (x, height), GRID, 2)
    for index in range(1, rows):
        y = round(index * height / rows)
        cv2.line(canvas, (0, y), (width, y), GRID, 2)
    for cell, radius in ((target, 14), (cue, 9)):
        if cell is None:
            continue
        top_left, bottom_right = _cell_rect(cell, rows, columns, width, height)
        centre = ((top_left[0] + bottom_right[0]) // 2, (top_left[1] + bottom_right[1]) // 2)
        cv2.circle(canvas, centre, radius, TARGET if cell == target else (220, 220, 220), -1)
        if cell == target:
            cv2.rectangle(canvas, top_left, bottom_right, TARGET, 4)
            if progress > 0:
                cv2.ellipse(canvas, centre, (34, 34), -90, 0, 360 * progress, TARGET, 4)
    cv2.putText(canvas, label, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (225, 225, 225), 2)
    return canvas


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

    window = f"Coarse zone targeting {args.participant}/{args.session} - q / Esc"
    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window_created = False

    def cancelled() -> bool:
        return cv2.waitKey(1) & 0xFF in (ord("q"), 27)

    try:
        with SignalExtractor(args.model) as signals:
            extractor = RecordingExtractor(signals)
            source.open()
            window_created = True
            width, height = open_target_window(cv2, np, window, args.screen_size)
            started = time.monotonic()

            calibration = calibration_schedule(args.seed)
            calibration_rows: list[dict] = []
            for position, presentation in enumerate(calibration, start=1):
                sampling_now = False

                def show(current: Presentation, sampling: bool, remaining: float) -> bool:
                    nonlocal sampling_now
                    sampling_now = sampling
                    canvas = _draw_target(
                        cv2,
                        np,
                        current,
                        position,
                        len(calibration),
                        sampling,
                        remaining,
                        width,
                        height,
                    )
                    cv2.imshow(window, canvas)
                    return cancelled()

                def measure():
                    result, details = measure_signals(recorded_source, extractor, signals)
                    if sampling_now:
                        calibration_rows.append(
                            {
                                "presentation": position,
                                "phase": "calibration",
                                "target_id": presentation.target.name,
                                "target_x": presentation.target.x,
                                "target_y": presentation.target.y,
                                "trial_number": 1,
                                **details,
                            }
                        )
                    return result

                collect_presentation(presentation, measure, show)

            mapping = fit_mapping(calibration_rows)
            if mapping is None:
                raise RuntimeError("calibration did not yield a usable COMBO mapping")

            trials = trial_schedule(args.session, args.seed)
            outcomes: list[dict] = []
            frames: list[dict] = []
            smoother = Smoother()
            for number, trial in enumerate(trials, start=1):
                label = f"{trial.layout}  trial {number}/{len(trials)}"
                cue_end = time.monotonic() + CUE_SECONDS
                while (now := time.monotonic()) < cue_end:
                    _, details = measure_signals(recorded_source, extractor, signals)
                    smoother.update(now, frame_point(details, mapping))
                    cv2.imshow(
                        window, draw_grid(cv2, np, trial, width, height, cue=trial.cue, label=label)
                    )
                    if cancelled():
                        raise InterruptedError("session cancelled")
                selector = DwellSelector()
                onset = time.monotonic()
                selected, decided_at = None, None
                while (now := time.monotonic()) - onset < TIMEOUT_SECONDS:
                    _, details = measure_signals(recorded_source, extractor, signals)
                    raw = frame_point(details, mapping)
                    smoothed = smoother.update(now, raw)
                    cell = (
                        None if smoothed is None else cell_of(smoothed, trial.rows, trial.columns)
                    )
                    choice = selector.update(now, cell)
                    frames.append(
                        {
                            "trial": number,
                            "seconds_from_onset": now - onset,
                            "raw": list(raw) if raw else None,
                            "smoothed": list(smoothed) if smoothed else None,
                            "cell": list(cell) if cell else None,
                            "blink": max(details["blink_left"], details["blink_right"])
                            if details.get("blink_left") is not None
                            and details.get("blink_right") is not None
                            else None,
                        }
                    )
                    cv2.imshow(
                        window,
                        draw_grid(
                            cv2,
                            np,
                            trial,
                            width,
                            height,
                            target=trial.target,
                            current=cell,
                            progress=selector.progress(now),
                            label=label,
                        ),
                    )
                    if cancelled():
                        raise InterruptedError("session cancelled")
                    if choice is not None:
                        selected, decided_at = choice, now - onset
                        break
                result = (
                    "timeout"
                    if selected is None
                    else "success"
                    if selected == trial.target
                    else "wrong"
                )
                outcomes.append(
                    {
                        "trial": number,
                        "layout": trial.layout,
                        "rows": trial.rows,
                        "columns": trial.columns,
                        "target": list(trial.target),
                        "cue": list(trial.cue),
                        "result": result,
                        "selected": list(selected) if selected else None,
                        "selection_seconds": decided_at,
                    }
                )
                feedback_end = time.monotonic() + FEEDBACK_SECONDS
                while time.monotonic() < feedback_end:
                    cv2.imshow(
                        window,
                        draw_grid(
                            cv2,
                            np,
                            trial,
                            width,
                            height,
                            target=trial.target,
                            outcome=(result, selected) if selected else None,
                            label=label,
                        ),
                    )
                    if cancelled():
                        raise InterruptedError("session cancelled")

            report = {
                "experiment": "issue-81-coarse-vertical-targeting",
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
                "settings": {
                    "smoothing_frames": SMOOTHING_FRAMES,
                    "smoothing_max_age_seconds": SMOOTHING_MAX_AGE_SECONDS,
                    "dwell_seconds": DWELL_SECONDS,
                    "timeout_seconds": TIMEOUT_SECONDS,
                    "cue_seconds": CUE_SECONDS,
                    "feedback_seconds": FEEDBACK_SECONDS,
                },
                "mapping": {
                    "x_coefficients": mapping.x_coefficients,
                    "y_coefficients": mapping.y_coefficients,
                    "calibration_presentations": mapping.calibration_presentations,
                },
                "camera_reads": recorded_source.reads,
                "failed_camera_reads": recorded_source.failed_reads,
                "no_face_observations": extractor.no_face,
                "outcomes": outcomes,
                "frames": frames,
            }
            text = json.dumps(report, indent=2, allow_nan=False)
            with args.output.open("x", encoding="utf-8") as destination:
                destination.write(text + "\n")
            print(f"Completed {len(outcomes)} trials; derived data: {args.output}")
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
