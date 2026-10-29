import numpy as np
import pytest

from experiments.desktop_demo.protocol import Session


def test_unigaze_calibration_selects_twenty_per_target_after_full_window():
    s = Session(model_name="unigaze")
    s.start_calibration([1000, 800, 0, 0, 1])
    now = 0
    for _ in range(13):
        s.ack(s.token, now)
        s.sample(now + 1, [9, 9], None)
        s.sample(now + 1.55, np.ones(258), None)
        for j in range(24):
            s.sample(now + 1.6 + j * 0.24, [j, j + 1], None)
        assert s.phase == "calibration"
        s.sample(now + 7.6, None, None)
        now += 8
    assert s.phase == "fitting"
    x, y = s.calibration_arrays()
    assert x.shape == (260, 2) and y.shape == (260, 2)
    assert x[0].tolist() == [0, 1] and x[19].tolist() == [23, 24]
    assert y[0].tolist() == [0.5, 0.5]


def test_unigaze_insufficient_samples_fail_without_fitting():
    s = Session(model_name="unigaze")
    s.start_calibration([1000, 800, 0, 0, 1])
    s.ack(s.token, 0)
    s.sample(2, [1, 2], None)
    s.sample(7.6, None, None)
    assert s.phase == "error" and not s.calibrated


def test_check_keeps_raw_and_filtered_errors_separate():
    s = Session(model_name="unigaze")
    s.geometry = [1000, 800, 0, 0, 1]
    s.fitted()
    s.ack(s.token, 0)
    for t in np.linspace(1.1, 2.9, 10):
        s.sample(t, None, s.point, raw_point=[s.point[0] + 0.1, s.point[1]])
    s.sample(3.1, None, None)
    assert s.check_results[0]["mean_px"] == 0
    assert s.check_results[0]["raw_mean_px"] == pytest.approx(100)


def test_unknown_backend_rejected_without_camera():
    from experiments.desktop_demo.runtime import DesktopAPI

    with pytest.raises(ValueError):
        DesktopAPI(model_name="unknown")


def test_default_desktop_is_unigaze_and_starts_camera_off(tmp_path):
    from experiments.desktop_demo.runtime import DesktopAPI

    api = DesktopAPI(output=tmp_path)
    assert api.snapshot()["model_name"] == "unigaze"
    assert api.snapshot()["camera"] == "off"
    assert api._worker is None
    assert api._session.feature_count == 2
    api.close()


def test_gate_rejects_closed_eyes_and_invalid_angles():
    from experiments.unigaze.desktop_worker import eligible_features

    row = dict(
        mgaze_valid=True, unigaze_valid=True, unigaze_angles=[0.1, 0.2], eye_gap_ratios=[0.2, 0.2]
    )
    assert eligible_features(row) == [0.1, 0.2]
    for change in [
        dict(mgaze_valid=False),
        dict(unigaze_valid=False),
        dict(unigaze_angles=[np.nan, 0.2]),
        dict(eye_gap_ratios=[0.09, 0.2]),
        dict(eye_gap_ratios=[]),
    ]:
        assert eligible_features(dict(row, **change)) is None


def test_missing_assets_fail_without_starting_worker(monkeypatch, tmp_path):
    from experiments.desktop_demo import unigaze_model
    from experiments.unigaze import settings

    monkeypatch.setattr(unigaze_model.sys, "platform", "darwin")
    monkeypatch.setattr(settings, "PYTHON", tmp_path / "missing-python")
    called = []
    monkeypatch.setattr(unigaze_model.subprocess, "Popen", lambda *a, **k: called.append(True))
    with pytest.raises(RuntimeError, match="eksik"):
        unigaze_model.CameraModel(0)
    assert not called


def test_worker_error_propagates_without_silent_fallback(monkeypatch):
    from experiments.desktop_demo import unigaze_model

    model = unigaze_model.CameraModel.__new__(unigaze_model.CameraModel)
    model.sock = object()
    import threading

    model.stop_event = threading.Event()
    monkeypatch.setattr(unigaze_model, "send", lambda *a: None)
    monkeypatch.setattr(
        unigaze_model, "receive", lambda *a, **k: ({"status": "error", "error": "lost camera"}, b"")
    )
    with pytest.raises(RuntimeError, match="lost camera"):
        model.read()


