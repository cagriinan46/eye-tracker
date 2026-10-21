from dataclasses import replace

import pytest

from eye_tracker.intent.targeting import (
    GazePoint,
    TargetingConfig,
    TargetResolver,
    select_target,
)
from eye_tracker.intent.targets import TargetRect, UISnapshot, UITarget

CONFIG = TargetingConfig(50, 10, 0.1, 0.08, 0.5, 0.05)
SCREEN = TargetRect(0, 0, 500, 500)
BUTTON = UITarget("a", "button", TargetRect(100, 100, 20, 20), True, "press")


def snapshot(*targets):
    return UISnapshot("s", 1, "window", SCREEN, targets or (BUTTON,), "ok")


def update(resolver, time, snap=None, x=125, y=110, **kwargs):
    return resolver.update(
        GazePoint(x, y, time), snap or snapshot(), now=time, context_id="window", **kwargs
    )


def acquire(resolver, snap=None):
    assert update(resolver, 1, snap).status == "pending"
    assert update(resolver, 1.06, snap).status == "pending"
    return update(resolver, 1.12, snap)


def test_sustained_evidence_and_explicit_reset():
    resolver = TargetResolver(CONFIG)
    assert acquire(resolver).target == BUTTON
    resolver.reset()
    assert update(resolver, 1.13).status == "pending"


@pytest.mark.parametrize(
    "rect", [TargetRect(130, 100, 20, 20), BUTTON.rect, TargetRect(90, 90, 50, 50)]
)
def test_competition_including_nested_and_identical_bounds(rect):
    other = replace(BUTTON, target_id="b", rect=rect)
    resolver = TargetResolver(CONFIG)
    result = update(resolver, 1, snapshot(BUTTON, other))
    assert result.status == "ambiguous"
    assert result.target is None


def test_radius_and_runner_up_outside_radius_still_competes():
    resolver = TargetResolver(replace(CONFIG, radius=5))
    other = replace(BUTTON, target_id="b", rect=TargetRect(131, 100, 20, 20))
    assert update(resolver, 1, snapshot(BUTTON, other)).status == "ambiguous"
    assert update(resolver, 1.01, x=126).status == "no_nearby_target"


@pytest.mark.parametrize(
    "bad",
    [
        replace(BUTTON, enabled=False),
        replace(BUTTON, category="unknown"),
        replace(BUTTON, rect=TargetRect(600, 100, 20, 20)),
    ],
)
def test_ineligible_targets(bad):
    assert update(TargetResolver(CONFIG), 1, snapshot(bad)).status == "no_nearby_target"


@pytest.mark.parametrize(
    "gaze,status",
    [
        (GazePoint(float("nan"), 100, 1.13), "invalid_gaze"),
        (GazePoint(100, float("inf"), 1.13), "invalid_gaze"),
        (GazePoint(100, 100, 1.13, False), "invalid_gaze"),
        (GazePoint(-1, 100, 1.13), "invalid_gaze"),
        (GazePoint(100, 100, 2), "invalid_gaze"),
        (GazePoint(100, 100, 1), "invalid_gaze"),
    ],
)
def test_bad_gaze_clears_acquired_candidate(gaze, status):
    resolver = TargetResolver(CONFIG)
    acquire(resolver)
    result = resolver.update(gaze, snapshot(), now=1.13, context_id="window")
    assert result.status == status and result.target is None
    assert update(resolver, 1.14).status == "pending"


@pytest.mark.parametrize(
    "changes,status",
    [
        ({"captured_at": 0}, "stale_snapshot"),
        ({"captured_at": 2}, "stale_snapshot"),
        ({"context_id": "other"}, "unavailable_context"),
        ({"status": "incomplete", "targets": ()}, "unavailable_context"),
        ({"status": "unsupported_coordinates", "targets": ()}, "unavailable_context"),
    ],
)
def test_bad_snapshot_clears_acquired_candidate(changes, status):
    resolver = TargetResolver(CONFIG)
    acquire(resolver)
    result = update(resolver, 1.13, replace(snapshot(), **changes))
    assert result.status == status and result.target is None
    assert update(resolver, 1.14).status == "pending"


@pytest.mark.parametrize(
    "changes",
    [
        {"snapshot_id": "next"},
        {"captured_at": 1.1},
        {"targets": (replace(BUTTON, rect=TargetRect(101, 100, 20, 20)),)},
    ],
)
def test_no_identity_or_evidence_reuse_across_snapshots(changes):
    resolver = TargetResolver(CONFIG)
    acquire(resolver)
    assert update(resolver, 1.13, replace(snapshot(), **changes)).status == "pending"


@pytest.mark.parametrize("time", [1.12, 1.11])
def test_duplicate_or_reversed_timestamps_clear_evidence(time):
    resolver = TargetResolver(CONFIG)
    acquire(resolver)
    result = update(resolver, time)
    assert result.status == "invalid_time" and result.target is None
    assert update(resolver, 1.14).status == "pending"


def test_sample_gap_restarts_pending_and_ambiguity_clears():
    resolver = TargetResolver(CONFIG)
    acquire(resolver)
    assert update(resolver, 1.3).status == "pending"
    other = replace(BUTTON, target_id="b", rect=BUTTON.rect)
    assert update(resolver, 1.31, snapshot(BUTTON, other)).status == "ambiguous"
    assert update(resolver, 1.32).status == "pending"


def test_context_mismatch_and_invalid_clock():
    resolver = TargetResolver(CONFIG)
    for now, context, status in [
        (1, None, "unavailable_context"),
        (float("nan"), "window", "invalid_time"),
    ]:
        result = resolver.update(GazePoint(110, 110, 1), snapshot(), now=now, context_id=context)
        assert result.status == status and result.target is None


