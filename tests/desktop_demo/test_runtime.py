import json

from experiments.desktop_demo.runtime import DesktopAPI


def test_window_starts_without_camera_or_model(tmp_path):
    api = DesktopAPI(output=tmp_path)
    s = api.snapshot()
    assert s["camera"] == "off" and s["phase"] == "preparation"
    assert api._worker is None
    assert list(tmp_path.iterdir()) == []
    api.close()


def test_commands_cannot_forge_gaze_results(tmp_path):
    api = DesktopAPI(output=tmp_path)
    assert not api.command("select", {"target": "circle"})["ok"]
    assert not api.command("demo", {})["ok"]
    assert not api.command("calibrate", {"geometry": [1000, 800, 0, 0, 1]})["ok"]
    assert not api.snapshot()["trials"]
    api.close()


def test_report_preserves_wrong_timeout_and_aborted_status(tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._begin_record()
    api._session.trials = [
        {"outcome": "incorrect", "modality": "gaze", "elapsed_s": 3},
        {"outcome": "timeout", "modality": "gaze", "elapsed_s": 15},
    ]
    api._save("aborted")
    report = json.loads((api._folder / "session.json").read_text())
    assert report["status"] == "aborted"
    assert len(report["trials"]) == 2
    assert report["camera_images_saved"] is False
    api.close()


def test_hidden_window_pauses_and_requires_explicit_resume(tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._session.phase = "ready"
    api._session.start_demo()
    api.command("focus", {"active": False})
    assert api.snapshot()["paused"]
    api.command("focus", {"active": True})
    assert api.snapshot()["paused"]
    api.close()


def test_retry_record_starts_empty(tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._session.phase = "results"
    api._session.trials = [{"outcome": "correct", "modality": "gaze", "elapsed_s": 3}]
    api._begin_record()
    old = api._folder
    assert api.command("demo")["ok"]
    assert api._folder != old
    assert json.loads((api._folder / "session.json").read_text())["trials"] == []
    assert len(json.loads((old / "session.json").read_text())["trials"]) == 1
    api.close()


def test_record_failure_stops_measurement_visibly(tmp_path):
    bad = tmp_path / "not-a-directory"
    bad.write_text("occupied")
    api = DesktopAPI(output=bad)
    api._camera = "ready"
    result = api.command("calibrate", {"geometry": [1000, 800, 0, 0, 1]})
    assert not result["ok"]
    assert api._session.phase == "error"
    assert "kay" in api._session.message.lower()
    api.close()


def test_retry_write_failure_does_not_rewrite_completed_record(tmp_path):
    api = DesktopAPI(output=tmp_path / "good")
    api._session.phase = "results"
    api._session.trials = [{"outcome": "correct", "modality": "gaze", "elapsed_s": 3}]
    api._begin_record()
    old = api._folder
    bad = tmp_path / "bad"
    bad.write_text("occupied")
    api._output = bad
    assert not api.command("demo")["ok"]
    api.close()
    saved = json.loads((old / "session.json").read_text())
    assert saved["status"] == "completed" and len(saved["trials"]) == 1


def test_native_move_callback_returns_no_bridge_payload(tmp_path):
    from experiments.desktop_demo.__main__ import pause_for_window_move

    api = DesktopAPI(output=tmp_path)
    api._session.phase = "ready"
    api._session.start_demo()
    assert pause_for_window_move(api, 10, 20) is None
    assert api._session.paused_at is not None
    api.close()


def test_finished_measurements_stay_completed_after_later_window_error(tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._session.phase = "results"
    api._session.trials = [
        {"outcome": "correct", "modality": "gaze", "elapsed_s": 3} for _ in range(12)
    ]
    api._begin_record()
    api._save("completed")
    api._session.fail("window moved after completion")
    api.close()
    assert json.loads((api._folder / "session.json").read_text())["status"] == "completed"


def test_stop_camera_clears_preview_and_can_return_home(tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._camera = "ready"
    api._preview = "private-image"
    assert api.command("stop_camera")["ok"]
    assert api.snapshot()["preview"] is None
    assert not api.snapshot()["tracking"]
    assert api._stop.is_set()
    api.close()


def test_home_preserves_calibration_but_requires_new_trial_on_return(tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._camera = "ready"
    api._session.phase = "ready"
    api._session.calibrated = True
    api._session.start_demo()
    api._begin_record()
    assert api.command("home")["ok"]
    assert api.snapshot()["phase"] == "preparation"
    assert api.snapshot()["can_demo"]
    assert api.command("demo")["ok"]
    assert not api._session.trials
    api.close()


def test_close_always_waits_for_worker_even_when_another_close_started(tmp_path):
    api = DesktopAPI(output=tmp_path)
    calls = []

    class Worker:
        def join(self, timeout):
            calls.append(timeout)

    api._worker = Worker()
    api._closed = True
    api.close()
    assert calls


def test_camera_worker_releases_before_restart(monkeypatch, tmp_path):
    import sys
    import threading
    import time
    from types import SimpleNamespace

    opened, released = threading.Event(), threading.Event()
    instances = []

    class Model:
        def __init__(self, index):
            instances.append(self)
            opened.set()

        def metadata(self):
            return {}

        def read(self, preview=False):
            time.sleep(0.005)
            return time.monotonic(), None, None, "memory-only-preview"

        def close(self):
            released.set()

    monkeypatch.setitem(
        sys.modules, "experiments.desktop_demo.model", SimpleNamespace(CameraModel=Model)
    )
    api = DesktopAPI(output=tmp_path)
    try:
        for _ in range(2):
            opened.clear()
            released.clear()
            assert api.command("camera")["ok"]
            assert opened.wait(2)
            assert api.command("stop_camera")["ok"]
            api._worker.join(2)
            assert released.is_set()
            assert not api._worker.is_alive()
            assert api.snapshot()["camera"] == "off"
            assert api.snapshot()["preview"] is None
        assert len(instances) == 2
    finally:
        api.close()


def test_camera_stop_survives_report_write_failure(monkeypatch, tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._camera = "ready"
    api._preview = "memory-only"
    api._session.calibrated = True

    def fail_save(status):
        raise OSError("disk full")

    monkeypatch.setattr(api, "_save", fail_save)
    assert not api.command("stop_camera")["ok"]
    assert api._stop.is_set()
    assert api._preview is None
    assert not api.snapshot()["can_demo"]
    api.close()


def test_camera_retry_requires_fresh_calibration(monkeypatch, tmp_path):
    import threading

    api = DesktopAPI(output=tmp_path)
    api._session.calibrated = True
    api._session.geometry = [1280, 772, 0, 0, 1]
    api._session.fail("camera disconnected")
    monkeypatch.setattr(threading.Thread, "start", lambda self: None)
    assert api.command("camera")["ok"]
    assert not api.snapshot()["can_demo"]
    assert api._session.geometry is None
    api._worker = None
    api.close()
