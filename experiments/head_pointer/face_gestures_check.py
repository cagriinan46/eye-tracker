"""Record per-user face-gesture scores to set wink, long-blink and smile thresholds (Issue #160).

Guided phases in a full-screen OpenCV window: neutral, looking/tilting down and up,
right winks, left winks, natural blinks, long closures and smiles. Saves only
MediaPipe blendshape scores and head pitch per frame (no images or landmarks), then
prints per-phase percentiles and what the current EyeGestures detector reports.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from experiments.desktop_demo.eye_gestures import EyeGestures
from experiments.head_pointer.signals import angle_signal
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import open_target_window

SCORES = (
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "eyeSquintLeft",
    "eyeSquintRight",
    "mouthSmileLeft",
    "mouthSmileRight",
)
PHASES = (
    ("neutral", 6, "Ekrana normal bak, rahat dur."),
    ("down", 6, "Kafani asagi eg ve ekranin altina bak."),
    ("up", 5, "Kafani yukari kaldir ve ekranin ustune bak."),
    ("wink_right", 12, "Sadece SAG gozunu 5 kez kirp (her biri kisa, ~0.3 sn)."),
    ("wink_left", 12, "Sadece SOL gozunu 5 kez kirp (her biri kisa, ~0.3 sn)."),
    ("blink", 8, "Normal sekilde 5 kez goz kirp."),
    ("long_blink", 10, "Iki gozunu 3 kez yaklasik 0.5 sn kapat."),
    ("smile", 12, "3 kez gulumse (dudaklarini kivir), aralarda normal yuz."),
    ("talk", 8, "Kendi kendine bir sey soyle / konus (yanlis alarm testi)."),
)
DEFAULT_MODEL = Path(".venv/models/face_landmarker.task")


def percentiles(values, points=(5, 50, 95, 100)):
    if not values:
        return None
    ordered = sorted(values)
    return {
        p: round(ordered[min(len(ordered) - 1, int(p / 100 * (len(ordered) - 1)))], 3)
        for p in points
    }


def summarize(frames):
    summary = {}
    for phase, *_ in PHASES:
        rows = [f for f in frames if f["phase"] == phase and f["scores"]]
        gestures = EyeGestures()
        events = gestures.feed(
            [
                (
                    f["t"],
                    f["scores"]["eyeBlinkLeft"],
                    f["scores"]["eyeBlinkRight"],
                    (f["scores"]["mouthSmileLeft"] + f["scores"]["mouthSmileRight"]) / 2,
                )
                for f in rows
            ]
        )
        summary[phase] = {
            "frames": len(rows),
            "events": events,
            **{name: percentiles([f["scores"][name] for f in rows]) for name in SCORES},
            "pitch": percentiles([f["pitch"] for f in rows if f["pitch"] is not None]),
        }
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--screen-size", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"Refusing to overwrite {args.output}", file=sys.stderr)
        return 1
    width, height = (int(v) for v in args.screen_size.lower().split("x"))

    import cv2
    import mediapipe as mp
    import numpy as np

    vision = mp.tasks.vision
    detector = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(args.model)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
    )
    source = OpenCVCameraSource(args.camera_index)
    window = "Yuz hareketleri olcumu - q ile cik"
    frames, started, last_ms = [], time.monotonic(), -1
    completed = False
    try:
        source.open()
        width, height = open_target_window(cv2, np, window, (width, height))
        for index, (phase, seconds, text) in enumerate(PHASES, start=1):
            ready_until = time.monotonic() + 2.5
            phase_end = None
            while True:
                now = time.monotonic()
                recording = now >= ready_until
                if recording and phase_end is None:
                    phase_end = now + seconds
                if phase_end is not None and now >= phase_end:
                    break
                frame = source.read()
                scores, pitch = None, None
                if frame is not None:
                    rgb = cv2.cvtColor(frame.payload, cv2.COLOR_BGR2RGB)
                    last_ms = max(last_ms + 1, frame.timestamp_ns // 1_000_000)
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), last_ms
                    )
                    if result.face_blendshapes:
                        all_scores = {c.category_name: c.score for c in result.face_blendshapes[0]}
                        scores = {name: round(float(all_scores[name]), 4) for name in SCORES}
                    if result.facial_transformation_matrixes:
                        angles = angle_signal(result.facial_transformation_matrixes[0])
                        pitch = round(angles[1], 2) if angles else None
                    if recording:
                        frames.append(
                            {
                                "phase": phase,
                                "t": round(frame.timestamp_ns / 1e9, 4),
                                "scores": scores,
                                "pitch": pitch,
                            }
                        )
                canvas = np.full((height, width, 3), 24, dtype=np.uint8)
                color = (80, 200, 80) if recording else (0, 210, 255)
                cv2.putText(canvas, f"{index}/{len(PHASES)}", (60, 90), 0, 1.0, (160,) * 3, 2)
                cv2.putText(canvas, text, (60, height // 2), 0, 1.0, (235,) * 3, 2)
                remaining = (phase_end - now) if phase_end else (ready_until - now)
                label = f"Kayit: {remaining:.0f} sn" if recording else "Hazirlan..."
                cv2.putText(canvas, label, (60, height // 2 + 60), 0, 0.9, color, 2)
                cv2.putText(
                    canvas,
                    "Yuz bulundu" if scores else "Yuz bulunamadi",
                    (60, height - 60),
                    0,
                    0.8,
                    (80, 200, 80) if scores else (60, 60, 230),
                    2,
                )
                cv2.imshow(window, canvas)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    raise KeyboardInterrupt
        completed = True
    except KeyboardInterrupt:
        print("Cancelled; partial record saved.", file=sys.stderr)
    finally:
        source.close()
        detector.close()
        cv2.destroyAllWindows()
        record = {
            "issue": 160,
            "started_local": datetime.now().astimezone().isoformat(timespec="seconds"),
            "camera_index": args.camera_index,
            "completed": completed,
            "duration_s": round(time.monotonic() - started, 1),
            "phases": [p[:2] for p in PHASES],
            "frames": frames,
        }
        record["summary"] = summarize(frames)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record))
        print(json.dumps(record["summary"], indent=1))
    return 0 if completed else 2


if __name__ == "__main__":
    raise SystemExit(main())
