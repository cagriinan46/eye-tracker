"""Human-run Issue #158 session: shared calibration, then one block per RAY condition.

Same display, calibration and target mechanics as Issue #156. Saves numbers only.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from experiments.head_pointer import protocol as base
from experiments.head_pointer.pointer import DwellTrial, OneEuroFilter2D, fit_mapping
from experiments.head_pointer.run import (
    BACKGROUND,
    CYAN,
    DEFAULT_MODEL,
    GREEN,
    GREY,
    RED,
    WHITE,
    YELLOW,
    Cancelled,
    HeadExtractor,
    _signals_json,
)
from experiments.head_pointer_tuning import protocol
from experiments.head_pointer_tuning.analysis import summarize
from experiments.head_pointer_tuning.pointer import GainedPointer
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import open_target_window


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


def comfort_from_key(key: int) -> int | None:
    low, high = protocol.COMFORT_SCALE
    value = key - ord("0")
    return value if low <= value <= high else None


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output.exists():
        print(f"Refusing to overwrite existing result: {args.output}", file=sys.stderr)
        return 1

    import cv2
    import numpy as np

    window = f"Head pointer tuning {args.participant}/{args.session} - q / Esc"
    record: dict = {
        "issue": 158,
        "participant": args.participant,
        "session": args.session,
        "camera_index": args.camera_index,
        "started_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "signal": protocol.SIGNAL,
        "condition_order": list(protocol.SESSION_ORDER[args.session]),
        "conditions": {
            c.name: {"min_cutoff": c.min_cutoff, "beta": c.beta, "gain": c.gain}
            for c in protocol.CONDITIONS
        },
        "completed": False,
        "calibration": [],
        "mappings": {},
        "trials": [],
        "frames": [],
        "comfort": {},
        "recentres": {},
        "failed_reads": 0,
        "no_face_frames": 0,
    }
    source = OpenCVCameraSource(args.camera_index)
    extractor = HeadExtractor(args.model)
    started = time.monotonic()
    width, height = args.screen_size

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

    def show(canvas) -> int:
        cv2.imshow(window, canvas)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            raise Cancelled
        return key

    def text(canvas, message, y, color=WHITE, scale=0.8):
        cv2.putText(canvas, message, (40, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)

    def blank():
        return np.full((height, width, 3), BACKGROUND, dtype=np.uint8)

    def prompt(lines: list[str], accept) -> int:
        while True:
            _, signals = sample()
            canvas = blank()
            for i, line in enumerate(lines):
                text(canvas, line, 80 + 44 * i)
            face = signals is not None and signals.get(protocol.SIGNAL) is not None
            text(
                canvas,
                "Yuz bulundu" if face else "Yuz bulunamadi",
                height - 60,
                GREEN if face else RED,
            )
            key = show(canvas)
            if accept(key):
                return key

    def pixels(normalized):
        return (
            min(max(normalized[0], 0.0), 1.0) * (width - 1),
            min(max(normalized[1], 0.0), 1.0) * (height - 1),
        )

    try:
        source.open()
        width, height = open_target_window(cv2, np, window, args.screen_size)
        prompt(
            [
                "Kafa imleci ayari (Issue #158)",
                "Once kalibrasyon: her noktayi BURNUNUZLA gosterin, gozle degil.",
                "Rahat ve dik oturun. Baslamak icin BOSLUK, cikmak icin q.",
            ],
            lambda key: key == ord(" "),
        )

        for point in base.calibration_schedule():
            target = (round(point.x * (width - 1)), round(point.y * (height - 1)))
            phase_start = time.monotonic()
            total = base.SETTLE_SECONDS + base.SAMPLE_SECONDS
            while (now := time.monotonic()) - phase_start < total:
                elapsed = now - phase_start
                sampling = elapsed >= base.SETTLE_SECONDS
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
                ring = int(40 * max(0.0, 1 - elapsed / base.SETTLE_SECONDS)) + 10
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

        mapping = fit_mapping(record["calibration"], protocol.SIGNAL)
        if mapping is None:
            raise RuntimeError("RAY could not be calibrated")
        for name in protocol.CONDITION_NAMES:
            record["mappings"][name] = {
                "x": [mapping.x.intercept, mapping.x.slope],
                "y": [mapping.y.intercept, mapping.y.slope],
            }

        schedule = protocol.target_schedule(args.session)
        order = protocol.SESSION_ORDER[args.session]
        for block, name in enumerate(order, start=1):
            condition = protocol.BY_NAME[name]
            trials = [t for t in schedule if t.candidate == name]
            prompt(
                [
                    f"Ayar {block}/3",
                    "Burnunuzla imleci hedef dairenin icine getirin ve bekleyin.",
                    "Imlec kayarsa kafanizi ortalayip R tusuna basin (ortala).",
                    f"Ilk {base.PRACTICE_TRIALS} hedef alistirma. Hazir olunca BOSLUK.",
                ],
                lambda key: key == ord(" "),
            )
            smoother = OneEuroFilter2D(condition.min_cutoff, condition.beta)
            pointer = GainedPointer(mapping, condition.gain)
            record["recentres"][name] = 0
            cursor = None
            last_signal = None
            for t in trials:
                center = pixels((t.x, t.y))
                trial = DwellTrial(center, t.diameter / 2)
                trial_start = time.monotonic()
                feedback_end = None
                recentred = False
                while True:
                    now, signals = sample()
                    rel = now - trial_start
                    value = signals.get(protocol.SIGNAL) if signals else None
                    if value is not None:
                        last_signal = value
                    raw = pixels(pointer(value)) if value is not None else None
                    measured = smoother.update(now, raw) if raw is not None else None
                    if measured is not None:
                        cursor = measured
                    trial.update(rel, measured)
                    record["frames"].append(
                        {
                            "t": round(now - started, 4),
                            "candidate": name,
                            "trial": t.number,
                            "signals": _signals_json(signals) if signals else None,
                            "raw": [round(v, 1) for v in raw] if raw else None,
                            "cursor": [round(v, 1) for v in measured] if measured else None,
                            "recentred": recentred,
                        }
                    )
                    recentred = False
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
                        feedback_end = feedback_end or now + base.FEEDBACK_SECONDS
                    if cursor is not None:
                        x, y = map(round, cursor)
                        cv2.line(canvas, (x - 12, y), (x + 12, y), CYAN, 2)
                        cv2.line(canvas, (x, y - 12), (x, y + 12), CYAN, 2)
                    label = "alistirma" if t.practice else "olcum"
                    text(
                        canvas,
                        f"Ayar {block}/3  hedef {t.number}/{len(trials)} ({label})  R: ortala",
                        40,
                        GREY,
                        0.7,
                    )
                    key = show(canvas)
                    if key in (ord(protocol.RECENTRE_KEY), ord(protocol.RECENTRE_KEY.upper())):
                        if last_signal is not None:
                            pointer.recentre(last_signal)
                            smoother.reset()
                            record["recentres"][name] += 1
                            recentred = True
                    if feedback_end is not None and now >= feedback_end:
                        break
                record["trials"].append(
                    {
                        "candidate": name,
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
            key = prompt(
                [
                    f"Ayar {block}/3 bitti.",
                    "Bu ayar ne kadar rahatti? 1 = cok yorucu ... 5 = cok rahat",
                    "1-5 arasi bir tusa basin.",
                ],
                lambda key: comfort_from_key(key) is not None,
            )
            record["comfort"][name] = comfort_from_key(key)
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
    print(json.dumps(summarize([record]), indent=2))
    return 0 if record["completed"] else 2


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
