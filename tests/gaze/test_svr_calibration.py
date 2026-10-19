"""Synthetic mapping checks; these do not establish human gaze accuracy."""

import math

import pytest

from eye_tracker.gaze.calibration import SVRCalibrationSample, fit_svr


def target(h, v):
    return 0.15 + 0.5 * h + 0.15 * v, 0.1 + 0.5 * v + 0.2 * h


def samples():
    return [
        SVRCalibrationSample(h, v, *target(h, v), 0, 0, 0)
        for h in (0.1, 0.3, 0.5, 0.7, 0.9)
        for v in (0.1, 0.3, 0.5, 0.7, 0.9)
    ]


def test_linear_cross_axis_predictions_on_unseen_features():
    mapping = fit_svr(samples(), screen_width=1512, screen_height=949)
    for h, v in ((0.2, 0.4), (0.4, 0.8), (0.6, 0.2), (0.8, 0.6)):
        expected = target(h, v)
        assert mapping.predict(h, v, 0, 0, 0) == pytest.approx(expected, abs=0.025)
        assert mapping.predict_pixels(h, v, 0, 0, 0) == pytest.approx(
            (expected[0] * 1512, expected[1] * 949), abs=38
        )


def test_pixel_units_and_prediction_does_not_refit():
    mapping = fit_svr(samples(), screen_width=1512, screen_height=949)
    before = mapping.predict_pixels(0.4, 0.6, 0, 0, 0)
    mapping.predict_pixels(12.0, -7.0, 0, 0, 0)
    assert mapping.predict_pixels(0.4, 0.6, 0, 0, 0) == before
    assert mapping.predict(0.4, 0.6, 0, 0, 0) == pytest.approx((before[0] / 1512, before[1] / 949))


def test_svr_receives_unscaled_pixel_targets(monkeypatch):
    import numpy as np
    from sklearn.svm import SVR

    calls = []
    original = SVR.fit

    def capture(self, X, y, **kwargs):
        calls.append((self.get_params(), np.asarray(X), np.asarray(y)))
        return original(self, X, y, **kwargs)

    monkeypatch.setattr(SVR, "fit", capture)
    fit_svr(samples(), screen_width=1512, screen_height=949)
    assert len(calls) == 2
    for (params, X, y), axis, size in zip(calls, ("target_x", "target_y"), (1512, 949)):
        assert params["C"] == 1000.0
        assert params["kernel"] == "rbf"
        assert params["gamma"] == 0.1
        assert params["epsilon"] == 1.0
        assert X.mean(axis=0) == pytest.approx([0, 0, 0, 0, 0], abs=1e-12)
        assert X.std(axis=0) == pytest.approx([1, 1, 0, 0, 0])
        assert y == pytest.approx([getattr(s, axis) * size for s in samples()])


def test_feature_scaling_handles_different_eye_feature_units():
    original = fit_svr(samples(), screen_width=1000, screen_height=500)
    rescaled = [
        SVRCalibrationSample(
            100 * s.horizontal_feature + 40,
            s.vertical_feature / 1000,
            s.target_x,
            s.target_y,
            0,
            0,
            0,
        )
        for s in samples()
    ]
    mapping = fit_svr(rescaled, screen_width=1000, screen_height=500)
    assert mapping.predict(80, 0.0006, 0, 0, 0) == pytest.approx(
        original.predict(0.4, 0.6, 0, 0, 0)
    )


@pytest.mark.parametrize("width,height", [(0, 949), (1512, -1), (math.nan, 949), (1.5, 949)])
def test_invalid_screen_size(width, height):
    with pytest.raises(ValueError):
        fit_svr(samples(), screen_width=width, screen_height=height)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_nonfinite_live_features(bad):
    mapping = fit_svr(samples(), screen_width=1512, screen_height=949)
    with pytest.raises(ValueError):
        mapping.predict_pixels(bad, 0.2, 0, 0, 0)


def test_rejects_insufficient_or_degenerate_calibration():
    with pytest.raises(ValueError):
        fit_svr(samples()[:2], screen_width=1512, screen_height=949)
    with pytest.raises(ValueError):
        fit_svr([samples()[0]] * 25, screen_width=1512, screen_height=949)
    with pytest.raises(TypeError):
        fit_svr([(0, 0, 0, 0)] * 25, screen_width=1512, screen_height=949)


def test_pose_columns_and_live_order_match(monkeypatch):
    from unittest.mock import Mock

    import numpy as np

    import eye_tracker.gaze.calibration as module

    data = [
        module.SVRCalibrationSample(
            s.horizontal_feature, s.vertical_feature, s.target_x, s.target_y, i, -2 * i, 3 * i
        )
        for i, s in enumerate(samples())
    ]
    mapping = fit_svr(data, screen_width=1512, screen_height=949)
    assert mapping.svr_x.named_steps["standardscaler"].mean_ == pytest.approx(
        np.array(
            [[s.horizontal_feature, s.vertical_feature, s.pitch, s.yaw, s.roll] for s in data]
        ).mean(axis=0)
    )
    x, y = Mock(), Mock()
    x.predict.return_value = [123]
    y.predict.return_value = [456]
    model = module.SVRMapping(x, y, 1512, 949)
    assert model.predict_pixels(0.4, 0.2, 10, -20, 30) == (123, 456)
    x.predict.assert_called_once_with([[0.4, 0.2, 10, -20, 30]])
    y.predict.assert_called_once_with([[0.4, 0.2, 10, -20, 30]])
    with pytest.raises(ValueError):
        model.predict_pixels(0.4, 0.2, math.nan, 0, 0)
    with pytest.raises(TypeError):
        model.predict_pixels(0.4, 0.2)
