"""Serialized desktop bridge with a single owner for camera/model resources."""

import hashlib
import json
import threading
import time
from pathlib import Path
from uuid import uuid4

from . import preferences
from .protocol import Session

ROOT = Path(__file__).resolve().parents[2]


class DesktopAPI:
    def __init__(self, output=None, camera_index=None, model_name="unigaze", preferences_path=None):
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._worker = None
        self._session = Session(model_name=model_name, scenario="web")
        self._model_name = model_name
        self._reset_filter = False
        self._last_raw_point = None
        self._filter_history_ms = None
        self._camera = "off"
        self._preview = None
        self._active_model = None
        self._pointer_captured = 0
        self._pointer_pause = threading.Event()
        self._tracking = False
        self._signal_status = "waiting"
        self._signal_counts = {}
        self._eligibility_counts = {}
        self._last_ui = time.monotonic()
        self._focused = True
        self._output = Path(output) if output is not None else ROOT / "validation/results"
        self._folder = None
        self._meta = {}
        self._camera_index = camera_index
        self._closed = False
        self._last_saved_trials = 0
        self._last_saved_token = None
        self._preferences_path = (
            Path(preferences_path) if preferences_path is not None else preferences.DEFAULT_PATH
        )
        self._preferences = preferences.load(self._preferences_path)

    def request_pointer_pause(self):
        self._pointer_pause.set()

    def pointer_sample(self):
        if not self._lock.acquire(blocking=False):
            return None
        try:
            s = self._session
            if (
                self._closed
                or self._pointer_pause.is_set()
                or self._stop.is_set()
                or self._camera != "ready"
                or not self._focused
                or not self._tracking
                or s.phase != "demo"
                or s.paused_at is not None
                or time.monotonic() - self._last_ui > 0.8
                or time.monotonic() - self._pointer_captured > 0.3
            ):
                return None
            return s.last_point
        finally:
            self._lock.release()

    def snapshot(self):
        with self._lock:
            self._last_ui = time.monotonic()
            if self._pointer_pause.is_set():
                self._session.pause(self._last_ui)
                self._reset_filter = True
                self._pointer_pause.clear()
            state = self._session.snapshot()
            state.update(
                camera=self._camera,
                model_name=self._model_name,
                preview=self._preview,
                tracking=self._tracking,
                signal_status=self._signal_status,
                record_path=str(self._folder) if self._folder else None,
                preferences=dict(self._preferences),
            )
            if self._camera == "ready" and self._active_model is not None:
                preview_snapshot = getattr(self._active_model, "preview_snapshot", None)
                if preview_snapshot is not None:
                    state.update(preview_snapshot())
            state["measurement"] = self._session.measurement_progress(time.monotonic())
            return state

    def command(self, action, payload=None):
        payload = payload or {}
        try:
            with self._lock:
                if self._closed:
                    raise ValueError("Uygulama kapalı.")
                now = time.monotonic()
                s = self._session
                if action == "preferences":
                    if not isinstance(payload, dict):
                        raise ValueError("Geçersiz görünüm ayarı.")
                    values = preferences.validated(self._preferences | payload)
                    try:
                        self._preferences = preferences.save(self._preferences_path, values)
                    except OSError:
                        return {
                            "ok": False,
                            "message": "Görünüm kaydedilemedi. Önceki ayar korundu.",
                        }
                elif action == "camera":
                    if self._worker is not None and self._worker.is_alive():
                        raise ValueError("Kamera zaten çalışıyor.")
                    self._stop.clear()
                    self._camera = "loading"
                    s.calibrated = False
                    s.geometry = None
                    s.transition("preparation")
                    s.message = ""
                    self._worker = threading.Thread(
                        target=self._run, name="gaze-camera", daemon=True
                    )
                    self._worker.start()
                elif action == "stop_camera":
                    try:
                        self._save("completed" if len(s.trials) == 12 else "aborted")
                    finally:
                        self._stop.set()
                        self._camera = (
                            "stopping" if self._worker and self._worker.is_alive() else "off"
                        )
                        self._preview = None
                        self._tracking = False
                        s.calibrated = False
                        s.geometry = None
                        s.message = ""
                        s.transition("preparation")
                elif action == "home":
                    self._save(
                        "completed" if s.phase == "results" or len(s.trials) == 12 else "aborted"
                    )
                    s.message = ""
                    s.paused_at = None
                    s.transition("preparation")
                elif action == "calibrate":
                    if self._camera != "ready" or not self._focused:
                        raise ValueError("Önce kamerayı başlat ve uygulama penceresine dön.")
                    self._save("aborted" if s.phase != "results" else "completed")
                    self._folder = None
                    s.start_calibration(payload["geometry"])
                    self._signal_counts = {}
                    self._eligibility_counts = {}
                    self._meta.pop("training_fit_normalized", None)
                    self._last_raw_point = self._filter_history_ms = None
                    self._reset_filter = True
                    self._begin_record()
                elif action == "retry_calibration":
                    if self._camera != "ready" or not self._focused:
                        raise ValueError("Önce uygulama penceresine dön.")
                    s.retry_calibration()
                    self._reset_filter = True
                elif action == "ack":
                    s.ack(payload["token"], now)
                elif action == "regions":
                    s.set_regions(payload["regions"])
                elif action == "geometry":
                    s.geometry_changed(payload["geometry"])
                elif action == "demo":
                    if not self._focused:
                        raise ValueError("Önce uygulama penceresine dön.")
                    retry = s.phase == "results" or bool(s.trials)
                    if retry:
                        self._save(
                            "completed"
                            if s.phase == "results" or len(s.trials) == 12
                            else "aborted"
                        )
                        self._folder = None
                    s.start_demo()
                    if retry:
                        self._begin_record()
                elif action == "pause":
                    s.pause(now)
                    self._reset_filter = True
                elif action == "resume":
                    if self._focused:
                        s.resume(now)
                        self._reset_filter = True
                elif action == "focus":
                    self._focused = bool(payload["active"])
                    if not self._focused:
                        s.pause(now)
                        self._reset_filter = True
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
            phase=s.phase,
            message=s.message,
            calibration_index=s.index,
            completed_calibration_points=len(s.training),
            current_samples=len(s.samples),
            signal_counts=dict(self._signal_counts),
            eligibility_counts=dict(self._eligibility_counts),
            modality="gaze",
            camera_images_saved=False,
            os_control=True,
            os_actions=["move_pointer_in_focused_demo"],
            os_clicks=False,
            geometry=s.geometry,
            checks=s.check_results,
            trials=s.trials,
            completed_trials=len(s.trials),
            planned_trials=12,
            dwell_seconds=1.2,
            dwell_max_interruption_seconds=s.dwell.max_interruption,
            trial_timeout_seconds=15,
            model=self._meta,
            protocol=("fresh13x20-window6s" if self._model_name == "unigaze" else "fresh13x45")
            + ";5point-independent-check;12-web-control-trials-v2",
            selected_model=self._model_name,
            scenario=self._session.scenario,
            appearance=dict(self._preferences),
            latest_raw_point=self._last_raw_point,
            latest_filter_history_ms=self._filter_history_ms,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in list(Path(__file__).parent.glob("*.py"))
                + list((ROOT / "experiments/unigaze").glob("*.py"))
                + list((ROOT / "experiments/unigaze").glob("*.json"))
            },
            limitation="Single-user prototype. Calibration fit is not selection accuracy.",
        )
        temp = self._folder / "session.tmp"
        temp.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
        temp.replace(self._folder / "session.json")

    def _run(self):
        model = None
        try:
            if self._model_name == "unigaze":
                from .unigaze_model import CameraModel
            else:
                from .model import CameraModel

            model = (
                CameraModel(self._camera_index, stop_event=self._stop)
                if self._model_name == "unigaze"
                else CameraModel(self._camera_index)
            )
            with self._lock:
                if self._stop.is_set():
                    return
                self._active_model = model
                self._meta = model.metadata()
                self._camera = "ready"
            while not self._stop.is_set():
                with self._lock:
                    token = self._session.token
                    reset_filter = self._reset_filter
                    self._reset_filter = False
                    preview = self._session.phase in ("preparation", "error", "ready", "results")
                if reset_filter and hasattr(model, "reset_filter"):
                    model.reset_filter()
                captured, features, point, jpeg = model.read(preview=preview)
                raw_point = getattr(model, "raw_point", point)
                now = time.monotonic()
                with self._lock:
                    if self._stop.is_set():
                        break
                    s = self._session
                    self._tracking = features is not None and 0 <= now - captured <= 0.3
                    self._signal_status = (
                        "tracking"
                        if self._tracking
                        else "processing_delayed"
                        if features is not None
                        else "no_gaze"
                    )
                    self._signal_counts[self._signal_status] = (
                        self._signal_counts.get(self._signal_status, 0) + 1
                    )
                    reason = getattr(model, "eligibility_reason", "unknown")
                    self._eligibility_counts[reason] = self._eligibility_counts.get(reason, 0) + 1
                    if jpeg is not None:
                        self._preview = jpeg
                    if now - self._last_ui > 0.8 or not self._focused:
                        s.pause(now)
                        self._reset_filter = True
                    if token != s.token or self._reset_filter:
                        continue
                    if not self._tracking:
                        # Calibration is indexed by capture time, as in the research runner.
                        # Late features must never move the live pointer or accrue dwell.
                        if s.phase not in ("calibration", "check"):
                            features = None
                        if s.phase != "check":
                            point = raw_point = None
                        if features is None or s.phase != "check":
                            self._reset_filter = True
                    self._last_raw_point = raw_point
                    self._filter_history_ms = getattr(model, "filter_history_ms", None)
                    s.sample(captured, features, point, raw_point=raw_point)
                    self._pointer_captured = captured
                    if s.phase == "fitting":
                        x, y = s.calibration_arrays()
                        self._meta["training_fit_normalized"] = model.fit(x, y)
                        s.fitted()
                        self._save("in_progress")
                    if len(s.trials) != self._last_saved_trials or (
                        s.phase in ("error", "calibration_retry")
                        and s.token != self._last_saved_token
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
            if self._stop.is_set():
                return
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
                self._active_model = None
                self._preview = None
                if self._camera != "error":
                    self._camera = "off"

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                self._stop.set()
                try:
                    self._save("completed" if self._session.phase == "results" else "aborted")
                except OSError:
                    pass
        # Every caller waits, including the main-thread finalizer after a native
        # closing event. Otherwise Python can shut down MediaPipe's executor early.
        if self._worker is not None and self._worker is not threading.current_thread():
            self._worker.join(timeout=10)
