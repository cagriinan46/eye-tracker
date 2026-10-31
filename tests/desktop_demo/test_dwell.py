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


def test_short_measurement_gap_holds_progress_without_crediting_it():
    d = RegionDwell(seconds=1.2, max_gap=0.3, max_interruption=0.5)
    for i in range(6):
        d.update(i * 0.125, "save")
    held = d.progress
    d.missing(0.75)
    d.missing(0.875)
    assert d.target == "save" and d.progress == held
    # The 0.375 s gap is not counted: 0.625 s observed before, 1.2 s needed.
    assert not d.update(1.0, "save")
    assert abs(d.progress - 0.625 / 1.2) < 1e-9
    for t in (1.125, 1.25, 1.375, 1.5):
        assert not d.update(t, "save")
    assert d.update(1.6, "save")


def test_missing_measurement_never_completes_a_dwell():
    d = RegionDwell()
    for i in range(10):
        d.update(i * 0.125, "save")
    for t in (1.2, 1.3, 1.4):
        d.missing(t)
    assert not d.fired
    assert not d.update(1.45, "save")


def test_long_gap_other_target_or_outside_point_still_reset():
    d = RegionDwell(max_interruption=0.5)
    d.update(0, "save")
    d.update(0.4, "save")
    d.missing(0.5)
    d.missing(0.95)
    assert d.target is None
    d.update(1, "save")
    d.update(1.4, "save")
    d.missing(1.5)
    d.update(1.6, "clear")
    assert d.target == "clear" and d.progress == 0
    d.update(1.8, "clear")
    d.update(1.9, None)
    assert d.target is None and d.progress == 0


def test_hold_cannot_bridge_beyond_limit_from_last_in_region_sample():
    d = RegionDwell(max_interruption=0.5)
    d.update(0, "save")
    d.update(0.5, "save")
    d.missing(0.6)
    assert not d.update(1.05, "save")
    assert d.progress == 0 and d.started == 1.05
