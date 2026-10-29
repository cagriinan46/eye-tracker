from eye_tracker.intent.region_dwell import RegionDwell


def test_dwell_requires_continuous_same_region_and_fresh_samples():
    d = RegionDwell(seconds=1.2, max_gap=0.3)
    assert not d.update(0, "circle")
    for i in range(1, 6):
        assert not d.update(i * 0.2, "circle")
    assert d.update(1.21, "circle")
    assert not d.update(1.3, "circle")
    d.update(1.4, None)
    assert not d.update(1.5, "circle")
    assert d.progress == 0


def test_target_change_and_gap_reset():
    d = RegionDwell()
    d.update(0, "a")
    d.update(0.2, "a")
    d.update(0.4, "b")
    assert d.progress == 0
    d.update(2, "b")
    assert d.progress == 0
    d.reset()
    assert d.target is None
