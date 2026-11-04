import pytest

from experiments.desktop_demo.protocol import Session
from eye_tracker.intent.region_magnet import RegionMagnet

SIZE = (1000, 800)
# x 100-200 px, y 80-120 px; center (150, 100) px.
REGIONS = {"a": [0.1, 0.1, 0.1, 0.05], "b": [0.5, 0.1, 0.1, 0.05]}


def pixels(point):
    return point[0] * SIZE[0], point[1] * SIZE[1]


def test_point_outside_ring_is_not_pulled():
    magnet = RegionMagnet(radius=70)
    for t in (0, 0.5, 1):
        assert magnet.update(t, [0.35, 0.5], REGIONS, SIZE) == [0.35, 0.5]
    assert magnet.target is None


def test_pull_grows_gradually_until_the_control_center():
    magnet = RegionMagnet(radius=70, pull_seconds=0.8)
    gaze = [0.25, 0.125]  # 50 px right of the control edge.
    xs = [pixels(magnet.update(i * 0.1, gaze, REGIONS, SIZE))[0] for i in range(10)]
    assert magnet.target == "a"
    assert xs[0] == pytest.approx(250)
    assert all(later < earlier for earlier, later in zip(xs[:8], xs[1:9]))
    assert xs[1] > 240  # Gentle start rather than a jump.
    assert xs[-1] == pytest.approx(150)


def test_looking_away_releases_at_once():
    magnet = RegionMagnet(radius=70, pull_seconds=0.8)
    for i in range(10):
        magnet.update(i * 0.1, [0.25, 0.125], REGIONS, SIZE)
    assert magnet.update(1.0, [0.35, 0.5], REGIONS, SIZE) == [0.35, 0.5]
    assert magnet.target is None and magnet.progress == 0


def test_nearest_control_wins_and_small_jitter_does_not_switch():
    regions = {"a": [0.1, 0.1, 0.1, 0.05], "b": [0.21, 0.1, 0.1, 0.05]}
    magnet = RegionMagnet(radius=70, switch_margin=20)
    magnet.update(0, [0.19, 0.125], regions, SIZE)
    assert magnet.target == "a"
    magnet.update(0.1, [0.215, 0.125], regions, SIZE)  # 15 px past "a", inside "b".
    assert magnet.target == "a"
    magnet.update(0.2, [0.25, 0.125], regions, SIZE)
    assert magnet.target == "b" and magnet.progress == 0


def test_long_gap_restarts_the_pull():
    magnet = RegionMagnet(radius=70, pull_seconds=0.8, max_gap=0.5)
    for i in range(10):
        magnet.update(i * 0.1, [0.25, 0.125], REGIONS, SIZE)
    assert magnet.progress == 1
    magnet.update(2, [0.25, 0.125], REGIONS, SIZE)
    assert magnet.progress == 0


def test_invalid_settings_are_rejected():
    with pytest.raises(ValueError):
        RegionMagnet(radius=0)


def demo():
    s = Session(scenario="web")
    s.phase = "ready"
    s.geometry = [1000, 800, 0, 0, 1]
    s.start_demo()
    # Overview spans x 0-20 px; the next control starts at 120 px.
    s.set_regions({name: [i * 0.12, 0.1, 0.02, 0.05] for i, name in enumerate(s.targets)})
    s.ack(s.token, 0)
    return s


def test_gaze_beside_a_control_is_selected_and_error_stays_unassisted():
    s = demo()
    t = 1.0
    while not s.trials and t < 4:
        s.sample(t, None, [0.05, 0.125])
        t += 0.1
    assert s.trials[0]["selected"] == "overview"
    # Gaze stayed 40 px from the 10 px center even though the cursor reached it.
    assert s.trials[0]["mean_error_px"] == pytest.approx(40)


def test_cue_time_shows_raw_gaze_without_pull():
    s = demo()
    s.sample(0.5, None, [0.05, 0.125])
    assert s.last_point == [0.05, 0.125]
    assert s.magnet.target is None


def test_magnet_state_clears_between_trials_and_on_pause():
    s = demo()
    t = 1.0
    while not s.trials and t < 4:
        s.sample(t, None, [0.05, 0.125])
        t += 0.1
    assert s.magnet.target is None and s.magnet.progress == 0
    s.ack(s.token, t)
    s.sample(t + 1.1, None, [0.05, 0.125])
    assert s.magnet.target is not None
    s.pause(t + 1.2)
    assert s.magnet.target is None
    assert s.snapshot()["gaze_ring"] is None


def test_snapshot_reports_ring_during_demo():
    s = demo()
    s.sample(1.0, None, [0.05, 0.125])
    ring = s.snapshot()["gaze_ring"]
    assert ring["radius_px"] == 35 and ring["target"] == "overview"
    assert ring["point"] == s.last_point
