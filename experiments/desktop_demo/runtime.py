"""Serialized desktop bridge with a single owner for camera/model resources."""

import hashlib
import json
import threading
import time
from pathlib import Path
from uuid import uuid4

from .protocol import Session

ROOT = Path(__file__).resolve().parents[2]


class DesktopAPI:
    def __init__(self, output=None, camera_index=None):
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._worker = None
        self._session = Session()
        self._camera = "off"
        self._preview = None
        self._tracking = False
        self._last_ui = time.monotonic()
        self._focused = True
        self._output = Path(output) if output is not None else ROOT / "validation/results"
        self._folder = None
        self._meta = {}
        self._camera_index = camera_index
        self._closed = False
        self._last_saved_trials = 0
        self._last_saved_token = None

    def snapshot(self):
        with self._lock:
            self._last_ui = time.monotonic()
            state = self._session.snapshot()
            state.update(
                camera=self._camera,
                preview=self._preview,
                tracking=self._tracking,
                record_path=str(self._folder) if self._folder else None,
            )
            return state

    def command(self, action, payload=None):
        payload = payload or {}
        try:
            with self._lock:
                if self._closed:
                    raise ValueError("Uygulama kapalı.")
                now = time.monotonic()
                s = self._session
                if action == "camera":
                    if self._worker is not None and self._worker.is_alive():
                        raise ValueError("Kamera zaten çalışıyor.")
                    self._camera = "loading"
                    s.transition("preparation")
                    s.message = ""
                    self._worker = threading.Thread(
                        target=self._run, name="gaze-camera", daemon=True
                    )
                    self._worker.start()
                elif action == "calibrate":
                    if self._camera != "ready" or not self._focused:
                        raise ValueError("Önce kamerayı başlat ve uygulama penceresine dön.")
                    self._save("aborted" if s.phase != "results" else "completed")
                    self._folder = None
                    s.start_calibration(payload["geometry"])
                    self._begin_record()
                elif action == "ack":
                    s.ack(payload["token"], now)
                elif action == "regions":
                    s.set_regions(payload["regions"])
                elif action == "geometry":
                    s.geometry_changed(payload["geometry"])
                elif action == "demo":
                    if not self._focused:
                        raise ValueError("Önce uygulama penceresine dön.")
                    retry = s.phase == "results"
                    if retry:
                        self._save("completed")
                        self._folder = None
                    s.start_demo()
                    if retry:
                        self._begin_record()
                elif action == "pause":
                    s.pause(now)
                elif action == "resume":
                    if self._focused:
                        s.resume(now)
                elif action == "focus":
                    self._focused = bool(payload["active"])
                    if not self._focused:
                        s.pause(now)
                else:
                    raise ValueError("Bilinmeyen komut.")
                return {"ok": True}
        except OSError as error:
            with self._lock:
                self._session.fail("Oturum kaydı yazılamadı. Kayıt klasörünü kontrol et.")
            return {"ok": False, "message": self._session.message + " " + str(error)}
        except (ValueError, KeyError, TypeError) as error:
            return {"ok": False, "message": str(error)}

    def _begin_record(self):
        self._output.mkdir(parents=True, exist_ok=True)
        self._folder = self._output / ("desktop-gaze-" + uuid4().hex)
        self._folder.mkdir()
        self._last_saved_trials = 0
        self._last_saved_token = None
        self._save("in_progress")

    def _save(self, status):
        if self._folder is None:
            return
        s = self._session
        record = dict(
            status="completed" if len(s.trials) == 12 else status,
            modality="gaze",
            camera_images_saved=False,
            os_control=False,
            geometry=s.geometry,
            checks=s.check_results,
            trials=s.trials,
            completed_trials=len(s.trials),
            planned_trials=12,
            dwell_seconds=1.2,
            trial_timeout_seconds=15,
            model=self._meta,
            protocol="fresh13x45;5point-independent-check;12-four-target-trials",
            source_sha256={
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in Path(__file__).parent.glob("*.py")
            },
            limitation="Single-user prototype. Calibration fit is not selection accuracy.",
        )
        temp = self._folder / "session.tmp"
        temp.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
        temp.replace(self._folder / "session.json")

    def _run(self):
        model = None
        try:
            from .model import CameraModel

            model = CameraModel(self._camera_index)
            with self._lock:
                self._meta = model.metadata()
                self._camera = "ready"
            last_preview = 0.0
            while not self._stop.is_set():
                with self._lock:
                    token = self._session.token
                    preview = (
                        self._session.phase in ("preparation", "error", "ready", "results")
                        and time.monotonic() - last_preview > 0.2
                    )
                captured, features, point, jpeg = model.read(preview=preview)
                now = time.monotonic()
                with self._lock:
                    if self._closed:
                        break
                    s = self._session
                    self._tracking = features is not None and now - captured <= 0.3
                    if jpeg is not None:
                        self._preview = jpeg
                        last_preview = now
                    if now - self._last_ui > 0.8 or not self._focused:
                        s.pause(now)
                    if token != s.token:
                        continue
                    if not self._tracking:
                        features = point = None
                    s.sample(captured, features, point)
                    if s.phase == "fitting":
                        x, y = s.calibration_arrays()
                        self._meta["training_fit_normalized"] = model.fit(x, y)
                        s.fitted()
                        self._save("in_progress")
                    if len(s.trials) != self._last_saved_trials or (
                        s.phase == "error" and s.token != self._last_saved_token
                    ):
                        self._save(
                            "completed"
                            if s.phase == "results"
                            else "interrupted"
                            if s.phase == "error"
                            else "in_progress"
                        )
                        self._last_saved_trials = len(s.trials)
                        self._last_saved_token = s.token
                self._stop.wait(0.005)
        except Exception as error:
            with self._lock:
                self._camera = "error"
                self._tracking = False
                self._session.fail(str(error))
                try:
                    self._save("failed")
                except OSError:
                    pass
        finally:
            if model is not None:
                model.close()
            with self._lock:
                self._preview = None
                if self._camera != "error":
                    self._camera = "off"

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._stop.set()
            try:
                self._save("completed" if self._session.phase == "results" else "aborted")
            except OSError:
                pass
        if self._worker is not None:
            self._worker.join(timeout=3)
