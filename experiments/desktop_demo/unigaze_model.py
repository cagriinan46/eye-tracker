"""UniGaze process adapter: GUI environment never imports torch or loads weights."""

import os
import signal
import socket
import subprocess
import sys
import threading
import time

from experiments.unigaze.settings import PYTHON, ROOT, validate_assets
from experiments.unigaze.wire import receive, send


class CameraModel:
    def __init__(self, camera_index=None, stop_event=None):
        self.stop_event = stop_event if stop_event is not None else threading.Event()
        self.sock = self.worker = None
        self.preview_sock = None
        self.preview_thread = None
        self.preview_stop = threading.Event()
        self.preview_lock = threading.Lock()
        self.latest_preview = {}
        self.raw_point = None
        self.filter_history_ms = None
        if sys.platform != "darwin":
            raise RuntimeError(
                "UniGaze masaüstü bağlantısı şu an macOS için hazır. MGaze için --model mgaze kullan."
            )
        validate_assets()
        if camera_index is None:
            from live_svr_demo import macbook_camera_index

            camera_index = macbook_camera_index()
        try:
            self.sock, child = socket.socketpair()
            self.preview_sock, preview_child = socket.socketpair()
            self.preview_sock.settimeout(2)
            self.sock.settimeout(120)
            try:
                self.worker = subprocess.Popen(
                    [
                        str(PYTHON),
                        "-m",
                        "experiments.unigaze.desktop_worker",
                        str(child.fileno()),
                        str(camera_index),
                        str(preview_child.fileno()),
                    ],
                    pass_fds=(child.fileno(), preview_child.fileno()),
                    start_new_session=True,
                    cwd=ROOT,
                    env=dict(
                        os.environ,
                        PYTHONPATH=str(ROOT / "src") + os.pathsep + str(ROOT),
                        PYTHONDONTWRITEBYTECODE="1",
                        HF_HUB_OFFLINE="1",
                    ),
                    stdout=subprocess.DEVNULL,
                )
            finally:
                child.close()
                preview_child.close()
            ready, _ = receive(self.sock, cancelled=self.stop_event.is_set, timeout=120)
            if ready.get("status") != "ready":
                raise RuntimeError(ready.get("error", "UniGaze başlatılamadı"))
            self._metadata = ready["metadata"]
            self.sock.settimeout(30)
            self.preview_thread = threading.Thread(
                target=self._preview_loop, daemon=True, name="camera-preview"
            )
            self.preview_thread.start()
        except BaseException:
            self.close()
            raise

    def _preview_loop(self):
        try:
            while not self.preview_stop.is_set():
                started = time.monotonic()
                send(self.preview_sock, {"command": "preview"})
                value, _ = receive(self.preview_sock, cancelled=self.preview_stop.is_set, timeout=2)
                with self.preview_lock:
                    self.latest_preview = value
                self.preview_stop.wait(max(0, 1 / 60 - (time.monotonic() - started)))
        except (OSError, EOFError, ValueError):
            with self.preview_lock:
                self.latest_preview = {}

    def preview_snapshot(self):
        with self.preview_lock:
            value = dict(self.latest_preview)
        if time.monotonic() - value.get("preview_captured", 0) > 0.5:
            value.update(preview=None, eye_preview=None)
        return value

    def _request(self, command, **data):
        if self.sock is None:
            raise RuntimeError("UniGaze bağlantısı kapalı")
        send(self.sock, dict(command=command, **data))
        result, _ = receive(self.sock, cancelled=self.stop_event.is_set, timeout=30)
        if result.get("status") != "ok":
            raise RuntimeError(result.get("error", "UniGaze işlem hatası"))
        return result

    def read(self, preview=False):
        r = self._request("read", preview=bool(preview))
        self.raw_point = r["raw_point"]
        self.filter_history_ms = r["filter_history_ms"]
        return r["captured"], r["features"], r["point"], r["preview"]

    def fit(self, features, labels):
        return self._request("fit", features=features.tolist(), labels=labels.tolist())["error"]

    def reset_filter(self):
        self._request("reset")
        self.raw_point = None
        self.filter_history_ms = None

    def metadata(self):
        return dict(self._metadata)

    def close(self):
        self.preview_stop.set()
        if self.preview_sock is not None:
            try:
                self.preview_sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.preview_sock.close()
        if self.preview_thread is not None:
            self.preview_thread.join(timeout=1)
        self.preview_sock = None
        if self.sock is not None:
            try:
                self.sock.settimeout(0.2)
                send(self.sock, {"command": "close"})
            except OSError:
                pass
            self.sock.close()
            self.sock = None
        if self.worker is not None:
            try:
                self.worker.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            # This process owns a new session; terminate its entire worker group,
            # including a blocked baseline child, even if the parent already exited.
            try:
                os.killpg(self.worker.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.worker.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(self.worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.worker.wait(timeout=2)
            self.worker = None
