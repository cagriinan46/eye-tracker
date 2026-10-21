"""Bounded one-shot discovery. Not a camera-loop service or an action adapter."""

from collections import deque
from dataclasses import dataclass
from math import isfinite
from time import monotonic
from uuid import uuid4

from eye_tracker.intent.targets import TargetRect, UISnapshot, UITarget
from eye_tracker.platform_adapters._macos_ax import (
    SUPPORTED_ROLES,
    AXBackend,
    AXEmptyTarget,
    AXReadError,
    AXUnavailable,
    UnsupportedCoordinates,
)


@dataclass(frozen=True, slots=True)
class DiscoveryLimits:
    max_nodes: int = 1024
    max_depth: int = 64
    max_children: int = 128
    seconds: float = 0.5
    message_timeout: float = 0.05

    def __post_init__(self):
        if any(
            type(v) is not int or v <= 0
            for v in (self.max_nodes, self.max_depth, self.max_children)
        ):
            raise ValueError("traversal limits must be positive integers")
        if any(not isfinite(v) or v <= 0 for v in (self.seconds, self.message_timeout)):
            raise ValueError("time limits must be finite and positive")


def _intersection(a, b):
    x, y = max(a.x, b.x), max(a.y, b.y)
    right, bottom = min(a.x + a.width, b.x + b.width), min(a.y + a.height, b.y + b.height)
    return TargetRect(x, y, right - x, bottom - y) if right > x and bottom > y else None


class MacOSAccessibility:
    def __init__(self, backend=None, limits=None, clock=monotonic):
        self.backend = backend
        self.limits = limits or DiscoveryLimits()
        self.clock = clock

    def snapshot(self):
        start = self.clock()
        identity = uuid4().hex
        context = screen = None

        def result(status, targets=()):
            return UISnapshot(identity, start, context, screen, tuple(targets), status)

        def budget():
            now = self.clock()
            if not isfinite(now) or now < start or now - start >= self.limits.seconds:
                raise AXReadError("discovery time budget exhausted")

        backend = (
            self.backend if self.backend is not None else AXBackend(self.limits.message_timeout)
        )
        try:
            with backend as native:
                if not native.trusted():
                    return result("unavailable")
                context = native.context()
                if context is None:
                    return result("unavailable")
                screen = native.screen()
                queue = deque((root, 0, screen) for root in native.roots())
                if not queue:
                    return result("unavailable")
                seen, targets = [], []
                while queue:
                    budget()
                    node, depth, clip = queue.popleft()
                    if any(native.same(node, old) for old in seen):
                        continue
                    if len(seen) >= self.limits.max_nodes:
                        raise AXReadError("node cap")
                    seen.append(node)
                    try:
                        role, rect, enabled, actions = native.describe(node)
                    except AXEmptyTarget as empty:
                        # A zero-area control cannot be a target. Its children
                        # can still have valid geometry, so keep traversing them.
                        role, rect, enabled, actions = empty.role, None, None, ()
                    # Menus need a separate open-menu lifecycle; never descend into
                    # application menu contents merely because AX advertises them.
                    if role == "AXMenu":
                        continue
                    if role in {"AXWindow", "AXMenuBar"}:
                        if rect is None:
                            raise AXReadError("missing root geometry")
                        clip = _intersection(clip, rect)
                        if clip is None:
                            continue
                    if role in SUPPORTED_ROLES and "AXPress" in actions:
                        if enabled is None or (enabled and rect is None):
                            raise AXReadError("missing target geometry or enabled state")
                        visible = _intersection(clip, rect) if enabled and rect else None
                        if visible:
                            budget()
                            hit = native.hit_test(*visible.center)
                            parents = []
                            for _ in range(self.limits.max_depth):
                                budget()
                                if hit is None:
                                    break
                                if any(native.same(hit, old) for old in parents):
                                    raise AXReadError("cyclic hit-test ancestry")
                                if native.same(hit, node):
                                    targets.append(
                                        UITarget(str(len(seen)), role, visible, True, "press")
                                    )
                                    break
                                parents.append(hit)
                                hit = native.parent(hit)
                            else:
                                if hit is not None:
                                    raise AXReadError("hit-test ancestry cap")
                    budget()
                    children, truncated = native.children(node, self.limits.max_children)
                    if truncated or (children and depth >= self.limits.max_depth):
                        raise AXReadError("child or depth cap")
                    if len(queue) + len(children) > self.limits.max_nodes:
                        raise AXReadError("queue cap")
                    queue.extend((child, depth + 1, clip) for child in children)
                budget()
                if native.context() != context:
                    return result("context_changed")
                budget()
                return result("ok", targets)
        except UnsupportedCoordinates:
            return result("unsupported_coordinates")
        except AXUnavailable:
            return result("unavailable")
        except AXReadError:
            return result("incomplete")
