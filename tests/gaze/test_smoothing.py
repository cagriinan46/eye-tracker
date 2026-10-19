import math

import pytest

from eye_tracker.gaze.smoothing import EMASmoother


def test_first_point_initializes_and_both_axes_follow_ema():
    smoother = EMASmoother(alpha=0.2)
    assert smoother.update((100, 200)) == (100, 200)
    assert smoother.update((200, 100)) == pytest.approx((120, 180))
    assert smoother.update((200, 100)) == pytest.approx((136, 164))


def test_loss_resets_and_does_not_display_stale_point():
    smoother = EMASmoother()
    smoother.update((100, 200))
    assert smoother.update(None) is None
    assert smoother.update((900, 700)) == (900, 700)
    smoother.reset()
    assert smoother.update((-100, 1200)) == (-100, 1200)


@pytest.mark.parametrize("point", [(math.nan, 0), (0, math.inf)])
def test_nonfinite_point_cannot_poison_future_predictions(point):
    smoother = EMASmoother()
    smoother.update((1, 2))
    assert smoother.update(point) is None
    assert smoother.update((3, 4)) == (3, 4)


@pytest.mark.parametrize("alpha", [0, -0.2, 1.1, math.nan, math.inf])
def test_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError):
        EMASmoother(alpha=alpha)


def test_alpha_one_disables_smoothing():
    smoother = EMASmoother(alpha=1)
    smoother.update((100, 100))
    assert smoother.update((0, 200)) == (0, 200)
