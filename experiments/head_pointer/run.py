"""Human-run Issue #156 session: shared calibration, then one target block per candidate.

Hardware imports stay inside ``run`` so CI remains camera-free. Saves numbers only:
the three candidate signals per frame, cursor positions, mappings and outcomes.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from experiments.head_pointer import protocol
from experiments.head_pointer.analysis import summarize
from experiments.head_pointer.pointer import DwellTrial, OneEuroFilter2D, fit_mapping
from experiments.head_pointer.signals import CANDIDATES, candidate_signals
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import open_target_window

DEFAULT_MODEL = Path(".venv/models/face_landmarker.task")
BACKGROUND = (24, 24, 24)
WHITE, GREY = (235, 235, 235), (120, 120, 120)
CYAN, GREEN, RED, YELLOW = (255, 220, 0), (80, 200, 80), (60, 60, 230), (0, 210, 255)


class Cancelled(Exception):
    pass


class HeadExtractor:
    """Face Landmarker in VIDEO mode with the facial transformation matrix enabled."""

    def __init__(self, model_path: Path) -> None:
        import cv2
        import mediapipe

        self._cv2, self._mp = cv2, mediapipe
        vision = mediapipe.tasks.vision
        options = vision.FaceLandmarkerOptions(
            base_options=mediapipe.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._last_ms = -1

    def signals(self, frame) -> dict:
        image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=self._cv2.cvtColor(frame.payload, self._cv2.COLOR_BGR2RGB),
        )
        stamp = max(self._last_ms + 1, frame.timestamp_ns // 1_000_000)
        self._last_ms = stamp
        result = self._landmarker.detect_for_video(image, stamp)
        faces = result.face_landmarks or []
        landmarks = [(p.x, p.y) for p in faces[0]] if faces and faces[0] else None
        matrices = result.facial_transformation_matrixes or []
        matrix = matrices[0] if len(matrices) else None
        return candidate_signals(landmarks, matrix)

    def close(self) -> None:
        self._landmarker.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True)
    parser.add_argument("--session", required=True, choices=protocol.SESSIONS)
    parser.add_argument("--camera-index", required=True, type=int)
    parser.add_argument("--screen-size", required=True, help="logical WxH, e.g. 1512x982")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    try:
        width, height = (int(v) for v in args.screen_size.lower().split("x"))
    except ValueError:
        parser.error("--screen-size must look like 1512x982")
    args.screen_size = (width, height)
    return args


def _signals_json(signals: dict) -> dict:
    return {k: (list(v) if v is not None else None) for k, v in signals.items()}


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output.exists():
        print(f"Refusing to overwrite existing result: {args.output}", file=sys.stderr)
        return 1

    import cv2
    import numpy as np

    window = f"Head pointer {args.participant}/{args.session} - q / Esc"
    record: dict = {
        "issue": 156,
        "participant": args.participant,
        "session": args.session,
        "camera_index": args.camera_index,
        "started_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "candidate_order": list(protocol.SESSION_ORDER[args.session]),
        "constants": {
            k: getattr(protocol, k) for k in dir(protocol) if k.isupper() and k != "SESSION_ORDER"
        },
        "completed": False,
        "calibration": [],
        "mappings": {},
        "trials": [],
        "frames": [],
        "failed_reads": 0,
        "no_face_frames": 0,
    }
    source = OpenCVCameraSource(args.camera_index)
    extractor = HeadExtractor(args.model)
    started = time.monotonic()

    def sample() -> tuple[float, dict | None]:
        frame = source.read()
        now = time.monotonic()
        if frame is None:
            record["failed_reads"] += 1
            return now, None
        signals = extractor.signals(frame)
        if all(v is None for v in signals.values()):
            record["no_face_frames"] += 1
        return now, signals

    def show(canvas) -> None:
        cv2.imshow(window, canvas)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            raise Cancelled
        return key

    def text(canvas, message, y, color=WHITE, scale=0.8):
        cv2.putText(canvas, message, (40, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)

    def blank():
        return np.full((height, width, 3), BACKGROUND, dtype=np.uint8)

    def wait_for_space(lines: list[str]) -> None:
        while True:
            _, signals = sample()
            canvas = blank()
            for i, line in enumerate(lines):
                text(canvas, line, 80 + 44 * i)
            face = signals is not None and signals.get("ANGLES") is not None
            text(
                canvas,
                "Yuz bulundu" if face else "Yuz bulunamadi",
                height - 60,
                GREEN if face else RED,
            )
            if show(canvas) == ord(" "):
                return

    def pixels(normalized):
        return (
            min(max(normalized[0], 0.0), 1.0) * (width - 1),
            min(max(normalized[1], 0.0), 1.0) * (height - 1),
        )

    width, height = args.screen_size
    try:
        source.open()
        width, height = open_target_window(cv2, np, window, args.screen_size)
        wait_for_space(
            [
                "Kafa imleci karsilastirmasi (Issue #156)",
                "Once kalibrasyon: her noktayi BURNUNUZLA gosterin, gozle degil.",
                "Rahat ve dik oturun. Baslamak icin BOSLUK, cikmak icin q.",
            ]
        )

        for point in protocol.calibration_schedule():
            target = (round(point.x * (width - 1)), round(point.y * (height - 1)))
            phase_start = time.monotonic()
            total = protocol.SETTLE_SECONDS + protocol.SAMPLE_SECONDS
            while (now := time.monotonic()) - phase_start < total:
                elapsed = now - phase_start
                sampling = elapsed >= protocol.SETTLE_SECONDS
                _, signals = sample()
                if sampling and signals is not None:
                    record["calibration"].append(
                        {
                            "point": point.index,
                            "target_x": point.x,
                            "target_y": point.y,
                            "t": round(now - started, 4),
                            "signals": _signals_json(signals),
                        }
                    )
                canvas = blank()
                ring = int(40 * max(0.0, 1 - elapsed / protocol.SETTLE_SECONDS)) + 10
                cv2.circle(canvas, target, ring, GREY, 2)
                cv2.circle(canvas, target, 9, YELLOW if sampling else WHITE, -1)
                text(
                    canvas,
                    f"Kalibrasyon {point.index}/9 - burnunuzla noktayi gosterin",
                    40,
                    GREY,
                    0.7,
                )
                show(canvas)

        mappings = {}
        for candidate in CANDIDATES:
            mapping = fit_mapping(record["calibration"], candidate)
            if mapping is not None:
                mappings[candidate] = mapping
                record["mappings"][candidate] = {
                    "x": [mapping.x.intercept, mapping.x.slope],
                    "y": [mapping.y.intercept, mapping.y.slope],
                }
        if not mappings:
            raise RuntimeError("no candidate could be calibrated")

        schedule = protocol.target_schedule(args.session)
        order = protocol.SESSION_ORDER[args.session]
        smoother = OneEuroFilter2D()
        for block, candidate in enumerate(order, start=1):
            trials = [t for t in schedule if t.candidate == candidate]
            if candidate not in mappings:
                for t in trials:
                    record["trials"].append(
                        {
                            "candidate": candidate,
                            "number": t.number,
                            "practice": t.practice,
                            "x": t.x,
                            "y": t.y,
                            "diameter": t.diameter,
                            "outcome": "uncalibrated",
                            "elapsed": None,
                            "entries": 0,
                            "first_entry": None,
                            "hold_jitter_px": None,
                        }
                    )
                continue
            wait_for_space(
                [
                    f"Aday {block}/3",
                    "Burnunuzla imleci hedef dairenin icine getirin ve bekleyin.",
                    f"Ilk {protocol.PRACTICE_TRIALS} hedef alistirma. Hazir olunca BOSLUK.",
                ]
            )
            smoother.reset()
            cursor = None
            mapping = mappings[candidate]
            for t in trials:
                center = pixels((t.x, t.y))
                trial = DwellTrial(center, t.diameter / 2)
                trial_start = time.monotonic()
                feedback_end = None
                while True:
                    now, signals = sample()
                    rel = now - trial_start
                    value = signals.get(candidate) if signals else None
                    raw = pixels(mapping(value)) if value is not None else None
                    measured = smoother.update(now, raw) if raw is not None else None
                    if measured is not None:
                        cursor = measured
                    trial.update(rel, measured)
                    record["frames"].append(
                        {
                            "t": round(now - started, 4),
                            "candidate": candidate,
                            "trial": t.number,
                            "signals": _signals_json(signals) if signals else None,
                            "raw": [round(v, 1) for v in raw] if raw else None,
                            "cursor": [round(v, 1) for v in measured] if measured else None,
                        }
                    )
                    canvas = blank()
                    c = tuple(map(round, center))
                    r = round(t.diameter / 2)
                    if trial.outcome is None:
                        cv2.circle(canvas, c, r, WHITE, 2)
                        progress = trial.progress(rel)
                        if progress > 0:
                            cv2.ellipse(
                                canvas, c, (r + 6, r + 6), -90, 0, 360 * progress, YELLOW, 3
                            )
                    else:
                        color = GREEN if trial.outcome == "selected" else RED
                        cv2.circle(canvas, c, r, color, -1)
                        feedback_end = feedback_end or now + protocol.FEEDBACK_SECONDS
                    if cursor is not None:
                        x, y = map(round, cursor)
                        cv2.line(canvas, (x - 12, y), (x + 12, y), CYAN, 2)
                        cv2.line(canvas, (x, y - 12), (x, y + 12), CYAN, 2)
                    label = "alistirma" if t.practice else "olcum"
                    text(
                        canvas,
                        f"Aday {block}/3  hedef {t.number}/{len(trials)} ({label})",
                        40,
                        GREY,
                        0.7,
                    )
                    show(canvas)
                    if feedback_end is not None and now >= feedback_end:
                        break
                record["trials"].append(
                    {
                        "candidate": candidate,
                        "number": t.number,
                        "practice": t.practice,
                        "x": t.x,
                        "y": t.y,
                        "diameter": t.diameter,
                        "outcome": trial.outcome,
                        "elapsed": trial.elapsed,
                        "entries": trial.entries,
                        "first_entry": trial.first_entry,
                        "hold_jitter_px": trial.hold_jitter(),
                    }
                )
        record["completed"] = True
    except Cancelled:
        print("Cancelled by the participant; partial record saved.", file=sys.stderr)
    finally:
        record["duration_s"] = round(time.monotonic() - started, 1)
        source.close()
        extractor.close()
        cv2.destroyAllWindows()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record))
        print(f"Saved {args.output}")
    print(json.dumps(summarize([record])["candidates"], indent=2))
    return 0 if record["completed"] else 2


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