def test_default_worker_uses_unigaze_and_releases_on_stop(monkeypatch, tmp_path):
    import sys
    import threading
    import time
    from types import SimpleNamespace

    from experiments.desktop_demo.runtime import DesktopAPI

    opened, released = threading.Event(), threading.Event()

    class Model:
        def __init__(self, index, stop_event=None):
            opened.set()

        def metadata(self):
            return {"model_id": "unigaze"}

        def read(self, preview=False):
            time.sleep(0.005)
            return time.monotonic(), [0, 0], None, None

        def close(self):
            released.set()

    monkeypatch.setitem(
        sys.modules, "experiments.desktop_demo.unigaze_model", SimpleNamespace(CameraModel=Model)
    )
    api = DesktopAPI(output=tmp_path)
    try:
        assert api.command("camera")["ok"]
        assert opened.wait(2)
        assert api.command("stop_camera")["ok"]
        api._worker.join(2)
        assert released.is_set() and not api._worker.is_alive()
        assert not api.snapshot()["can_demo"]
    finally:
        api.close()


def test_wire_rejects_oversize_and_disconnect():
    import socket
    import struct

    from experiments.unigaze.wire import receive

    a, b = socket.socketpair()
    try:
        b.sendall(struct.pack("!II", 1_000_001, 0))
        with pytest.raises(ValueError):
            receive(a)
        b.close()
        with pytest.raises(EOFError):
            receive(a)
    finally:
        a.close()
        b.close()


def test_socket_wait_is_cancellable_without_camera():
    import socket
    import threading

    from experiments.unigaze.wire import receive

    a, b = socket.socketpair()
    stop = threading.Event()
    stop.set()
    try:
        with pytest.raises(InterruptedError):
            receive(a, cancelled=stop.is_set, timeout=1)
    finally:
        a.close()
        b.close()


def test_resume_requests_fresh_filter_history(tmp_path):
    from experiments.desktop_demo.runtime import DesktopAPI

    api = DesktopAPI(output=tmp_path)
    api._session.phase = "ready"
    api._session.start_demo()
    api._session.ack(api._session.token, 0)
    api.command("pause")
    api._reset_filter = False  # Worker consumed initial reset and processed paused frames.
    api.command("resume")
    assert api._reset_filter
    api.close()


def test_cancelled_startup_reaps_worker_and_nested_child(monkeypatch, tmp_path):
    import os
    import subprocess
    import sys
    import threading

    from experiments.desktop_demo import unigaze_model

    monkeypatch.setattr(unigaze_model.sys, "platform", "darwin")
    monkeypatch.setattr(unigaze_model, "validate_assets", lambda: None)
    original = subprocess.Popen
    processes = []
    child_pid = tmp_path / "child-pid"
    code = (
        "import subprocess,sys,time; from pathlib import Path; "
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
        "Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)"
    )

    def stalled(args, **kwargs):
        p = original([sys.executable, "-c", code, str(child_pid)], **kwargs)
        processes.append(p)
        return p

    monkeypatch.setattr(unigaze_model.subprocess, "Popen", stalled)
    stop = threading.Event()
    timer = threading.Timer(0.5, stop.set)
    timer.start()
    try:
        with pytest.raises(InterruptedError):
            unigaze_model.CameraModel(1, stop_event=stop)
        assert processes[0].poll() is not None
        if child_pid.exists():
            check = original(
                ["ps", "-o", "stat=", "-p", child_pid.read_text()],
                stdout=subprocess.PIPE,
                text=True,
            )
            stat = check.communicate(timeout=2)[0].strip()
            assert not stat or stat.startswith("Z")
    finally:
        timer.cancel()
        if processes:
            try:
                os.killpg(processes[0].pid, 9)
            except ProcessLookupError:
                pass


def test_inflight_paused_frame_is_discarded_on_resume(monkeypatch, tmp_path):
    import sys
    import threading
    import time
    from types import SimpleNamespace

    from experiments.desktop_demo.runtime import DesktopAPI

    entered, release = threading.Event(), threading.Event()
    resets, samples = [], []

    class Model:
        def __init__(self, index, stop_event=None):
            self.stop = stop_event
            self.n = 0

        def metadata(self):
            return {}

        def reset_filter(self):
            resets.append(True)

        def read(self, preview=False):
            self.n += 1
            if self.n == 1:
                entered.set()
                assert release.wait(2)
            else:
                self.stop.set()
            return time.monotonic(), [0, 0], [0.2, 0.2], None

        def close(self):
            pass

    monkeypatch.setitem(
        sys.modules, "experiments.desktop_demo.unigaze_model", SimpleNamespace(CameraModel=Model)
    )
    api = DesktopAPI(output=tmp_path)
    monkeypatch.setattr(api._session, "sample", lambda *a, **k: samples.append(a))
    try:
        assert api.command("camera")["ok"]
        assert entered.wait(2)
        api._session.phase = "ready"
        api._session.start_demo()
        api.command("pause")
        api.command("resume")
        release.set()
        api._worker.join(2)
        assert not samples and resets
    finally:
        release.set()
        api.close()
