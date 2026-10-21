from contextlib import contextmanager
from dataclasses import replace
from threading import Event
from time import monotonic, sleep

import pytest

from eye_tracker.app.semantic_preview import CheckedSnapshot, PreviewFeed, SemanticPreview
from eye_tracker.intent.targeting import GazePoint, TargetingConfig
from eye_tracker.intent.targets import TargetRect, UISnapshot, UITarget

SCREEN = TargetRect(0, 0, 500, 500)
TARGET = UITarget("t", "button", TargetRect(100, 100, 20, 20), True, "press")
CONFIG = TargetingConfig(50, 10, 0.1, 0.08, 0.5, 0.05)


def snap(time=1):
    return UISnapshot("s", time, "window", SCREEN, (TARGET,), "ok")


def wait_until(predicate):
    deadline = monotonic() + 2
    while monotonic() < deadline:
        if predicate():
            return
        sleep(0.001)
    pytest.fail("worker did not reach expected state")


class Provider:
    def __init__(self):
        self.entered = Event()
        self.release = Event()
        self.exited = Event()
        self.block = False
        self.fail = False

    @contextmanager
    def session(self):
        self.entered.set()
        if self.block:
            assert self.release.wait(2)
        if self.fail:
            raise RuntimeError("native failure")
        self.snapshot = snap(monotonic())
        try:
            yield self
        finally:
            self.exited.set()

    def current_context(self):
        return "window"


def test_explicit_start_latest_only_and_close():
    provider = Provider()
    feed = PreviewFeed(provider)
    assert feed.latest() is None and not provider.entered.is_set()
    feed.start()
    try:
        wait_until(lambda: feed.latest() is not None)
        assert feed.latest().context_id == "window"
        with pytest.raises(RuntimeError):
            feed.start()
    finally:
        assert feed.close(1)
    assert feed.latest() is None and provider.exited.is_set()
    with pytest.raises(RuntimeError):
        feed.start()


def test_blocked_native_work_does_not_block_consumer_or_shutdown():
    provider = Provider()
    provider.block = True
    feed = PreviewFeed(provider)
    feed.start()
    assert provider.entered.wait(1)
    try:
        assert feed.latest() is None
        assert not feed.close(0)
        assert feed.latest() is None
    finally:
        provider.release.set()
        assert feed.close(1)
    assert feed.latest() is None


def test_worker_failure_is_visible_and_clears_state():
    provider = Provider()
    provider.fail = True
    feed = PreviewFeed(provider)
    feed.start()
    try:
        wait_until(lambda: feed.status == "failed")
        assert feed.latest() is None
    finally:
        assert feed.close(1)


def test_slow_context_check_uses_start_time_and_expired_snapshot_is_hidden():
    provider = Provider()
    checking, release, later_release = Event(), Event(), Event()
    calls = [0]
    time = [1.0]

    @contextmanager
    def session():
        provider.snapshot = snap()
        yield provider

    def context():
        calls[0] += 1
        checking.set()
        assert (release if calls[0] == 1 else later_release).wait(2)
        return "window"

    provider.session = session
    provider.current_context = context
    feed = PreviewFeed(provider, clock=lambda: time[0])
    feed.start()
    assert checking.wait(1)
    time[0] = 1.2
    release.set()
    try:
        wait_until(lambda: feed.latest() is not None)
        assert feed.latest().checked_at == 1
        time[0] = 1.5
        assert feed.latest() is None
    finally:
        later_release.set()
        assert feed.close(1)


def checked(time=1, **changes):
    return replace(CheckedSnapshot(snap(), time, "window"), **changes)


def tick(preview, time, value=None, **kwargs):
    return preview.update(
        GazePoint(125, 110, time),
        value or checked(time),
        now=time,
        input_screen=SCREEN,
        enabled=True,
        **kwargs,
    )


def test_opt_in_and_stability_without_coordinate_mutation():
    preview = SemanticPreview(CONFIG, max_context_age=0.1)
    gaze = GazePoint(125, 110, 1)
    assert preview.update(gaze, checked(), now=1, input_screen=SCREEN).target is None
    assert tick(preview, 1).status == "pending"
    assert tick(preview, 1.06).status == "pending"
    assert tick(preview, 1.12).target == TARGET
    assert gaze == GazePoint(125, 110, 1)


