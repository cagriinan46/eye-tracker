"""Isolated real inference/camera worker. Preview bytes remain only in local IPC."""

import base64
import socket
import sys
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
        self.cap = self.pair = None
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
        except BaseException:
            self.close()
            raise

    def process_frame(self, frame, captured_ns, preview=False):
        row = self.pair.process(frame, self.frame_id, captured_ns)
        self.frame_id += 1
        features = eligible_features(row)
        raw = None
        if features is not None and self.mapping.weights is not None:
            raw = self.mapping.predict(features).tolist()
        point, lag = self.smoothing.update(raw, captured_ns)
        jpeg = None
        if preview:
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
            preview=jpeg,
        )

    def read(self, preview=False):
        ok, frame = self.cap.read()
        captured = time.monotonic_ns()
        if not ok:
            raise RuntimeError("Kamera bağlantısı kesildi. Kamerayı yeniden başlat.")
        # No resizing: measured intrinsics only apply to native640x480.
        return self.process_frame(frame, captured, preview)

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
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.pair is not None:
            self.pair.close()
            self.pair = None


def main(fd, camera_index):
    sock = socket.socket(fileno=fd)
    engine = None
    try:
        engine = Engine(camera_index)
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
        if engine is not None:
            engine.close()
        sock.close()


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
