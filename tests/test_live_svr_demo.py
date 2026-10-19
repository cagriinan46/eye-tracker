"""Single-camera SVR tests: no participant data or hardware."""

import copy
import json
from math import sin

import pytest


def old_details(x, y):
    opening = x * x + 0.3 * y * y
    blend = sin(3 * x + y)
    pitch = x * y + 0.2 * x * x * x
    return {
        "status": "usable",
        "horizontal": 0.1 + 0.8 * x,
        "vertical": y - 0.1 * opening - 0.2 * blend - 0.05 * pitch,
        "binocular_eye_opening": opening,
        "look_down_left": blend,
        "look_down_right": blend,
        "look_up_left": 0,
        "look_up_right": 0,
        "head_pitch_deg": pitch,
        "blink_left": 0.05,
        "blink_right": 0.05,
    }


def calibration():
    rows = []
    for p, (x, y) in enumerate(
        ((x, y) for y in (0.1, 0.3, 0.5, 0.7, 0.9) for x in (0.1, 0.3, 0.5, 0.7, 0.9)), start=1
    ):
        for camera in ("top", "bottom"):
            for _ in range(6):
                rows.append(
                    {
                        "camera": camera,
                        "presentation": p,
                        "phase": "calibration",
                        "target_id": str(p),
                        "target_x": x,
                        "target_y": y,
                        "trial_number": 1,
                        **old_details(x, y),
                    }
                )
    return rows


def details(x, y):
    return dict(
        old_details(x, y), vertical=0.2 + 0.6 * y, head_pitch_deg=0, head_yaw_deg=0, head_roll_deg=0
    )


def rows():
    return [
        dict(
            r,
            camera="macbook",
            vertical=0.2 + 0.6 * r["target_y"],
            head_pitch_deg=0,
            head_yaw_deg=0,
            head_roll_deg=0,
        )
        for r in calibration()
        if r["camera"] == "top"
    ]


def test_single_camera_fit_ignores_unused_combo_signals_and_validation():
    import live_svr_demo as demo

    data = rows()
    for r in data:
        for k in (
            "binocular_eye_opening",
            "look_up_left",
            "look_up_right",
            "look_down_left",
            "look_down_right",
        ):
            r.pop(k)
    mapping = demo.fit_calibration(data, (1512, 949))
    assert mapping["calibration_targets"] == 25
    before = demo.predict_single(mapping, details(0.4, 0.6))
    assert before["point"] == pytest.approx([0.4, 0.6], abs=0.03)
    bad = copy.deepcopy(data)
    for r in bad:
        r["phase"] = "validation"
        r["target_x"] = 5000
    other = demo.fit_calibration(data + bad, (1512, 949))
    assert demo.predict_single(other, details(0.4, 0.6)) == before
    json.dumps(demo.mapping_metadata(mapping), allow_nan=False)
    with pytest.raises(ValueError):
        demo.fit_calibration([r for r in data if r["presentation"] <= 19], (1512, 949))


def test_blink_and_tracking_loss_hide_point_and_reset_ema():
    import live_svr_demo as demo

    mapping = demo.fit_calibration(rows(), (1512, 949))
    d = details(0.4, 0.6)
    d["blink_left"] = 0.9
    assert demo.predict_single(mapping, d)["point"] is None
    assert demo.safe_features({"status": "unavailable_no_face"}) is None
    smoother = demo.EMASmoother()
    raw = {"point": [0.2, 0.2]}
    demo.smooth_prediction(raw, smoother)
    assert demo.smooth_prediction({"point": [0.8, 0.6]}, smoother)["point"] == pytest.approx(
        [0.32, 0.28]
    )
    assert raw == {"point": [0.2, 0.2]}
    assert demo.smooth_prediction({"point": None}, smoother)["point"] is None
    assert demo.smooth_prediction({"point": [0.8, 0.6]}, smoother)["point"] == (0.8, 0.6)


def test_selects_builtin_by_name_and_opencv_sorted_id_order():
    import live_svr_demo as demo

    devices = [("aaa", "Cagri iPhone Camera"), ("zzz", "FaceTime HD Camera")]
    assert demo.select_macbook_camera(devices) == 1
    assert demo.select_macbook_camera(devices[1:]) == 0
    with pytest.raises(RuntimeError):
        demo.select_macbook_camera(devices[:1])


def test_preview_blocks_enter_until_eye_tracking_is_ready(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    import numpy as np

    import eye_tracker.vision.eye_features as ef
    import eye_tracker.vision.eye_topology as et
    import live_svr_demo as demo

    monkeypatch.setattr(et, "eye_geometry_from_observation", lambda obs: (None, None))
    monkeypatch.setattr(
        ef,
        "extract_binocular_features",
        lambda *args: SimpleNamespace(horizontal=0.4, vertical=0.1),
    )
    frame = SimpleNamespace(payload=np.zeros((100, 100, 3), dtype=np.uint8), width=100, height=100)
    source = Mock()
    source.read.return_value = frame
    extractor = Mock(
        last_signals={
            "blink_left": 0.1,
            "blink_right": 0.1,
            "head_pitch_deg": 0,
            "head_yaw_deg": 0,
            "head_roll_deg": 0,
        }
    )
    cv = Mock()
    cv.getWindowProperty.return_value = 1
    cv.waitKey.side_effect = [13] * 5
    cv.resize.side_effect = lambda image, size: np.zeros((size[1], size[0], 3), dtype=np.uint8)
    demo.wait_for_single_camera(cv, np, "preview", (800, 600), source, extractor)
    assert source.read.call_count == 5
    extractor.last_signals = {}
    cv.waitKey.side_effect = [13, 27]
    with pytest.raises(InterruptedError):
        demo.wait_for_single_camera(cv, np, "preview", (800, 600), source, extractor)


def test_blink_rows_never_enter_collection_or_medians(monkeypatch):
    import live_svr_demo as demo

    accepted = []
    bad = dict(rows()[0], blink_left=0.9, horizontal=999)
    assert not demo.append_calibration_row(accepted, bad)
    assert accepted == []
    assert demo.append_calibration_row(accepted, rows()[0])
    assert len(accepted) == 1
    data = rows()
    captured = []
    original = demo.fit_svr

    def capture(samples, **kwargs):
        captured.extend(samples)
        return original(samples, **kwargs)

    monkeypatch.setattr(demo, "fit_svr", capture)
    demo.fit_calibration(data + [bad] * 100, (1512, 949))
    assert captured[0].horizontal_feature == data[0]["horizontal"]
    assert captured[0].pitch == 0
    assert captured[0].yaw == 0
    assert captured[0].roll == 0
    for field in ("head_pitch_deg", "head_yaw_deg", "head_roll_deg"):
        invalid = dict(data[0])
        invalid[field] = None
        assert demo.safe_features(invalid) is None
