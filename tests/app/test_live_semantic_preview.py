from types import SimpleNamespace

import pytest

from eye_tracker.app.live_semantic_preview import LiveSemanticPreview
from eye_tracker.app.semantic_preview import CheckedSnapshot
from eye_tracker.intent.targets import TargetRect, UISnapshot, UITarget

SCREEN = TargetRect(0, 0, 500, 400)
TARGET = UITarget("t", "button", TargetRect(100, 100, 20, 20), True, "press")


def setup():
    time = [1.0]
    calls = []
    snapshot = UISnapshot("s", 1, "window", SCREEN, (TARGET,), "ok")
    feed = SimpleNamespace(
        status="ready",
        start=lambda: calls.append("feed-start"),
        latest=lambda: CheckedSnapshot(snapshot, time[0], "window"),
        close=lambda: calls.append("feed-close") or True,
    )
    outline = SimpleNamespace(
        start=lambda: calls.append("outline-start"),
        check_stop=lambda: None,
        hide=lambda: calls.append("hide"),
        show=lambda r, e: calls.append((r, e)),
        close=lambda: calls.append("outline-close"),
    )
    preview = LiveSemanticPreview(feed, outline, SCREEN, clock=lambda: time[0])
    return preview, feed, outline, time, calls


def test_no_resources_start_before_tab_and_candidate_expires_by_input_freshness():
    preview, _, _, time, calls = setup()
    assert calls == []
    assert preview.update([125, 110], 1, desktop=False)["semantic_status"] == "disabled"
    preview.activate()
    for t in (1, 1.06, 1.12):
        time[0] = t
        result = preview.update([125, 110], t, desktop=True)
    assert result["semantic_status"] == "candidate"
    rect, expires = calls[-1]
    assert rect == TARGET.rect
    assert expires == pytest.approx(1.24)
    time[0] = 1.13
    assert preview.update(None, 1.13, desktop=True)["semantic_status"] == "invalid_gaze"
    assert calls[-1] == "hide"
    preview.close()
    assert calls[-2:] == ["outline-close", "feed-close"]


def test_missing_context_and_expired_gaze_hide():
    preview, feed, _, time, calls = setup()
    preview.activate()
    feed.latest = lambda: None
    assert preview.update([125, 110], 1, desktop=True)["semantic_status"] == "unavailable_context"
    assert calls[-1] == "hide"


def test_partial_start_failure_cleans_both_resources():
    preview, _, outline, _, calls = setup()

    def fail():
        raise RuntimeError("start")

    outline.start = fail
    with pytest.raises(RuntimeError):
        preview.activate()
    assert calls[-2:] == ["outline-close", "feed-close"]


def test_close_always_closes_feed_if_outline_cleanup_fails():
    preview, _, outline, _, calls = setup()

    def fail():
        raise RuntimeError("close")

    outline.close = fail
    with pytest.raises(RuntimeError):
        preview.close()
    assert calls[-1] == "feed-close"
