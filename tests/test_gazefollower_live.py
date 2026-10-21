"""Synthetic live telemetry tests: no camera, native pointer or participant data."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.gazefollower_baseline import run


def trace_type():
    from experiments.gazefollower_baseline.live_trace import LiveTrace

    return LiveTrace


def test_pointer_returns_only_successfully_sent_coordinates():
    moves = []
    backend = SimpleNamespace(
        screen_size=(100, 80),
        check_stop=lambda: None,
        move=lambda x, y: moves.append([x, y]),
    )
    pointer = run.MoveOnlyPointer(backend, (100, 80))
    assert pointer.update([99.9, 79.9]) == {"command_px": [99, 79], "movement_status": "sent"}
    assert moves == [[99, 79]]
    assert pointer.update([-1, 3]) == {"command_px": None, "movement_status": "offscreen"}
    assert pointer.update([np.nan, 3]) == {
        "command_px": None,
        "movement_status": "invalid_prediction",
    }
    assert len(moves) == 1


def test_trace_flushes_periodically_and_preserves_existing_files(tmp_path):
    clock = [10.0]
    with trace_type()(tmp_path, {"selection": "original"}, clock=lambda: clock[0]) as trace:
        trace.record({"frame": 1})
        assert (tmp_path / "live.jsonl").read_bytes() == b""
        clock[0] = 11.1
        trace.record({"frame": 2})
        assert len((tmp_path / "live.jsonl").read_text().splitlines()) == 2
        trace.record({"frame": 3})
    assert [json.loads(s)["frame"] for s in (tmp_path / "live.jsonl").read_text().splitlines()] == [
        1,
        2,
        3,
    ]
    summary = json.loads((tmp_path / "live-trace-summary.json").read_text())
    assert summary["status"] == "closed"
    assert summary["rows"] == 3
    before = (tmp_path / "live.jsonl").read_bytes()
    with pytest.raises(FileExistsError):
        trace_type()(tmp_path, {"selection": "candidate"})
    assert (tmp_path / "live.jsonl").read_bytes() == before


def test_trace_cap_preserves_prefix_and_warns_once(tmp_path, capsys):
    with trace_type()(tmp_path, {}, max_bytes=25) as trace:
        for n in range(10):
            trace.record({"frame": n})
    rows = (tmp_path / "live.jsonl").read_text().splitlines()
    assert rows and len(rows) < 10
    assert (tmp_path / "live.jsonl").stat().st_size <= 25
    summary = json.loads((tmp_path / "live-trace-summary.json").read_text())
    assert summary["status"] == "size_limit"
    assert summary["rows"] + summary["skipped_rows"] == 10
    assert capsys.readouterr().err.count("size limit") == 1


@pytest.mark.parametrize("operation", ["write", "flush", "close"])
def test_trace_io_failure_is_visible_and_not_success(tmp_path, monkeypatch, operation, capsys):
    trace = trace_type()(tmp_path, {}, flush_seconds=0)

    def fail(*args):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(trace.stream, operation, fail)
    with pytest.raises(OSError, match="synthetic disk failure"):
        with trace:
            trace.record({"frame": 1})
    summary = json.loads((tmp_path / "live-trace-summary.json").read_text())
    assert summary["status"] == "failed"
    assert summary["live_exit"] == "error"
    assert summary["error_type"] == "OSError"
    assert "Live trace" in capsys.readouterr().err
    # Restore close so the real temporary file can be released.
    monkeypatch.undo()
    trace.stream.close()


def live_fixture(tmp_path, monkeypatch, *, enabled=True, selection="original", move_error=None):
    moves, drawn = [], []
    state = {"frame": 0, "stops": 0}
    face = SimpleNamespace(
        status=True,
        can_gaze_estimation=True,
        face_landmarks=np.zeros((478, 3)),
        left_eye_openness=11,
        right_eye_openness=11,
    )
    gaze = SimpleNamespace(status=True, features=np.ones(258), raw_gaze_coordinates=None)
    points = [[99.9, 79.9], [150.0, 30.0], None, [20.0, 30.0]]

    class Filter:
        def filter_values(self, point):
            return point

    def observe():
        index = state["frame"]
        state["frame"] += 1
        face.status = points[index] is not None
        return None, face, gaze, 2.5, 100.0 + index

    def predict(*args):
        return True, points[state["frame"] - 1]

    def events(pg, on_desktop=None, **kwargs):
        if state["frame"] == 4:
            raise InterruptedError("Escape")
        if state["frame"] == 1 and on_desktop:
            on_desktop()
        return False

    def move(x, y):
        if move_error:
            raise move_error
        moves.append([x, y])

    def check_stop():
        state["stops"] += 1

    backend = SimpleNamespace(screen_size=(100, 80), check_stop=check_stop, move=move)
    monkeypatch.setattr(run, "enter_pressed", events)
    return (
        dict(
            pg=SimpleNamespace(display=SimpleNamespace(iconify=lambda: True)),
            folder=tmp_path,
            calibration=SimpleNamespace(predict=predict),
            controller=SimpleNamespace(convert_to_pixel=lambda point: point),
            filter_type=Filter,
            threshold=10,
            observe=observe,
            draw=lambda *args: drawn.append(args),
            targets=[(0.25, 0.25)],
            pointer=run.MoveOnlyPointer(backend, (100, 80)) if enabled else None,
            pointer_backend=backend if enabled else None,
            model_info={"selection": selection, "weights_sha256": "synthetic"},
        ),
        moves,
        drawn,
        state,
    )


@pytest.mark.parametrize("selection", ["original", "candidate"])
def test_live_records_same_frame_pipeline_desktop_and_loss(tmp_path, monkeypatch, selection):
    args, moves, drawn, state = live_fixture(tmp_path, monkeypatch, selection=selection)
    with pytest.raises(InterruptedError):
        run.live_view(**args)
    rows = [json.loads(line) for line in (tmp_path / "live.jsonl").read_text().splitlines()]
    assert len(rows) == 4
    assert moves == [[99, 79], [20, 30]]
    assert rows[0]["raw_px"] == rows[0]["filtered_px"] == [99.9, 79.9]
    assert rows[0]["command_px"] == [99, 79]
    assert rows[0]["mode"] == "yellow_blue"
    assert rows[1]["mode"] == "desktop"
    assert rows[1]["raw_px"] == [150, 30]
    assert rows[1]["movement_status"] == "offscreen"
    assert rows[2]["validity"] == "ineligible"
    assert rows[2]["raw_px"] is rows[2]["filtered_px"] is rows[2]["command_px"] is None
    assert rows[3]["validity"] == "valid"
    assert all(r["active_model"] == selection for r in rows)
    assert [r["captured_monotonic_s"] for r in rows] == [100, 101, 102, 103]
    assert len(drawn) == 1
    assert state["stops"] >= 4


def test_visual_only_records_without_os_commands(tmp_path, monkeypatch):
    args, moves, _, _ = live_fixture(tmp_path, monkeypatch, enabled=False)
    with pytest.raises(InterruptedError):
        run.live_view(**args)
    rows = [json.loads(line) for line in (tmp_path / "live.jsonl").read_text().splitlines()]
    assert not moves
    assert all(r["command_px"] is None and r["movement_status"] == "disabled" for r in rows)


@pytest.mark.parametrize(
    "error,status",
    [
        (OSError("move failed"), "backend_error"),
        (InterruptedError("Escape in move"), "interrupted"),
    ],
)
def test_failed_move_is_not_logged_as_sent(tmp_path, monkeypatch, error, status):
    args, moves, _, _ = live_fixture(tmp_path, monkeypatch, move_error=error)
    with pytest.raises(type(error)):
        run.live_view(**args)
    rows = [json.loads(line) for line in (tmp_path / "live.jsonl").read_text().splitlines()]
    assert not moves
    assert len(rows) == 1
    assert rows[0]["movement_status"] == status
    assert rows[0]["command_px"] is None
    assert rows[0]["movement_error"] == type(error).__name__


def test_filter_output_and_invalid_predictions_are_recorded_separately(tmp_path, monkeypatch):
    args, moves, _, _ = live_fixture(tmp_path, monkeypatch)
    predictions = iter([(True, [80, 60]), (False, None), (True, [np.nan, 10])])
    args["calibration"].predict = lambda *unused: next(predictions)
    args["filter_type"] = lambda: SimpleNamespace(filter_values=lambda point: [40, 30])
    with pytest.raises(InterruptedError):
        run.live_view(**args)
    rows = [json.loads(line) for line in (tmp_path / "live.jsonl").read_text().splitlines()]
    assert rows[0]["raw_px"] == [80, 60]
    assert rows[0]["filtered_px"] == rows[0]["command_px"] == [40, 30]
    assert moves == [[40, 30]]
    for i in [1, 3]:
        assert rows[i]["validity"] == "prediction_invalid"
        assert rows[i]["raw_px"] is rows[i]["filtered_px"] is None


def test_live_stops_on_log_failure_before_another_move(tmp_path, monkeypatch, capsys):
    args, moves, _, _ = live_fixture(tmp_path, monkeypatch)
    original = trace_type().record

    def record_with_broken_stream(self, row):
        self.stream.close()
        return original(self, row)

    monkeypatch.setattr(trace_type(), "record", record_with_broken_stream)
    with pytest.raises(ValueError, match="closed"):
        run.live_view(**args)
    assert moves == [[99, 79]]
    assert "stopping live mode" in capsys.readouterr().err
    summary = json.loads((tmp_path / "live-trace-summary.json").read_text())
    assert summary["status"] == "failed"
    assert summary["live_exit"] == "error"


def test_semantic_preview_tab_and_tracking_loss_without_pointer(tmp_path, monkeypatch):
    args, moves, drawn, state = live_fixture(tmp_path, monkeypatch, enabled=False)
    events = []
    preview = SimpleNamespace(
        activate=lambda: events.append("activate"),
        check_stop=lambda: None,
        update=lambda point, captured_at, desktop: (
            events.append((point, desktop)) or {"semantic_status": "synthetic"}
        ),
        close=lambda: events.append("close"),
    )
    with pytest.raises(InterruptedError):
        run.live_view(**args, preview=preview)
    assert moves == []
    assert "activate" in events
    assert (None, True) in events
    assert events[-1] == "close"
    assert len(drawn) == 1


def test_semantic_preview_rejects_pointer_mode_before_any_frame(tmp_path, monkeypatch):
    args, moves, drawn, state = live_fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="pointer"):
        run.live_view(**args, preview=object())
    assert state["frame"] == 0 and moves == []


def test_cli_rejects_preview_and_pointer_together(monkeypatch):
    monkeypatch.setattr(run.sys, "argv", ["run", "--semantic-preview", "--control-pointer"])
    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 2


def test_cli_rejects_preview_on_windows_before_loading_models(monkeypatch):
    monkeypatch.setattr(run.sys, "argv", ["run", "--semantic-preview"])
    monkeypatch.setattr(run.sys, "platform", "win32")
    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 2
