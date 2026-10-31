"""Single camera owner; bounded latest-frame handoff independent of gaze inference."""

import threading
import time


class LatestCamera:
    def __init__(self, cap, encode):
        self.cap, self.encode = cap, encode
        self.condition = threading.Condition()
        self.stop = threading.Event()
        self.latest = None
        self.image = None
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
                image = self.encode(frame) if self.enabled else None
                with self.condition:
                    self.latest = (sequence, captured, frame)
                    self.image = image
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
            sequence, stamp = self.latest[:2] if self.latest is not None else (-1, 0)
            fresh = (
                not self.error
                and not self.stop.is_set()
                and time.monotonic_ns() - stamp < 500_000_000
            )
            return dict(
                preview=self.image if fresh and self.enabled else None,
                preview_sequence=sequence,
                preview_captured=stamp / 1e9,
            )

    def close(self):
        self.stop.set()
        with self.condition:
            self.condition.notify_all()
        self.thread.join(timeout=2)
