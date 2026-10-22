import json
from types import SimpleNamespace

import numpy as np
import pytest


def sample(valid=True):
    from experiments.gazefollower_baseline.diagnostics import diagnostic_row

    face = SimpleNamespace(
        face_rect=[0, 0, 4, 4],
        left_rect=[0, 0, 2, 2],
        right_rect=[2, 0, 2, 2],
        left_eye_openness=12,
        right_eye_openness=13,
    )
    gaze = SimpleNamespace(features=np.arange(258, dtype=float))
    return diagnostic_row(
        np.full((4, 4, 3), 100, dtype=np.uint8),
        face,
        gaze,
        usable=valid,
        captured_at=3.5,
        phase="evaluation",
        trial=2,
    )


def test_usable_sample_retains_replay_features_and_scalar_image_proxies():
    row = sample()
    assert row["features"] == list(range(258))
    assert (row["captured_monotonic_s"], row["phase"], row["trial"]) == (3.5, "evaluation", 2)
    assert row["eyes"]["left"]["mean_rgb_intensity"] == 100
    assert row["eyes"]["left"]["gradient_rms"] == 0
    assert row["eyes"]["left"]["bright_fraction"] == 0
    assert row["eyes"]["left"]["crop_size"] == [2, 2]
    assert "image" not in row and "landmarks" not in row
    json.dumps(row, allow_nan=False)


def test_rejected_sample_is_retained_without_features():
    row = sample(False)
    assert row["usable"] is False and row["features"] is None
    assert row["trial"] == 2


def test_bad_geometry_and_nonfinite_metadata_do_not_fabricate_quality():
    from experiments.gazefollower_baseline.diagnostics import diagnostic_row

    face = SimpleNamespace(
        left_rect=[0, 0, -1, 2], right_rect=[float("nan")] * 4, left_eye_openness=float("nan")
    )
    row = diagnostic_row(
        np.zeros((4, 4, 3), dtype=np.uint8),
        face,
        SimpleNamespace(features=None),
        usable=False,
        captured_at=1,
        phase="calibration",
        trial=None,
    )
    assert row["eyes"] == {"left": None, "right": None}
    assert row["eye_openness"] == [None, None]
    assert row["face_rect"] is None
    json.dumps(row, allow_nan=False)


def test_diagnostic_writer_is_exclusive_bounded_and_closable(tmp_path):
    from experiments.gazefollower_baseline.diagnostics import DiagnosticRecorder

    path = tmp_path / "frames.jsonl"
    writer = DiagnosticRecorder(path, max_rows=1)
    writer.write(sample())
    with pytest.raises(RuntimeError, match="limit"):
        writer.write(sample())
    writer.close()
    writer.close()
    assert len(path.read_text().splitlines()) == 1
    with pytest.raises(FileExistsError):
        DiagnosticRecorder(path)