def test_baselines_do_not_imply_activation_or_temporal_stability():
    gaze = GazePoint(125, 110, 1)
    kwargs = dict(now=1, context_id="window", config=CONFIG)
    assert select_target(gaze, snapshot(), method="coordinate", **kwargs).target is None
    assert select_target(gaze, snapshot(), method="nearest", **kwargs).target == BUTTON
    assert (
        select_target(GazePoint(110, 110, 1), snapshot(), method="coordinate", **kwargs).target
        == BUTTON
    )
    with pytest.raises(ValueError):
        select_target(gaze, snapshot(), method="guess", **kwargs)


@pytest.mark.parametrize(
    "field",
    [
        "radius",
        "separation",
        "stable_seconds",
        "max_sample_gap",
        "max_snapshot_age",
        "max_gaze_age",
    ],
)
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_configuration_rejects_nonpositive_or_nonfinite(field, value):
    with pytest.raises(ValueError):
        replace(CONFIG, **{field: value})


def test_repeated_sample_with_advancing_delivery_time_cannot_accumulate():
    resolver = TargetResolver(CONFIG)
    assert update(resolver, 1).status == "pending"
    result = resolver.update(GazePoint(125, 110, 1), snapshot(), now=1.01, context_id="window")
    assert result.status == "invalid_time" and result.target is None


def test_reversed_delivery_time_with_advancing_sample_clears():
    resolver = TargetResolver(CONFIG)
    resolver.update(GazePoint(125, 110, 1), snapshot(), now=1.03, context_id="window")
    result = resolver.update(GazePoint(125, 110, 1.01), snapshot(), now=1.02, context_id="window")
    assert result.status == "invalid_time" and result.target is None


def test_switching_winner_requires_new_evidence_in_same_snapshot():
    resolver = TargetResolver(CONFIG)
    other = replace(BUTTON, target_id="b", rect=TargetRect(200, 100, 20, 20))
    snap = snapshot(BUTTON, other)
    assert acquire(resolver, snap).target == BUTTON
    result = update(resolver, 1.13, snap, x=210)
    assert result.status == "pending" and result.target is None


def test_eligibility_loss_clears_existing_target():
    resolver = TargetResolver(CONFIG)
    acquire(resolver)
    result = update(resolver, 1.13, snapshot(replace(BUTTON, enabled=False)))
    assert result.status == "no_nearby_target" and result.target is None


def test_exact_binary_thresholds_are_inclusive():
    config = TargetingConfig(8, 8, 0.125, 0.125, 0.5, 0.125)
    resolver = TargetResolver(config)
    assert update(resolver, 1, x=128).status == "pending"
    assert update(resolver, 1.125, x=128).target == BUTTON
    result = select_target(
        GazePoint(128, 110, 1.375),
        snapshot(),
        now=1.5,
        context_id="window",
        config=config,
        method="nearest",
    )
    assert result.target == BUTTON


def test_delivery_gap_alone_restarts_evidence():
    resolver = TargetResolver(replace(CONFIG, max_gaze_age=0.2))
    acquire(resolver)
    result = resolver.update(GazePoint(125, 110, 1.13), snapshot(), now=1.25, context_id="window")
    assert result.status == "pending" and result.target is None


def test_verified_identity_preserves_evidence_across_complete_refresh():
    resolver = TargetResolver(CONFIG)
    target = replace(BUTTON, continuity_id="lease/control")
    original = snapshot(target)
    assert acquire(resolver, original).target == target
    refreshed_target = replace(target, target_id="new-local-id")
    refreshed = replace(original, snapshot_id="next", captured_at=1.1, targets=(refreshed_target,))
    assert update(resolver, 1.13, refreshed).target == refreshed_target


@pytest.mark.parametrize(
    "changes",
    [
        {"continuity_id": "replacement"},
        {"rect": TargetRect(101, 100, 20, 20)},
        {"role": "link"},
        {"continuity_id": None},
    ],
)
def test_continuity_requires_same_identity_and_properties(changes):
    resolver = TargetResolver(CONFIG)
    target = replace(BUTTON, continuity_id="lease/control")
    acquire(resolver, snapshot(target))
    refreshed = replace(snapshot(replace(target, **changes)), snapshot_id="next", captured_at=1.1)
    assert update(resolver, 1.13, refreshed).status == "pending"


def test_continuity_does_not_override_competition_or_time_regression():
    target = replace(BUTTON, continuity_id="lease/control")
    resolver = TargetResolver(CONFIG)
    acquire(resolver, snapshot(target))
    rival = replace(BUTTON, target_id="rival")
    refreshed = replace(snapshot(target, rival), snapshot_id="next", captured_at=1.1)
    assert update(resolver, 1.13, refreshed).status == "ambiguous"
    resolver.reset()
    acquire(resolver, snapshot(target))
    older = replace(snapshot(target), snapshot_id="older", captured_at=0.99)
    assert update(resolver, 1.13, older).status == "invalid_time"


def test_four_scan_synthetic_stream_reduces_reacquisition_without_changing_gaze():
    from dataclasses import replace

    counts = {}
    for token in (None, "verified-native-control"):
        resolver = TargetResolver(CONFIG)
        candidates = 0
        for index in range(32):
            time = 1 + index * 0.025
            scan = index // 8
            target = replace(BUTTON, target_id=str(scan), continuity_id=token)
            current = replace(snapshot(target), snapshot_id=str(scan), captured_at=1 + scan * 0.2)
            decision = update(resolver, time, current)
            candidates += decision.status == "candidate"
        counts[token] = candidates
    assert counts["verified-native-control"] > counts[None]
    # The initial acquisition remains mandatory with verified identity as well.
    assert counts["verified-native-control"] < 32
