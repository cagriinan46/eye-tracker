"""Read-only preview preparation. No GUI, camera, native calls or actions here."""

from dataclasses import dataclass
from math import isfinite
from threading import Event, Lock, Thread
from time import monotonic

from eye_tracker.intent.targeting import GazePoint, TargetDecision, TargetingConfig, TargetResolver
from eye_tracker.intent.targets import TargetRect, UISnapshot


def _positive(value):
    if not isfinite(value) or value <= 0:
        raise ValueError("timing limits must be finite and positive")


@dataclass(frozen=True, slots=True)
class CheckedSnapshot:
    snapshot: UISnapshot
    checked_at: float
    context_id: str


class PreviewFeed:
    """One worker owns native sessions; consumers only read immutable values.

    Native timeouts are cooperative. close() clears publication immediately and
    returns whether the worker actually stopped within the requested join bound.
    A blocked worker is a daemon; never start another worker to replace it in place.
    """

    def __init__(self, provider, *, refresh_seconds=0.4, check_seconds=0.05, clock=monotonic):
        _positive(refresh_seconds)
        _positive(check_seconds)
        self.provider = provider
        self.refresh_seconds = refresh_seconds
        self.check_seconds = check_seconds
        self.clock = clock
        self._lock = Lock()
        self._stop = Event()
        self._thread = None
        self._latest = None
        self._status = "idle"

    @property
    def status(self):
        with self._lock:
            return self._status

    def start(self):
        with self._lock:
            if self._thread is not None or self._stop.is_set():
                raise RuntimeError("feed is single-use")
            self._thread = Thread(target=self._run, name="semantic-preview-feed", daemon=True)
            self._thread.start()

    def latest(self) -> CheckedSnapshot | None:
        with self._lock:
            value = self._latest
        now = self.clock()
        if value is None or not isfinite(now):
            return None
        if not 0 <= now - value.snapshot.captured_at <= self.refresh_seconds:
            return None
        return value

    def close(self, timeout=0.1) -> bool:
        if not isfinite(timeout) or timeout < 0:
            raise ValueError("join timeout must be finite and nonnegative")
        with self._lock:
            self._stop.set()
            self._latest = None
            self._status = "closed"
            thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return thread is None or not thread.is_alive()

    def _publish(self, value, status):
        with self._lock:
            if not self._stop.is_set():
                self._latest = value
                self._status = status

    def _run(self):
        try:
            while not self._stop.is_set():
                self._publish(None, "scanning")
                with self.provider.session() as session:
                    snapshot = session.snapshot
                    while not self._stop.is_set():
                        started = self.clock()
                        if (
                            snapshot.status != "ok"
                            or not isfinite(started)
                            or not 0 <= started - snapshot.captured_at < self.refresh_seconds
                        ):
                            self._publish(None, "unavailable")
                            break
                        context = session.current_context()
                        finished = self.clock()
                        if (
                            context != snapshot.context_id
                            or not isfinite(finished)
                            or finished < started
                            or finished - snapshot.captured_at >= self.refresh_seconds
                        ):
                            self._publish(None, "unavailable")
                            break
                        self._publish(CheckedSnapshot(snapshot, started, context), "ready")
                        if self._stop.wait(self.check_seconds):
                            break
                self._publish(None, "scanning")
                self._stop.wait(self.check_seconds)
        except Exception:
            # Never log native/UI details. Failure is explicit and terminal; the
            # owner may inspect status and close rather than retrying invisibly.
            self._publish(None, "failed")


class SemanticPreview:
    """Opt-in coordinator; caller must prove exact logical coordinate agreement."""

    def __init__(self, config: TargetingConfig, *, max_context_age: float):
        _positive(max_context_age)
        self.max_context_age = max_context_age
        self._resolver = TargetResolver(config)

    def reset(self):
        self._resolver.reset()

    def update(
        self,
        gaze: GazePoint,
        checked: CheckedSnapshot | None,
        *,
        now: float,
        input_screen: TargetRect,
        enabled: bool = False,
    ) -> TargetDecision:
        if (
            enabled is not True
            or checked is None
            or not isfinite(now)
            or not isfinite(checked.checked_at)
            or not checked.snapshot.captured_at <= checked.checked_at <= now
            or now - checked.checked_at > self.max_context_age
            or checked.context_id != checked.snapshot.context_id
            or input_screen != checked.snapshot.screen
        ):
            self.reset()
            return TargetDecision("unavailable_context")
        return self._resolver.update(gaze, checked.snapshot, now=now, context_id=checked.context_id)
