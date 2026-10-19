"""No webcam, model download, OS actions or historical participant data."""

import json
from types import SimpleNamespace

import numpy as np
import pytest


def api():
    from experiments.gazefollower_baseline import run

    return run


def test_rejects_blinks_tracking_loss_and_nonfinite_features():
    face = SimpleNamespace(
        status=True,
        can_gaze_estimation=True,
        left_eye_openness=11,
        right_eye_openness=11,
        face_landmarks=np.zeros((478, 3)),
    )
    gaze = SimpleNamespace(status=True, features=np.ones(258))
    assert api().eligible(face, gaze, 10)
    face.left_eye_openness = 10
    assert not api().eligible(face, gaze, 10)
    face.left_eye_openness = 11
    gaze.features[0] = np.nan
    assert not api().eligible(face, gaze, 10)
    gaze.features = None
    assert not api().eligible(face, gaze, 10)


def test_rejects_successful_blazeface_fallback_with_fabricated_openness():
    face = SimpleNamespace(
        status=True,
        can_gaze_estimation=True,
        left_eye_openness=100,
        right_eye_openness=100,
        face_landmarks=np.zeros((12, 2)),
    )
    gaze = SimpleNamespace(status=True, features=np.ones(258))
    assert not api().eligible(face, gaze, 10)


def test_report_preserves_offscreen_errors_and_counts_missing_attempts():
    rows = [
        dict(trial=1, target_px=[50, 50], raw_px=p, filtered_px=p)
        for p in ([50, 50], [150, 50], None)
    ]
    result = api().summarize(rows)
    trial = result["trials"][0]
    assert trial["raw"]["mean_error_px"] == 50
    assert trial["raw"]["within_30px_fraction"] == pytest.approx(1 / 3)
    assert trial["raw"]["availability"] == pytest.approx(2 / 3)
    assert trial["raw"]["bias_px"] == [50, 0]
    assert trial["raw"]["centered_rms_px"] == 50
    json.dumps(result, allow_nan=False)


def test_missing_trial_is_not_success():
    result = api().summarize([dict(trial=1, target_px=[50, 50], raw_px=None, filtered_px=None)])
    assert result["trials"][0]["raw"]["mean_error_px"] is None
    assert not result["sufficient_data"]


def test_existing_records_cannot_be_overwritten(tmp_path):
    path = tmp_path / "result.json"
    api().write_new(path, {"original": True})
    with pytest.raises(FileExistsError):
        api().write_new(path, {"original": False})
    assert json.loads(path.read_text()) == {"original": True}
    assert api().new_session(tmp_path) != api().new_session(tmp_path)


def test_camera_failure_stops_instead_of_using_dummy_frames():
    source = SimpleNamespace(read=lambda: (False, None))
    with pytest.raises(RuntimeError, match="Camera"):
        api().read_frame(source)


def test_enter_gate_requires_new_press_after_screen_is_presented():
    events = iter([[], [SimpleNamespace(type=1, key=13)]])
    calls = []
    pg = SimpleNamespace(
        QUIT=0,
        KEYDOWN=1,
        K_ESCAPE=27,
        K_RETURN=13,
        K_KP_ENTER=14,
        event=SimpleNamespace(clear=lambda: calls.append("clear"), get=lambda: next(events)),
        time=SimpleNamespace(wait=lambda _: None),
    )
    api().wait_enter(pg, lambda: calls.append("draw"))
    assert calls == ["draw", "clear"]
