"""Isolated real inference/camera worker. Preview bytes remain only in local IPC."""

import base64
import socket
import sys
import threading
import time

import numpy as np

from .mapping import Ridge
from .wire import receive, send


def eligible_features(row):
    angles = np.asarray(row.get("unigaze_angles"), float)
    ratios = np.asarray(row.get("eye_gap_ratios", []), float)
    if (
        not row.get("mgaze_valid")
        or not row.get("unigaze_valid")
        or angles.shape != (2,)
        or not np.isfinite(angles).all()
        or ratios.shape != (2,)
        or not np.isfinite(ratios).all()
        or min(ratios) < 0.1
    ):
        return None
    return angles.tolist()


class Engine:
    def __init__(self, camera_index):
        self.cap = self.pair = self.stream = None
        self.last_capture = -1
        self.eye_preview = None
        self.eye_captured = 0
        self.eye_updated = 0
        self.eye_detected = False
        try:
            import cv2

            from .paired import PairedExtractor
            from .smoothing import SOURCE_HASHES, StreamFilter

            self.cv2 = cv2
            self.pair = PairedExtractor()
            self.mapping = Ridge(standardize=True)
            self.smoothing = StreamFilter()
            self.frame_id = 0
            self.metadata = dict(
                model="UniGaze B16 joint + standardized Ridge alpha0.1",
                model_id="unigaze",
                camera_index=camera_index,
                provenance=self.pair.provenance,
                filter="HeuristicFilter look_ahead3",
                filter_source_sha256=SOURCE_HASHES,
                calibration="13 research targets, 1.5s settle + 6s window, 20 selected samples each",
                limitations=[
                    "Lateral head translation can cause large bias; recalibrate after repositioning.",
                    "Windows execution unverified; macOS worker transport only.",
                    "MGaze branch retained for validated eligibility/matching, not selected gaze output.",
                ],
            )
            self.cap = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
            if not self.cap.isOpened():
                raise RuntimeError("Kamera açılamadı. Kamera iznini kontrol et.")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            from .camera_stream import LatestCamera
            from .preview import jpeg_url

            self.stream = LatestCamera(
                self.cap, lambda frame: jpeg_url(cv2, cv2.resize(frame, (640, 480))[:, ::-1])
            )
        except BaseException:
            self.close()
            raise

    def process_frame(self, frame, captured_ns, preview=False):
        row = self.pair.process(frame, self.frame_id, captured_ns)
        self.frame_id += 1
        if preview:
            from .preview import eye_view

            crop = eye_view(self.cv2, frame, row.get("preview_eyes"))
            self.eye_detected = crop is not None
            if crop is not None:
                self.eye_preview = crop
                self.eye_captured = captured_ns / 1e9
                self.eye_updated = time.monotonic()
        else:
            self.eye_preview = None
        features = eligible_features(row)
        raw = None
        if features is not None and self.mapping.weights is not None:
            raw = self.mapping.predict(features).tolist()
        point, lag = self.smoothing.update(raw, captured_ns)
        jpeg = None
        if preview and getattr(self, "stream", None) is None:
            small = self.cv2.resize(frame, (400, 300))[:, ::-1]
            ok, data = self.cv2.imencode(".jpg", small, [self.cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok:
                jpeg = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        return dict(
            status="ok",
            captured=captured_ns / 1e9,
            features=features,
            raw_point=raw,
            point=point,
            filter_history_ms=lag,
            eligibility_reason=(
                "valid"
                if features is not None
                else "mgaze_invalid"
                if not row.get("mgaze_valid")
                else row.get("unigaze_reason") or "eye_gap_or_invalid_features"
            ),
            preview=jpeg,
        )

    def read(self, preview=False):
        self.stream.enabled = bool(preview)
        sequence, captured, frame = self.stream.read_after(self.last_capture)
        self.last_capture = sequence
        # Both estimators still see exactly this capture; old captures never queue.
        return self.process_frame(frame, captured, preview)

    def preview_snapshot(self):
        result = self.stream.preview()
        result["eye_preview"] = (
            self.eye_preview if time.monotonic() - self.eye_updated < 1.0 else None
        )
        result["eye_age_ms"] = max(0, (time.monotonic() - self.eye_captured) * 1000)
        result["eye_detected"] = self.eye_detected
        return result

    def fit(self, features, labels):
        x, y = np.asarray(features, float), np.asarray(labels, float)
        if x.shape != (260, 2) or y.shape != (260, 2):
            raise ValueError("UniGaze requires fresh13x20 calibration")
        self.mapping.fit(x, y)
        self.smoothing.reset()
        return float(
            np.linalg.norm(np.array([self.mapping.predict(v) for v in x]) - y, axis=1).mean()
        )

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None
            self.cap = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.pair is not None:
            self.pair.close()
            self.pair = None


def serve_preview(sock, engine):
    try:
        while True:
            request, _ = receive(sock)
            if request.get("command") != "preview":
                break
            send(sock, engine.preview_snapshot())
    except (EOFError, OSError):
        pass


def main(fd, camera_index, preview_fd=None):
    sock = socket.socket(fileno=fd)
    engine = None
    preview_sock = socket.socket(fileno=preview_fd) if preview_fd is not None else None
    preview_thread = None
    try:
        engine = Engine(camera_index)
        if preview_sock is not None:
            preview_thread = threading.Thread(
                target=serve_preview, args=(preview_sock, engine), daemon=True
            )
            preview_thread.start()
        send(sock, dict(status="ready", metadata=engine.metadata))
        while True:
            request, _ = receive(sock)
            command = request.get("command")
            if command == "close":
                break
            if command == "read":
                response = engine.read(request.get("preview", False))
            elif command == "fit":
                response = dict(
                    status="ok", error=engine.fit(request["features"], request["labels"])
                )
            elif command == "reset":
                engine.smoothing.reset()
                response = dict(status="ok")
            else:
                raise ValueError("Unknown worker command")
            send(sock, response)
    except (EOFError, BrokenPipeError):
        pass
    except Exception as exc:
        try:
            send(sock, dict(status="error", error=f"{type(exc).__name__}: {exc}"))
        except OSError:
            pass
    finally:
        if preview_sock is not None:
            try:
                preview_sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            preview_sock.close()
        if preview_thread is not None:
            preview_thread.join(timeout=1)
        if engine is not None:
            engine.close()
        sock.close()


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else None)