@pytest.mark.parametrize(
    "value", [None, checked(0), checked(2), checked(context_id="other"), checked(float("nan"))]
)
def test_missing_stale_or_changed_context_rejects_and_resets(value):
    preview = SemanticPreview(CONFIG, max_context_age=0.1)
    for t in (1, 1.06, 1.12):
        tick(preview, t)
    result = preview.update(
        GazePoint(125, 110, 1.13), value, now=1.13, input_screen=SCREEN, enabled=True
    )
    assert result.target is None and result.status == "unavailable_context"
    assert tick(preview, 1.14).status == "pending"


def test_coordinates_and_opt_out_clear_candidate():
    preview = SemanticPreview(CONFIG, max_context_age=0.1)
    for screen, enabled in [(TargetRect(0, 0, 1000, 1000), True), (SCREEN, False)]:
        for t in (1, 1.06, 1.12):
            tick(preview, t)
        result = preview.update(
            GazePoint(125, 110, 1.13), checked(1.13), now=1.13, input_screen=screen, enabled=enabled
        )
        assert result.target is None
        assert tick(preview, 1.14).status == "pending"
        preview.reset()


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_configuration(value):
    with pytest.raises(ValueError):
        PreviewFeed(Provider(), refresh_seconds=value)
    with pytest.raises(ValueError):
        PreviewFeed(Provider(), check_seconds=value)
    with pytest.raises(ValueError):
        SemanticPreview(CONFIG, max_context_age=value)


def test_failure_after_publication_clears_old_snapshot_and_releases_session():
    provider = Provider()
    called = Event()
    count = [0]

    def context():
        count[0] += 1
        if count[0] > 1:
            called.set()
            raise RuntimeError("context read failed")
        return "window"

    provider.current_context = context
    feed = PreviewFeed(provider, check_seconds=0.01)
    feed.start()
    try:
        assert called.wait(1)
        wait_until(lambda: feed.status == "failed")
        assert feed.latest() is None
        assert provider.exited.is_set()
    finally:
        assert feed.close(1)


def test_context_mismatch_discards_snapshot_before_next_blocked_scan():
    provider = Provider()
    scans = [0]
    second_scan, release = Event(), Event()

    @contextmanager
    def session():
        scans[0] += 1
        if scans[0] > 1:
            second_scan.set()
            assert release.wait(2)
        provider.snapshot = snap(monotonic())
        yield provider

    provider.session = session
    provider.current_context = lambda: "different-window"
    feed = PreviewFeed(provider, check_seconds=0.01)
    feed.start()
    try:
        assert second_scan.wait(1)
        assert feed.latest() is None
    finally:
        release.set()
        assert feed.close(1)


@pytest.mark.parametrize("outcome", ["ok", "failed", "context", "closed"])
def test_early_refresh_retains_only_unexpired_values_and_clears_on_failure(outcome):
    provider = Provider()
    refreshing, release, next_scan = Event(), Event(), Event()
    now = [1.0]
    scans = [0]

    @contextmanager
    def session():
        scans[0] += 1
        if scans[0] > 1:
            next_scan.set()
            assert provider.release.wait(2)
        provider.snapshot = snap(now[0])
        yield provider

    def refresh():
        refreshing.set()
        assert release.wait(2)
        if outcome == "failed":
            return replace(snap(now[0]), status="incomplete", targets=())
        return replace(
            snap(now[0]),
            snapshot_id="new",
            context_id=("other" if outcome == "context" else "window"),
        )

    provider.session = session
    provider.refresh = refresh
    feed = PreviewFeed(provider, clock=lambda: now[0], check_seconds=0.001)
    feed.start()
    try:
        wait_until(lambda: feed.latest() is not None)
        now[0] = 1.21
        assert refreshing.wait(1)
        old = feed.latest()
        assert old.snapshot.captured_at == 1
        assert old.checked_at == 1.21
        assert feed.status == "refreshing"
        # Context expires independently, even before snapshot expiry.
        preview = SemanticPreview(CONFIG, max_context_age=0.1)
        assert tick(preview, 1.32, old).status == "unavailable_context"
        now[0] = 1.41
        assert feed.latest() is None
        assert old.checked_at == 1.21
        if outcome == "closed":
            assert not feed.close(0)
        release.set()
        if outcome == "ok":
            wait_until(lambda: feed.latest() is not None)
            assert feed.latest().snapshot.snapshot_id == "new"
        elif outcome != "closed":
            assert next_scan.wait(1)
            assert feed.latest() is None
    finally:
        release.set()
        provider.release.set()
        assert feed.close(1)
    assert feed.latest() is None and feed.status == "closed"
