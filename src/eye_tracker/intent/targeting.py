"""Pure, non-activating target selection in the snapshot's logical coordinates.

Times must use one monotonic clock. Callers supply current context independently
of the snapshot. Only explicit provider-verified continuity can bridge snapshot replacement.
"""

from dataclasses import dataclass, fields
from math import isfinite

from eye_tracker.intent.targets import UISnapshot, UITarget


@dataclass(frozen=True, slots=True)
class TargetingConfig:
    """Explicit development thresholds; none are calibrated probabilities."""

    radius: float
    separation: float
    stable_seconds: float
    max_sample_gap: float
    max_snapshot_age: float
    max_gaze_age: float

    def __post_init__(self):
        if any(not isfinite(v := getattr(self, f.name)) or v <= 0 for f in fields(self)):
            raise ValueError("targeting thresholds must be finite and positive")


@dataclass(frozen=True, slots=True)
class GazePoint:
    x: float
    y: float
    captured_at: float
    valid: bool = True


@dataclass(frozen=True, slots=True)
class TargetDecision:
    status: str
    target: UITarget | None = None

    def __post_init__(self):
        if self.status not in {
            "candidate",
            "pending",
            "ambiguous",
            "no_nearby_target",
            "invalid_gaze",
            "invalid_time",
            "stale_snapshot",
            "unavailable_context",
        }:
            raise ValueError("unknown target decision")
        if (self.status == "candidate") != isinstance(self.target, UITarget):
            raise ValueError("only candidates carry a target")
        if self.status != "candidate" and self.target is not None:
            raise ValueError("abstentions cannot carry a target")


def _rank(gaze, snapshot, *, now, context_id, config):
    if not isfinite(now) or now < 0:
        return TargetDecision("invalid_time"), []
    if snapshot.status != "ok" or not context_id or context_id != snapshot.context_id:
        return TargetDecision("unavailable_context"), []
    if not 0 <= now - snapshot.captured_at <= config.max_snapshot_age:
        return TargetDecision("stale_snapshot"), []
    if (
        gaze.valid is not True
        or not all(isfinite(v) for v in (gaze.x, gaze.y, gaze.captured_at))
        or gaze.captured_at < 0
        or not 0 <= now - gaze.captured_at <= config.max_gaze_age
        or snapshot.screen.distance_to(gaze.x, gaze.y) != 0
    ):
        return TargetDecision("invalid_gaze"), []
    ranked = sorted(
        (
            (target.rect.distance_to(gaze.x, gaze.y), target)
            for target in snapshot.targets
            if target.enabled
            and target.category == "press"
            and snapshot.screen.distance_to(*target.rect.center) == 0
        ),
        key=lambda item: item[0],
    )
    if not ranked or ranked[0][0] > config.radius:
        return TargetDecision("no_nearby_target"), []
    return None, ranked


def select_target(
    gaze: GazePoint,
    snapshot: UISnapshot,
    *,
    now: float,
    context_id: str | None,
    config: TargetingConfig,
    method: str,
) -> TargetDecision:
    """Stateless comparison baselines; neither result is an activation intent."""
    if method not in {"coordinate", "nearest"}:
        raise ValueError("method must be coordinate or nearest")
    failure, ranked = _rank(gaze, snapshot, now=now, context_id=context_id, config=config)
    if failure:
        return failure
    if method == "coordinate" and ranked[0][0] != 0:
        return TargetDecision("no_nearby_target")
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return TargetDecision("ambiguous")
    return TargetDecision("candidate", ranked[0][1])


class TargetResolver:
    """Separated evidence; optional native-verified tokens bridge complete scans."""

    def __init__(self, config: TargetingConfig):
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._key = None
        self._started_at = None
        self._last_sample = None
        self._last_update = None
        self._last_snapshot_time = None

    def update(
        self,
        gaze: GazePoint,
        snapshot: UISnapshot,
        *,
        now: float,
        context_id: str | None,
    ) -> TargetDecision:
        failure, ranked = _rank(gaze, snapshot, now=now, context_id=context_id, config=self.config)
        if failure:
            self.reset()
            return failure
        if self._last_sample is not None and (
            gaze.captured_at <= self._last_sample
            or now <= self._last_update
            or snapshot.captured_at < self._last_snapshot_time
        ):
            self.reset()
            return TargetDecision("invalid_time")
        if len(ranked) > 1 and ranked[1][0] - ranked[0][0] < self.config.separation:
            self.reset()
            return TargetDecision("ambiguous")
        target = ranked[0][1]
        key = (
            (
                target.continuity_id,
                context_id,
                snapshot.screen,
                target.role,
                target.rect,
                target.enabled,
                target.category,
            )
            if target.continuity_id is not None
            else (snapshot, target.target_id, context_id)
        )
        if (
            key != self._key
            or gaze.captured_at - self._last_sample > self.config.max_sample_gap
            or now - self._last_update > self.config.max_sample_gap
        ):
            self._started_at = gaze.captured_at
        self._key = key
        self._last_sample = gaze.captured_at
        self._last_update = now
        self._last_snapshot_time = snapshot.captured_at
        if gaze.captured_at - self._started_at < self.config.stable_seconds:
            return TargetDecision("pending")
        return TargetDecision("candidate", target)
