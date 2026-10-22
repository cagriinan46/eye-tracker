"""Bounded one-shot discovery. Not a camera-loop service or an action adapter."""

from collections import deque
from contextlib import contextmanager, nullcontext
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
    max_nodes: int = 2048
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

    @contextmanager
    def session(self):
        """Thread-confined, ephemeral native references for context revalidation.

        Consumers receive only immutable values; never share this session across
        threads or retain it after exit. Existing one-shot snapshot() is unchanged.
        """
        backend = (
            self.backend if self.backend is not None else AXBackend(self.limits.message_timeout)
        )
        with backend as native:
            scanner = MacOSAccessibility(
                backend=nullcontext(native), limits=self.limits, clock=self.clock
            )
            session = _DiscoverySession(native, scanner, self.clock)
            try:
                yield session
            finally:
                session.close()

    def snapshot(self, *, _identity=None):
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
                seen, targets = {}, []
                seen_count = 0
                # CFHash only narrows equality comparisons; collisions must not
                # hide competitors. Backends without hashing retain full equality.
                identity_hash = getattr(native, "identity_hash", lambda node: 0)
                while queue:
                    budget()
                    node, depth, clip = queue.popleft()
                    bucket = seen.setdefault(identity_hash(node), [])
                    if any(native.same(node, old) for old in bucket):
                        continue
                    if seen_count >= self.limits.max_nodes:
                        raise AXReadError("node cap")
                    bucket.append(node)
                    seen_count += 1
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
                        if enabled is not False and rect is None:
                            raise AXReadError("missing target geometry or enabled state")
                        visible = (
                            _intersection(clip, rect) if enabled is not False and rect else None
                        )
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
                                        UITarget(
                                            str(seen_count),
                                            role,
                                            visible,
                                            enabled,
                                            "preview_only" if enabled is None else "press",
                                            _identity(node, role, visible) if _identity else None,
                                        )
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


class _DiscoverySession:
    """At most four scans / two seconds of native references and identity evidence."""

    def __init__(self, native, scanner, clock):
        self._native = native
        self._scanner = scanner
        self._clock = clock
        self._started = clock()
        self._scans = 0
        self._previous = {}
        self.snapshot = None
        self.refresh()

    def close(self):
        self._native = None
        self._previous.clear()

    def _alive(self):
        now = self._clock()
        if self._native is not None and isfinite(now) and 0 <= now - self._started < 2:
            return True
        self.close()
        return False

    def refresh(self):
        if not self._alive() or self._scans >= 4:
            self.close()
            return None
        if self.snapshot is not None and self.current_context() is None:
            return None
        native = self._native
        current = {}
        identity_hash = getattr(native, "identity_hash", lambda node: 0)

        def identity(node, role, rect):
            # Only hit-tested press/preview-only targets reach this callback.
            # Resolver keys also include enabled/category, so state changes reset evidence.
            bucket = identity_hash(node)
            token = (
                next(
                    (
                        token
                        for old, old_role, old_rect, token in self._previous.get(bucket, ())
                        if native.same(node, old) and role == old_role and rect == old_rect
                    ),
                    None,
                )
                or uuid4().hex
            )
            current.setdefault(bucket, []).append((node, role, rect, token))
            return token

        self._scans += 1
        previous = self.snapshot
        result = self._scanner.snapshot(_identity=identity)
        self.snapshot = result
        if (
            result.status != "ok"
            or not self._alive()
            or (
                previous is not None
                and (previous.context_id != result.context_id or previous.screen != result.screen)
            )
            or self.current_context() is None
        ):
            self.close()
            if result.status == "ok":
                return None
        else:
            self._previous = current
        return result

    def current_context(self):
        if not self._alive() or self.snapshot is None or self.snapshot.status != "ok":
            return None
        native = self._native
        try:
            if (
                native.trusted()
                and native.context() == self.snapshot.context_id
                and native.screen() == self.snapshot.screen
                and native.context() == self.snapshot.context_id
                and self._alive()
            ):
                return self.snapshot.context_id
        except AXReadError:
            pass
        self.close()
        return None
