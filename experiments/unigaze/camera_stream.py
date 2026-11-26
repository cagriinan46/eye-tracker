"""Single camera owner; bounded latest-frame handoff independent of gaze inference."""

import threading
import time
from collections import deque


class LatestCamera:
    def __init__(self, cap, encode):
        self.cap, self.encode = cap, encode
        self.condition = threading.Condition()
        self.stop = threading.Event()
        self.latest = None
        self.encoded_sequence = -1
        self.image = None
        self.timestamps = deque(maxlen=30)
        self.error = None
        self.enabled = True
        self.thread = threading.Thread(target=self._capture, daemon=True, name="camera-capture")
        self.thread.start()

    def _capture(self):
        sequence = 0
        try:
            while not self.stop.is_set():
                ok, frame = self.cap.read()
                captured = time.monotonic_ns()
                if not ok:
                    raise RuntimeError("Kamera bağlantısı kesildi. Kamerayı yeniden başlat.")
                with self.condition:
                    self.latest = (sequence, captured, frame)
                    self.timestamps.append(captured)
                    sequence += 1
                    self.condition.notify_all()
        except Exception as exc:
            with self.condition:
                self.error = str(exc)
                self.image = None
                self.condition.notify_all()
        finally:
            self.cap.release()

    def read_after(self, sequence, timeout=5):
        with self.condition:
            ready = self.condition.wait_for(
                lambda: (
                    self.error
                    or self.stop.is_set()
                    or (self.latest is not None and self.latest[0] > sequence)
                ),
                timeout,
            )
            if self.error:
                raise RuntimeError(self.error)
            if not ready or self.stop.is_set():
                raise RuntimeError("Kameradan yeni kare alınamadı.")
            return self.latest

    def preview(self):
        with self.condition:
            latest = self.latest
            timestamps = tuple(self.timestamps)
            if (
                self.error
                or self.stop.is_set()
                or latest is None
                or time.monotonic_ns() - latest[1] >= 500_000_000
            ):
                return dict(preview=None, preview_sequence=-1, preview_captured=0)
        sequence, stamp, frame = latest
        image = None
        if self.enabled:
            if self.encoded_sequence != sequence:
                self.image = self.encode(frame)
                self.encoded_sequence = sequence
            image = self.image
        fps = (
            (len(timestamps) - 1) * 1e9 / (timestamps[-1] - timestamps[0])
            if len(timestamps) > 1 and timestamps[-1] > timestamps[0]
            else None
        )
        return dict(
            preview=image,
            preview_sequence=sequence,
            preview_captured=stamp / 1e9,
            capture_size=list(frame.shape[:2][::-1]),
            capture_fps=fps,
        )

    def close(self):
        self.stop.set()
        with self.condition:
            self.condition.notify_all()
        self.thread.join(timeout=2)
