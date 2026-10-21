"""Immutable UI geometry; no native APIs or activation semantics."""

from dataclasses import dataclass
from math import hypot, isfinite


@dataclass(frozen=True, slots=True)
class TargetRect:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        if (
            not all(
                isfinite(v)
                for v in (
                    self.x,
                    self.y,
                    self.width,
                    self.height,
                    self.x + self.width,
                    self.y + self.height,
                )
            )
            or self.width <= 0
            or self.height <= 0
        ):
            raise ValueError("rectangle must have finite coordinates and positive size")

    @property
    def center(self):
        return self.x + self.width / 2, self.y + self.height / 2

    def distance_to(self, x, y):
        if not isfinite(x) or not isfinite(y):
            raise ValueError("point must be finite")
        return hypot(
            max(self.x - x, 0, x - self.x - self.width),
            max(self.y - y, 0, y - self.y - self.height),
        )


@dataclass(frozen=True, slots=True)
class UITarget:
    target_id: str
    role: str
    rect: TargetRect
    enabled: bool
    category: str
    continuity_id: str | None = None

    def __post_init__(self):
        if self.continuity_id is not None and (
            not isinstance(self.continuity_id, str) or not self.continuity_id
        ):
            raise ValueError("continuity identity must be a nonempty string or None")
        if not self.target_id or not self.role or not self.category:
            raise ValueError("target identity, role and category are required")
        if not isinstance(self.rect, TargetRect) or type(self.enabled) is not bool:
            raise TypeError("target requires a rectangle and boolean enabled state")


@dataclass(frozen=True, slots=True)
class UISnapshot:
    snapshot_id: str
    captured_at: float
    context_id: str | None
    screen: TargetRect | None
    targets: tuple[UITarget, ...]
    status: str

    def __post_init__(self):
        if not self.snapshot_id or not isfinite(self.captured_at) or self.captured_at < 0:
            raise ValueError("snapshot requires identity and nonnegative finite time")
        if self.status not in {
            "ok",
            "unavailable",
            "incomplete",
            "context_changed",
            "unsupported_coordinates",
        }:
            raise ValueError("unknown snapshot status")
        if not isinstance(self.targets, tuple) or any(
            not isinstance(t, UITarget) for t in self.targets
        ):
            raise TypeError("targets must be an immutable tuple of UITarget")
        if self.screen is not None and not isinstance(self.screen, TargetRect):
            raise TypeError("screen must be a TargetRect or None")
        if self.status != "ok" and self.targets:
            raise ValueError("failed snapshots cannot carry selectable targets")
        if self.status == "ok" and (not self.context_id or self.screen is None):
            raise ValueError("complete snapshot requires context and screen")
        if len({t.target_id for t in self.targets}) != len(self.targets):
            raise ValueError("duplicate target identities")
        tokens = [t.continuity_id for t in self.targets if t.continuity_id is not None]
        if len(set(tokens)) != len(tokens):
            raise ValueError("duplicate continuity identities")
