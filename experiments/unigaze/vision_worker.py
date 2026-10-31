"""Baseline environment worker; camera never opened."""

import hashlib
import socket
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .signals import EYES, eye_signal, image_signal
from .wire import receive, send

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main(fd):
    sock = socket.socket(fileno=fd)
    face = gaze = extractor = None
    try:
        import cv2

        from experiments.gazefollower_baseline.diagnostics import eye_metrics, finite_values
        from experiments.gazefollower_baseline.run import (
            SUPPORT,
            UPSTREAM_COMMIT,
            eligible,
            load_components,
        )
        from eye_tracker.vision.contracts import CameraFrame
        from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor

        config, face, gaze, *_ = load_components(
            SimpleNamespace(
                upstream=SUPPORT / "upstream", face_model=SUPPORT / "face_landmarker.task"
            )
        )
        extractor = MediaPipeFaceLandmarkExtractor(SUPPORT / "face_landmarker.task")
        baseline_files = [
            SUPPORT / "upstream/gazefollower/res/model_weights/base.mnn",
            SUPPORT / "face_landmarker.task",
            ROOT / "experiments/gazefollower_baseline/run.py",
            ROOT / "src/eye_tracker/vision/face_tracker.py",
        ] + list((SUPPORT / "upstream/gazefollower").rglob("*.py"))
        send(
            sock,
            {
                "status": "ready",
                "baseline": {
                    "expected_upstream_commit": UPSTREAM_COMMIT,
                    "source_hashes": {
                        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline_files
                    },
                },
            },
        )
        while True:
            meta, payload = receive(sock)
            if meta["command"] == "close":
                break
            if len(payload) != 2 * 640 * 480 * 3:
                raise ValueError("Expected original and corrected frames")
            frames = np.frombuffer(payload, np.uint8).reshape(2, 480, 640, 3)
            original, corrected = frames
            t = time.perf_counter()
            f = face.detect(meta["timestamp_ns"], original)
            g = gaze.detect(cv2.cvtColor(original, cv2.COLOR_BGR2RGB), f)
            valid = eligible(f, g, config.eye_blink_threshold)
            baseline_ms = 1000 * (time.perf_counter() - t)
            t = time.perf_counter()
            observation = extractor.extract(CameraFrame(corrected, 640, 480, meta["timestamp_ns"]))
            landmarks_ms = 1000 * (time.perf_counter() - t)
            diagnostic_started = time.perf_counter()
            points = observation.landmarks
            corrected_points = (
                None if points is None else np.array([[p.x * 640, p.y * 480] for p in points])
            )
            diagnostics = dict(
                raw_frame=image_signal(original),
                mgaze_face_rect=finite_values(getattr(f, "face_rect", None), 4),
                mgaze_eyes={},
                corrected_eyes={},
            )
            for side, indices in EYES.items():
                rect = finite_values(getattr(f, side + "_rect", None), 4)
                diagnostics["mgaze_eyes"][side] = dict(
                    rect=rect,
                    image=eye_metrics(original, rect),
                    landmark_geometry=eye_signal(getattr(f, "face_landmarks", None), indices, rect),
                )
                diagnostics["corrected_eyes"][side] = eye_signal(corrected_points, indices)
            landmarks = (
                None
                if points is None or len(points) < 468
                else [[p.x * 640, p.y * 480] for p in points[:468]]
            )
            raw_points = getattr(f, "face_landmarks", None)
            preview_eyes = None
            if raw_points is not None:
                raw_points = np.asarray(raw_points, float)
                if raw_points.ndim == 2 and len(raw_points) >= 478:
                    selected = [
                        raw_points[[a, b, u, low, *ring], :2]
                        for a, b, u, low, ring in EYES.values()
                    ]
                    if all(np.isfinite(p).all() for p in selected):
                        preview_eyes = [p.tolist() for p in selected]
            send(
                sock,
                dict(
                    status="ok",
                    preview_eyes=preview_eyes,
                    frame_id=meta["frame_id"],
                    timestamp_ns=meta["timestamp_ns"],
                    raw_sha256=hashlib.sha256(original.tobytes()).hexdigest(),
                    corrected_sha256=hashlib.sha256(corrected.tobytes()).hexdigest(),
                    mgaze_features=g.features.tolist() if valid else None,
                    mgaze_valid=valid,
                    mgaze_ms=baseline_ms,
                    diagnostics=diagnostics,
                    landmarks=landmarks,
                    landmarks_ms=landmarks_ms,
                    diagnostics_ms=1000 * (time.perf_counter() - diagnostic_started),
                ),
            )
    except EOFError:
        pass
    except Exception as exc:
        try:
            send(sock, {"status": "error", "error": f"{type(exc).__name__}: {exc}"})
        except OSError:
            pass
        raise
    finally:
        if extractor is not None:
            extractor.close()
        if face is not None:
            face.release()
        if gaze is not None:
            gaze.release()
        sock.close()


if __name__ == "__main__":
    main(int(sys.argv[1]))
