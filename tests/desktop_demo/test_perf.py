import hashlib
import json
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.desktop_demo.perf import PerfRecorder, distribution
from experiments.desktop_demo.runtime import DesktopAPI


def recorder(tmp_path):
    cpu = iter(range(0, 1000))
    return PerfRecorder(tmp_path, "unigaze", clock=lambda: 0.0, cpu=lambda: next(cpu) * 0.1)


def test_distribution_uses_nearest_rank_and_ignores_missing():
    d = distribution([10, None, 30, 20, float("nan"), 40])
    assert d == dict(n=4, mean=25.0, median=20.0, p90=40.0, max=40.0)
    assert distribution([None]) is None


def test_demo_segment_reports_first_3s_and_next_15s_separately(tmp_path, capsys):
    r = recorder(tmp_path)
    r.set_model({"camera_index": 0, "provenance": {"device": "mps", "threads": 4}})
    r.phase("demo", 100.0)
    for i in range(24):  # 8/s, all fresh in the first 3 s
        t = 100.0 + i / 8
        r.frame(t, captured=t - 0.1, camera_sequence=3 * i, status="tracking", age_ms=100.0)
        r.pointer(t, "delivered", captured=t - 0.1)
    for i in range(30):  # 2/s and half late in the next 15 s
        t = 103.0 + i / 2
        r.frame(
            t,
            captured=t - 0.3,
            camera_sequence=100 + 12 * i,
            status="tracking" if i % 2 else "processing_delayed",
            age_ms=300.0,
            unigaze_ms=200.0,
        )
        r.pointer(t, "busy")
    r.frame(118.5, captured=118.4, status="tracking", age_ms=1.0)  # after both windows
    first, second = r.windows
    assert (first["window"], second["window"]) == ("first_3s", "next_15s")
    assert first["complete"] and second["complete"]
    assert first["frames"] == 24 and first["processed_fps"] == 8.0
    assert first["on_time_pct"] == 100.0 and second["on_time_pct"] == 50.0
    assert first["cursor"]["fresh_estimate_per_s"] == 8.0
    assert second["cursor"]["lock_busy_per_s"] == 2.0
    assert first["camera_fps"] == 24.0 and second["camera_fps"] == 24.0
    assert first["ms"]["age_ms"]["median"] == 100.0
    assert second["ms"]["unigaze_ms"]["p90"] == 200.0
    assert first["ms"]["interval_ms"]["median"] == 125.0
    saved = json.loads(r.path.read_text())
    assert saved["device"] == "mps" and saved["torch_threads"] == 4
    assert [s["window"] for s in saved["summaries"]] == ["first_3s", "next_15s"]
    assert r.path.stat().st_size < 20_000
    text = r.path.read_text()
    for forbidden in ('"point"', '"raw_point"', '"features"', '"preview"', "data:image"):
        assert forbidden not in text
    assert capsys.readouterr().err.count("[perf] #1 demo") == 2


def test_phase_change_closes_partial_window_and_starts_new_segment(tmp_path):
    r = recorder(tmp_path)
    r.phase("calibration", 10.0)
    r.frame(10.5, captured=10.4, status="tracking")
    r.phase("fitting", 11.0)
    r.frame(11.2, captured=11.1, status="tracking")  # outside a measured phase: ignored
    r.phase("check", 12.0)
    r.close(13.0)
    calibration, check = r.windows
    assert calibration["phase"] == "calibration" and not calibration["complete"]
    assert calibration["frames"] == 1 and calibration["end_s"] == 1.0
    assert check["segment"] == 2 and check["frames"] == 0
    r.close(14.0)
    assert len(r.windows) == 2


def test_no_file_without_a_measured_phase(tmp_path):
    r = recorder(tmp_path)
    r.phase("preparation", 1.0)
    r.close(2.0)
    assert not r.path.exists()


def test_diagnostics_are_off_by_default(tmp_path):
    api = DesktopAPI(model_name="mgaze", output=tmp_path)
    assert api._perf is None
    api.close()
    assert list(tmp_path.iterdir()) == []


def test_runtime_records_worker_timing_and_pointer_delivery(monkeypatch, tmp_path):
    seen = []

    class Model:
        def __init__(self, index, stop_event=None):
            self.stop, self.n = stop_event, 0
            self.collect_timing = False
            self.last_timing = None

        def metadata(self):
            return {"model": "fake", "provenance": {"device": "cpu", "threads": 4}}

        def read(self, preview=False):
            self.n += 1
            seen.append(self.collect_timing)
            if self.n >= 3:
                self.stop.set()
            self.last_timing = dict(wait_ms=1.0, worker_ms=5.0, unigaze_ms=3.0)
            return time.monotonic() - 0.05, [0.1, 0.2], [0.5, 0.5], None

        def close(self):
            pass

    monkeypatch.setitem(
        sys.modules, "experiments.desktop_demo.unigaze_model", SimpleNamespace(CameraModel=Model)
    )
    api = DesktopAPI(output=tmp_path, perf_diagnostics=True)
    api._session.phase = "ready"
    api._session.start_demo()
    api._perf_phase(time.monotonic())
    api._run()
    assert seen and all(seen)
    frames = api._perf._segment["window"]["frames"]
    assert len(frames) == 2  # the stopped third read is not processed
    assert frames[0]["status"] == "tracking" and frames[0]["unigaze_ms"] == 3.0
    assert frames[0]["transport_ms"] == pytest.approx(frames[0]["request_ms"] - 6.0)
    assert 40 <= frames[0]["age_ms"] < 300
    assert "gui_ms" in frames[0]
    api.close()
    summary = json.loads(api._perf.path.read_text())
    assert summary["model"] == "fake"
    assert summary["summaries"][0]["frames"] == 2


