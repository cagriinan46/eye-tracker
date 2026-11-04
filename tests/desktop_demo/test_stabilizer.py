import pytest

from experiments.desktop_demo.protocol import Session
from eye_tracker.intent.gaze_stabilizer import GazeStabilizer

SIZE = (1000, 800)
HOME = [0.5, 0.5]
FAR = [0.5, 0.9]  # 320 px below HOME.


def test_small_moves_pass_through():
    g = GazeStabilizer()
    assert g.update(0, HOME, SIZE) == HOME
    assert g.update(0.1, [0.55, 0.5], SIZE) == [0.55, 0.5]


def test_single_outlier_is_held_and_never_shown():
    g = GazeStabilizer()
    g.update(0, HOME, SIZE)
    assert g.update(0.1, FAR, SIZE) == HOME
    assert g.update(0.2, HOME, SIZE) == HOME
    assert g.pending is None and g.held_since is None


def test_real_saccade_is_accepted_on_the_second_sample():
    g = GazeStabilizer()
    g.update(0, HOME, SIZE)
    assert g.update(0.1, FAR, SIZE) == HOME
    assert g.update(0.2, [0.51, 0.9], SIZE) == [0.51, 0.9]


def test_outliers_on_both_sides_of_a_blink_cannot_confirm_each_other():
    g = GazeStabilizer()
    g.update(0, HOME, SIZE)
    assert g.update(0.1, FAR, SIZE) == HOME  # Eyes closing.
    g.missing()
    assert g.update(0.3, FAR, SIZE) == HOME  # Eyes reopening.
    assert g.update(0.4, HOME, SIZE) == HOME


def test_scattered_samples_cannot_freeze_the_point():
    g = GazeStabilizer(max_hold=0.4)
    g.update(0, HOME, SIZE)
    assert g.update(0.1, [0.1, 0.1], SIZE) == HOME
    assert g.update(0.2, [0.9, 0.1], SIZE) == HOME
    assert g.update(0.3, [0.1, 0.9], SIZE) == HOME
    assert g.update(0.5, [0.9, 0.9], SIZE) == [0.9, 0.9]


def test_long_gap_starts_over():
    g = GazeStabilizer(max_gap=1)
    g.update(0, HOME, SIZE)
    assert g.update(2, FAR, SIZE) == FAR


def test_invalid_settings_are_rejected():
    with pytest.raises(ValueError):
        GazeStabilizer(jump_px=0)


def demo():
    s = Session(scenario="web")
    s.phase = "ready"
    s.geometry = [1000, 800, 0, 0, 1]
    s.start_demo()
    s.set_regions({name: [i * 0.12, 0.1, 0.02, 0.05] for i, name in enumerate(s.targets)})
    s.ack(s.token, 0)
    return s


def test_blink_keeps_cursor_ring_and_pull_in_place():
    s = demo()
    for i in range(5):
        s.sample(1 + i * 0.1, None, [0.03, 0.12])
    target, progress = s.magnet.target, s.magnet.progress
    assert target == "overview"
    point = s.last_point
    s.sample(1.5, None, [0.5, 0.9])  # Eyes closing: a valid frame pointing far away.
    assert s.magnet.target == target and s.magnet.progress > progress
    assert s.last_point[0] < 0.05 and point[0] < 0.05
    s.sample(1.6, None, None)  # Eyes closed.
    assert s.last_point is None
    assert s.snapshot()["gaze_ring"]["point"] is not None
    s.sample(1.7, None, [0.03, 0.12])
    assert s.magnet.target == target
    assert not s.trials


def test_outlier_still_counts_in_the_recorded_gaze_error():
    s = demo()
    s.sample(1.0, None, [0.01, 0.125])
    s.sample(1.1, None, [0.5, 0.9])
    assert s.trial_errors[0] == pytest.approx(0)
    assert s.trial_errors[1] > 300


def test_ring_disappears_after_a_long_loss_of_gaze():
    s = demo()
    s.sample(1.0, None, [0.03, 0.12])
    s.sample(1.2, None, None)
    assert s.snapshot()["gaze_ring"] is not None
    s.sample(1.7, None, None)
    assert s.snapshot()["gaze_ring"] is None
