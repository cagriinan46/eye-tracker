"""Run one full-screen Issue #84 head-assisted zone-targeting session (derived numbers only)."""

import argparse
import json
import sys
import time
from pathlib import Path

from experiments.head_vertical_targeting.online import (
    BLINK_MAX,
    CUE_SECONDS,
    DWELL_SECONDS,
    FEEDBACK_SECONDS,
    SMOOTHING_FRAMES,
    SMOOTHING_MAX_AGE_SECONDS,
    TIMEOUT_SECONDS,
    DwellSelector,
    Smoother,
    cell_of,
    fit_calibration,
    frame_point,
)
from experiments.head_vertical_targeting.protocol import (
    BLOCKS,
    CONDITION_HINTS,
    Trial,
    calibration_schedule,
    trial_schedule,
)
from experiments.vertical_signal_comparison.capture import SignalExtractor, measure_signals
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import (
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    Presentation,
    RecordingExtractor,
    RecordingSource,
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
TEXT = (225, 225, 225)
LOGGED_FIELDS = (
    "status",
    "horizontal",
    "vertical",
    "binocular_eye_opening",
    "head_center_y",
    "head_pitch_deg",
    "head_yaw_deg",
    "head_roll_deg",
    "blink_left",
    "blink_right",
    "extract_ms",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Pseudonymous participant ID")
    parser.add_argument("--session", required=True, choices=("A", "B"))
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--screen-size", type=parse_screen_size, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--seed", type=int, default=84)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if not args.participant.strip():
        parser.error("participant ID must not be blank")
    if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
        parser.error("derived numerical output must be inside the Git-ignored .venv directory")
    return args


def draw_calibration(cv2, np, presentation, position, total, sampling, remaining, width, height):
    canvas = np.full((height, width, 3), BACKGROUND, dtype=np.uint8)
    point = (round(presentation.target.x * width), round(presentation.target.y * height))
    cv2.circle(canvas, point, 24, (255, 255, 255), 3)
    cv2.circle(canvas, point, 7, TARGET, -1)
    state = "SAMPLING" if sampling else "SETTLING"
    for message, baseline, scale in (
        (BLOCKS[presentation.phase], 50, 0.9),
        (f"Calibration {position}/{total} | {state} | {remaining:.1f}s", 90, 0.65),
    ):
        cv2.putText(canvas, message, (30, baseline), cv2.FONT_HERSHEY_SIMPLEX, scale, TEXT, 2)
    return canvas


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
        cv2.rectangle(canvas, *_cell_rect(current, rows, columns, width, height), CURRENT, -1)
    if outcome is not None:
        colour = SUCCESS if outcome[0] == "success" else WRONG
        cv2.rectangle(canvas, *_cell_rect(outcome[1], rows, columns, width, height), colour, -1)
    for index in range(1, columns):
        x = round(index * width / columns)
        cv2.line(canvas, (x, 0), (x, height), GRID, 2)
    for index in range(1, rows):
        y = round(index * height / rows)
        cv2.line(canvas, (0, y), (width, y), GRID, 2)
    for cell, colour, radius in ((cue, (220, 220, 220), 9), (target, TARGET, 14)):
        if cell is None:
            continue
        top_left, bottom_right = _cell_rect(cell, rows, columns, width, height)
        centre = ((top_left[0] + bottom_right[0]) // 2, (top_left[1] + bottom_right[1]) // 2)
        cv2.circle(canvas, centre, radius, colour, -1)
        if cell == target:
            cv2.rectangle(canvas, top_left, bottom_right, TARGET, 4)
            if progress > 0:
                cv2.ellipse(canvas, centre, (34, 34), -90, 0, 360 * progress, TARGET, 4)
    cv2.putText(canvas, label, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, TEXT, 2)
    return canvas


def _logged(details: dict) -> dict:
    return {field: details.get(field) for field in LOGGED_FIELDS}


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

    window = f"Head-assisted targeting {args.participant}/{args.session} - q / Esc"
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
                    cv2.imshow(
                        window,
                        draw_calibration(
                            cv2,
                            np,
                            current,
                            position,
                            len(calibration),
                            sampling,
                            remaining,
                            width,
                            height,
                        ),
                    )
                    return cancelled()

                def measure():
                    result, details = measure_signals(recorded_source, extractor, signals)
                    if sampling_now:
                        calibration_rows.append(
                            {
                                "presentation": position,
                                "phase": presentation.phase,
                                "target_id": presentation.target.name,
                                "target_x": presentation.target.x,
                                "target_y": presentation.target.y,
                                **_logged(details),
                            }
                        )
                    return result

                collect_presentation(presentation, measure, show)

            lines = fit_calibration(calibration_rows)
            if lines is None:
                raise RuntimeError("calibration did not yield usable eye/head lines")

            trials = trial_schedule(args.session, args.seed)
            outcomes: list[dict] = []
            frames: list[dict] = []
            smoother = Smoother()
            condition = None
            for number, trial in enumerate(trials, start=1):
                if trial.condition != condition:
                    condition = trial.condition
                    smoother.reset()
                label = (
                    f"{trial.condition} {trial.layout}  trial {number}/{len(trials)}  -  "
                    f"{CONDITION_HINTS[trial.condition]}"
                )
                cue_end = time.monotonic() + CUE_SECONDS
                while (now := time.monotonic()) < cue_end:
                    _, details = measure_signals(recorded_source, extractor, signals)
                    smoother.update(now, frame_point(details, lines, trial.condition))
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
                    raw = frame_point(details, lines, trial.condition)
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
                            **_logged(details),
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
                        "condition": trial.condition,
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
                "experiment": "issue-84-head-vertical-targeting",
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
                    "blink_max": BLINK_MAX,
                    "settle_seconds": SETTLE_SECONDS,
                    "sample_seconds": SAMPLE_SECONDS,
                    "smoothing_frames": SMOOTHING_FRAMES,
                    "smoothing_max_age_seconds": SMOOTHING_MAX_AGE_SECONDS,
                    "dwell_seconds": DWELL_SECONDS,
                    "timeout_seconds": TIMEOUT_SECONDS,
                    "cue_seconds": CUE_SECONDS,
                    "feedback_seconds": FEEDBACK_SECONDS,
                },
                "lines": {
                    block: {"intercept": line.intercept, "slope": line.slope}
                    for block, line in lines.items()
                },
                "camera_reads": recorded_source.reads,
                "failed_camera_reads": recorded_source.failed_reads,
                "no_face_observations": extractor.no_face,
                "calibration_rows": calibration_rows,
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
