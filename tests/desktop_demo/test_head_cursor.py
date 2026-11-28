"""Issue #160: head-cursor mode pieces without camera, MediaPipe or GUI."""

from types import SimpleNamespace

import numpy as np
import pytest

from experiments.desktop_demo.hold_key import R_KEY_CODE, RECENTRE_HOLD_SECONDS, HoldKey
from experiments.desktop_demo.protocol import UNIGAZE_POINTS, Session
from experiments.desktop_demo.runtime import DesktopAPI
from experiments.head_pointer import desktop
from experiments.unigaze.desktop_worker import ENGINES, EyeClosure, HeadEngine
from experiments.unigaze.mapping import Ridge


def _eye(cx, opening):
    # corner, upper outer, upper inner, corner, lower inner, lower outer (width 20)
    return [
        [cx - 10, 0],
        [cx - 4, -opening],
        [cx + 4, -opening],
        [cx + 10, 0],
        [cx + 4, opening],
        [cx - 4, opening],
    ]


def test_eye_opening_ratio_and_invalid_input() -> None:
    ratios = desktop.eye_opening([_eye(0, 3), _eye(50, 1)])
    assert ratios == pytest.approx([0.3, 0.1])
    assert desktop.eye_opening([_eye(0, 3)]) is None
    assert desktop.eye_opening([[[np.nan, 0]] * 6] * 2) is None


def test_filter_constant_is_the_158_outcome() -> None:
    assert (desktop.FILTER.name, desktop.FILTER.min_cutoff, desktop.FILTER.beta) == (
        "STEADY",
        0.3,
        0.03,
    )
    assert desktop.EYE_INDICES == ((33, 160, 158, 133, 153, 144), (362, 385, 387, 263, 373, 380))


def _fitted():
    x = np.array([[a, b] for a in np.linspace(-10, 10, 5) for b in np.linspace(-6, 6, 5)])
    y = np.c_[0.5 + x[:, 0] / 25, 0.5 - x[:, 1] / 15]
    return desktop.RecentredMapping(Ridge(standardize=True)).fit(x, y)


def test_recentred_mapping_moves_current_pose_to_centre() -> None:
    mapping = _fitted()
    assert not desktop.RecentredMapping(Ridge()).recentre()
    assert not mapping.recentre()  # nothing predicted yet
    before = mapping.predict([5.0, 3.0])
    assert before == pytest.approx([0.7, 0.3], abs=0.01)
    assert mapping.recentre()
    assert mapping.predict([5.0, 3.0]) == pytest.approx([0.5, 0.5])
    # Relative movement is unchanged by recentring.
    moved = mapping.predict([7.5, 3.0]) - mapping.predict([5.0, 3.0])
    assert moved == pytest.approx([0.1, 0.0], abs=0.01)
    mapping.fit(np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]]), np.array([[0, 0], [1, 1], [2, 0]]))
    assert np.all(mapping.offset == 0) and mapping.last is None


def test_head_filter_resets_on_missing_and_smooths() -> None:
    f = desktop.HeadFilter()
    assert f.update(None, 0) == (None, None)
    assert f.update([0.5, 0.5], 0)[0] == pytest.approx([0.5, 0.5])
    out = None
    for i in range(1, 30):
        out, lag = f.update([0.5 + (0.004 if i % 2 else -0.004), 0.5], int(i * 1e9 / 30))
    assert abs(out[0] - 0.5) < 0.002 and lag is None


def test_head_engine_registered_and_observe_sets_eye_closure() -> None:
    assert ENGINES["head"] is HeadEngine
    engine = HeadEngine.__new__(HeadEngine)
    engine.eye_closure = EyeClosure(HeadEngine.minimum_eye_open)
    eyes = [_eye(0, 3), _eye(50, 3)]
    engine.pair = SimpleNamespace(observe=lambda frame, ns: ([1.0, 2.0], eyes, "valid"))
    assert engine.observe(None, 0) == ([1.0, 2.0], eyes, "valid")
    assert engine.eyes_closed is False
    closed = [_eye(0, 0.5), _eye(50, 0.5)]
    engine.pair = SimpleNamespace(observe=lambda frame, ns: ([1.0, 2.0], closed, "valid"))
    engine.observe(None, 0)
    assert engine.eyes_closed is True
    engine.pair = SimpleNamespace(observe=lambda frame, ns: (None, None, "no_face"))
    assert engine.observe(None, 0) == (None, None, "no_face") and engine.eyes_closed is None


def test_head_engine_fits_app_calibration_and_recentres() -> None:
    session = Session("head")
    assert (session.feature_count, session.sample_count) == (2, 20)
    assert session.calibration_points == UNIGAZE_POINTS
    session.start_calibration([1512, 982, 0, 0, 2], "standard")
    for index in range(13):
        onset = index * 8
        session.ack(session.token, onset)
        x, y = session.point
        for stamp in np.linspace(1.5, 4.0, 20):
            session.sample(onset + stamp, [30 * x - 15, 10 - 20 * y], None)
        session.sample(onset + 7.5, None, None)
    assert session.phase == "fitting"
    engine = HeadEngine.__new__(HeadEngine)
    engine.mapping = desktop.RecentredMapping(Ridge(standardize=True))
    resets = []
    engine.smoothing = SimpleNamespace(reset=lambda: resets.append(1))
    features, labels = session.calibration_arrays()
    assert engine.fit(features.tolist(), labels.tolist()) < 0.01
    engine.mapping.predict([6.0, 0.0])
    assert engine.recentre() is True
    assert engine.mapping.predict([6.0, 0.0]) == pytest.approx([0.5, 0.5])
    assert len(resets) == 2  # once by fit, once by recentre


def test_hold_key_fires_once_per_long_press_only() -> None:
    assert R_KEY_CODE == 15 and RECENTRE_HOLD_SECONDS == 0.35
    key = HoldKey()
    # A typing tap never fires.
    assert not key.update(0.0, True) and not key.update(0.1, True) and not key.update(0.2, False)
    assert not key.update(1.0, True)
    assert not key.update(1.3, True)
    assert key.update(1.36, True)
    assert not key.update(2.0, True)  # still held: no repeat
    assert not key.update(2.1, False)
    assert not key.update(3.0, True) and key.update(3.4, True)


def test_runtime_recentre_needs_head_model_and_calibration(tmp_path) -> None:
    head = DesktopAPI(model_name="head", output=tmp_path)
    assert head.supports_recentre() and head.snapshot()["model_name"] == "head"
    assert head.command("recentre")["ok"] is False
    gaze = DesktopAPI(model_name="mgaze", output=tmp_path)
    assert not gaze.supports_recentre()
    assert gaze.command("recentre")["ok"] is False
    head.close()
    gaze.close()


def test_validate_head_assets_reports_missing_face_model(tmp_path, monkeypatch) -> None:
    from experiments.unigaze import settings

    monkeypatch.setenv("EYE_TRACKER_BLINK_MODEL", str(tmp_path / "missing.task"))
    with pytest.raises(RuntimeError, match="Kafa imleci"):
        settings.validate_head_assets()
