"""Isolated real inference/camera worker. Preview bytes remain only in local IPC."""

import base64
import os
import resource
import socket
import sys
import threading
import time
from collections import deque

import numpy as np

from .blink_stream import BlinkStream
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


class EyeClosure:
    """Classify bilateral closure against recent open-eye apertures."""

    def __init__(self, minimum_open):
        self.minimum_open = minimum_open
        self.open_samples = deque(maxlen=40)

    def update(self, ratios):
        ratios = np.asarray(ratios, dtype=float)
        if ratios.shape != (2,) or not np.isfinite(ratios).all() or np.any(ratios < 0):
            return None
        if not self.open_samples:
            if min(ratios) < self.minimum_open:
                return None
            self.open_samples.append(ratios)
            return False
        baseline = np.median(self.open_samples, axis=0)
        closed = ratios < baseline * 0.68
        if not np.any(closed):
            self.open_samples.append(ratios)
            return False
        return True if np.all(closed) else None


class Engine:
    model_id = "unigaze"

    def __init__(self, camera_index):
        self.cap = self.pair = self.stream = self.blinks = None
        self.last_capture = -1
        self.eye_preview = None
        self.eye_captured = 0
        self.eye_updated = 0
        self.eye_detected = False
        self.eye_closure = EyeClosure(self.minimum_eye_open)
        self.eyes_closed = None
        self.cpu_seconds = None
        try:
            import cv2

            from .smoothing import SOURCE_HASHES, StreamFilter

            self.cv2 = cv2
            self.pair = self.create_extractor()
            self.mapping = Ridge(standardize=True)
            self.smoothing = StreamFilter()
            self.frame_id = 0
            self.metadata = dict(
                model=self.model_description,
                model_id=self.model_id,
                camera_index=camera_index,
                provenance=self.pair.provenance,
                filter="HeuristicFilter look_ahead3",
                filter_source_sha256=SOURCE_HASHES,
                calibration="13 targets with 20 standard or 10 quick samples per target",
                limitations=[
                    "Lateral head translation can cause large bias; recalibrate after repositioning.",
                    "Windows execution unverified; macOS worker transport only.",
                    *self.model_limitations,
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

            self.stream = LatestCamera(self.cap, lambda frame: jpeg_url(cv2, frame[:, ::-1]))
            self.blinks = BlinkStream(self.stream, cv2)
        except BaseException:
            self.close()
            raise

    minimum_eye_open = 0.10
    model_description = "UniGaze B16 joint + standardized Ridge alpha0.1"
    model_limitations = ("MGaze supplies face matching and eligibility.",)

    def create_extractor(self):
        from .paired import PairedExtractor

        return PairedExtractor()

    def observe(self, frame, captured_ns):
        row = self.pair.process(frame, self.frame_id, captured_ns)
        self.frame_id += 1
        self.eyes_closed = self.eye_closure.update(row.get("eye_gap_ratios"))
        features = eligible_features(row)
        if features is not None:
            reason = "valid"
        elif not row.get("mgaze_valid"):
            reason = "mgaze_invalid"
        else:
            reason = row.get("unigaze_reason") or "eye_gap_or_invalid_features"
        return features, row.get("preview_eyes"), reason

    def process_frame(self, frame, captured_ns, preview=False):
        features, eyes, reason = self.observe(frame, captured_ns)
        if preview:
            from .preview import eye_view

            crop = eye_view(self.cv2, frame, eyes)
            self.eye_detected = crop is not None
            if crop is not None:
                self.eye_preview = crop
                self.eye_captured = captured_ns / 1e9
                self.eye_updated = time.monotonic()
        else:
            self.eye_preview = None
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
            eligibility_reason=reason,
            eyes_closed=getattr(self, "eyes_closed", None),
            preview=jpeg,
        )

    def read(self, preview=False, timing=False, blink=False):
        if preview:
            self.blinks.start()
        self.blinks.enable(blink)
        self.stream.enabled = bool(preview)
        requested = time.perf_counter()
        sequence, captured, frame = self.stream.read_after(self.last_capture)
        received, received_ns = time.perf_counter(), time.monotonic_ns()
        skipped = sequence - self.last_capture - 1 if self.last_capture >= 0 else None
        self.last_capture = sequence
        # Both estimators still see exactly this capture; old captures never queue.
        response = self.process_frame(frame, captured, preview)
        response["blink_samples"] = self.blinks.drain() if blink else None
        if timing:
            response["timing"] = self.timing(
                requested, received, received_ns, captured, sequence, skipped
            )
        return response

    def timing(self, requested, received, received_ns, captured_ns, sequence, skipped):
        """Opt-in aggregate timings (issue #145); no image or gaze content."""
        worker_ms = (time.perf_counter() - received) * 1000
        cpu = os.times()
        cpu_seconds = cpu.user + cpu.system
        cpu_ms = None if self.cpu_seconds is None else (cpu_seconds - self.cpu_seconds) * 1000
        self.cpu_seconds = cpu_seconds
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        pair = dict(getattr(self.pair, "last_timing", None) or {})
        paired_ms = pair.get("paired_ms")
        return dict(
            pair,
            camera_sequence=sequence,
            skipped_frames=skipped,
            wait_ms=(received - requested) * 1000,
            start_age_ms=(received_ns - captured_ns) / 1e6,
            worker_ms=worker_ms,
            post_ms=None if paired_ms is None else worker_ms - paired_ms,
            worker_cpu_ms=cpu_ms,
            # macOS reports bytes, Linux kibibytes.
            worker_rss_mb=rss / 2**20 if sys.platform == "darwin" else rss / 2**10,
        )

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
        if x.shape not in ((130, 2), (260, 2)) or y.shape != x.shape:
            raise ValueError("Kalibrasyon 13 noktada 10 veya 20 örnek gerektirir.")
        _, counts = np.unique(y, axis=0, return_counts=True)
        if len(counts) != 13 or not np.all(counts == len(x) // 13):
            raise ValueError("Kalibrasyon örnekleri 13 noktaya eşit dağılmalı.")
        self.mapping.fit(x, y)
        self.smoothing.reset()
        return float(
            np.linalg.norm(np.array([self.mapping.predict(v) for v in x]) - y, axis=1).mean()
        )

    def close(self):
        if self.blinks is not None:
            self.blinks.close()
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


class MPIIFaceEngine(Engine):
    model_id = "mpiifacegaze"
    minimum_eye_open = 0.16
    model_description = "MPIIFaceGaze ResNet-18 + standardized Ridge alpha0.1"
    model_limitations = ("One detected face is required per frame.",)

    def create_extractor(self):
        from .mpiifacegaze import Extractor

        return Extractor()

    def observe(self, frame, captured_ns):
        features, eyes, reason = self.pair.observe(frame)
        self.eyes_closed = None
        if eyes is not None:
            points = np.asarray(eyes)
            widths = np.linalg.norm(points[:, 0] - points[:, 3], axis=1)
            gaps = np.linalg.norm(points[:, 1] - points[:, 5], axis=1) + np.linalg.norm(
                points[:, 2] - points[:, 4], axis=1
            )
            self.eyes_closed = self.eye_closure.update(gaps / (2 * np.maximum(widths, 1e-8)))
        return features, eyes, reason


def serve_preview(sock, engine):
    try:
        while True:
            request, _ = receive(sock)
            if request.get("command") != "preview":
                break
            send(sock, engine.preview_snapshot())
    except (EOFError, OSError):
        pass


def main(fd, camera_index, preview_fd=None, model_name="unigaze"):
    sock = socket.socket(fileno=fd)
    engine = None
    preview_sock = socket.socket(fileno=preview_fd) if preview_fd is not None else None
    preview_thread = None
    try:
        engine = {"unigaze": Engine, "mpiifacegaze": MPIIFaceEngine}[model_name](camera_index)
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
                response = engine.read(
                    request.get("preview", False),
                    request.get("timing", False),
                    request.get("blink", False),
                )
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
    main(
        int(sys.argv[1]),
        int(sys.argv[2]),
        int(sys.argv[3]) if len(sys.argv) > 3 else None,
        sys.argv[4] if len(sys.argv) > 4 else "unigaze",
    )
