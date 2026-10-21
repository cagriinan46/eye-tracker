"""Coordinate existing read-only feed, resolver and an expiring outline adapter."""

from time import monotonic

from eye_tracker.app.semantic_preview import PreviewFeed, SemanticPreview
from eye_tracker.intent.targeting import GazePoint, TargetingConfig
from eye_tracker.intent.targets import TargetRect

# Development settings, not calibrated user defaults or accuracy guarantees.
CONFIG = TargetingConfig(50, 10, 0.1, 0.2, 0.5, 0.2)
CONTEXT_AGE = 0.15
OUTLINE_SECONDS = 0.12


class LiveSemanticPreview:
    def __init__(self, feed, outline, screen, *, clock=monotonic):
        self.feed = feed
        self.outline = outline
        self.screen = screen
        self.clock = clock
        self.resolver = SemanticPreview(CONFIG, max_context_age=CONTEXT_AGE)
        self.active = False
        self.closed = False

    def activate(self):
        if self.closed:
            raise RuntimeError("preview already closed")
        if self.active:
            return
        try:
            self.feed.start()
            self.outline.start()
            self.active = True
        except BaseException:
            self.close()
            raise

    def check_stop(self):
        if self.active:
            self.outline.check_stop()

    def update(self, point, captured_at, *, desktop):
        if not self.active or not desktop or self.closed:
            self.resolver.reset()
            self.outline.hide()
            return {"semantic_status": "disabled"}
        self.check_stop()
        now = self.clock()
        checked = self.feed.latest()
        gaze = GazePoint(*(point if point is not None else (0, 0)), captured_at, point is not None)
        decision = self.resolver.update(
            gaze, checked, now=now, input_screen=self.screen, enabled=True
        )
        if decision.target is None:
            self.outline.hide()
        else:
            expires = min(
                now + OUTLINE_SECONDS,
                captured_at + CONFIG.max_gaze_age,
                checked.checked_at + CONTEXT_AGE,
                checked.snapshot.captured_at + CONFIG.max_snapshot_age,
            )
            self.outline.show(decision.target.rect, expires)
        return {"semantic_status": decision.status, "semantic_feed_status": self.feed.status}

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.active = False
        self.resolver.reset()
        try:
            self.outline.close()
        finally:
            stopped = self.feed.close()
            if not stopped:
                print(
                    "Semantic discovery is still finishing a native call; preview is closed.",
                    flush=True,
                )


def create_macos_preview(size):
    # No native resource starts until activate() after the user's Tab.
    from eye_tracker.platform_adapters.macos_accessibility import MacOSAccessibility
    from eye_tracker.platform_adapters.macos_outline import MacOSOutline

    return LiveSemanticPreview(
        PreviewFeed(MacOSAccessibility()), MacOSOutline(size), TargetRect(0, 0, *size)
    )