def test_contended_pointer_poll_is_counted_without_blocking(tmp_path):
    api = DesktopAPI(model_name="mgaze", output=tmp_path, perf_diagnostics=True)
    api._session.phase = "demo"
    api._perf_phase(time.monotonic())
    held = threading.Event()
    done = threading.Event()

    def hold():
        with api._lock:
            held.set()
            done.wait(2)

    thread = threading.Thread(target=hold)
    thread.start()
    assert held.wait(2)
    assert api.pointer_sample() is None
    done.set()
    thread.join(2)
    assert api.pointer_sample() is None
    counts = api._perf._segment["window"]["pointer"]
    assert counts["busy"] == 1 and counts["none"] == 1 and counts["fresh"] == 0
    api.close()


def test_engine_timing_reports_skipped_frames_and_stage_times(monkeypatch):
    from experiments.unigaze.desktop_worker import Engine

    e = Engine.__new__(Engine)
    e.last_capture = 4
    e.cpu_seconds = None
    e.stream = SimpleNamespace(
        enabled=True, read_after=lambda last: (7, time.monotonic_ns() - 20_000_000, "frame")
    )
    e.pair = SimpleNamespace(last_timing=dict(paired_ms=2.0, unigaze_ms=1.0))
    monkeypatch.setattr(e, "process_frame", lambda frame, captured, preview: {"status": "ok"})
    assert "timing" not in e.read()
    e.last_capture = 4
    t = e.read(timing=True)["timing"]
    assert t["camera_sequence"] == 7 and t["skipped_frames"] == 2
    assert t["start_age_ms"] >= 20 and t["worker_ms"] >= 0
    assert t["post_ms"] == pytest.approx(t["worker_ms"] - 2.0)
    assert t["unigaze_ms"] == 1.0 and t["worker_cpu_ms"] is None and t["worker_rss_mb"] > 0
    assert e.read(timing=True)["timing"]["worker_cpu_ms"] >= 0


def test_paired_timing_is_side_channel_and_rows_keep_their_keys(monkeypatch):
    import importlib

    # The real adapter imports torch; this test needs only the extractor's bookkeeping.
    monkeypatch.setitem(
        sys.modules, "experiments.unigaze.adapter", SimpleNamespace(Candidate=object)
    )
    monkeypatch.delitem(sys.modules, "experiments.unigaze.paired", raising=False)
    paired = importlib.import_module("experiments.unigaze.paired")

    frame = np.zeros((480, 640, 3), np.uint8)
    replies = []

    def send(sock, meta, payload=b""):
        replies.append(
            dict(
                status="ok",
                frame_id=meta["frame_id"],
                timestamp_ns=meta["timestamp_ns"],
                raw_sha256=hashlib.sha256(payload[: frame.nbytes]).hexdigest(),
                corrected_sha256=hashlib.sha256(payload[frame.nbytes :]).hexdigest(),
                mgaze_valid=True,
                mgaze_ms=4.0,
                landmarks_ms=3.0,
                diagnostics_ms=1.0,
                diagnostics={"mgaze_face_rect": None},
                landmarks=None,
                process_cpu_s=2.0 + len(replies),
            )
        )

    monkeypatch.setattr(paired, "send", send)
    monkeypatch.setattr(paired, "receive", lambda sock: (replies[-1], b""))

    class Candidate:
        def prepare(self, raw):
            return raw

        def infer(self, corrected, landmarks, rect):
            self.last_timing = dict(ug_detect_ms=0.5)
            return dict(unigaze_valid=False)

    p = paired.PairedExtractor.__new__(paired.PairedExtractor)
    p.sock, p.worker, p.last_id, p.last_timestamp = object(), None, -1, -1
    p.last_timing, p.vision_cpu, p.candidate = {}, None, Candidate()
    row = p.process(frame, 0, 10)
    assert "process_cpu_s" not in row and "vision_ms" not in row
    t = p.last_timing
    assert t["mgaze_ms"] == 4.0 and t["ug_detect_ms"] == 0.5 and t["vision_cpu_ms"] is None
    assert t["vision_overhead_ms"] == pytest.approx(t["vision_ms"] - 8.0)
    p.process(frame, 1, 11)
    assert p.last_timing["vision_cpu_ms"] == pytest.approx(1000.0)
    p.sock = None
