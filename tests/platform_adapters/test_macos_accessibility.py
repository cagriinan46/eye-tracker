import pytest

from eye_tracker.intent.targets import TargetRect
from eye_tracker.platform_adapters.macos_accessibility import DiscoveryLimits, MacOSAccessibility


class Backend:
    def __init__(self):
        self.closed = False
        self.permission = True
        self.changed = False
        self.calls = 0
        self.tree = {"window": ["button"], "button": []}
        self.info = {
            "window": ("AXWindow", TargetRect(0, 0, 500, 500), None, ()),
            "button": ("AXButton", TargetRect(20, 20, 40, 40), True, ("AXPress",)),
        }
        self.hit = "button"
        self.parents = {}
        self.truncated = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def trusted(self):
        return self.permission

    def context(self):
        self.calls += 1
        return "changed" if self.changed and self.calls > 1 else "context"

    def screen(self):
        return TargetRect(0, 0, 1000, 800)

    def roots(self):
        return ("window",)

    def children(self, node, limit):
        values = self.tree.get(node, [])
        return tuple(values[:limit]), self.truncated or len(values) > limit

    def describe(self, node):
        return self.info[node]

    def hit_test(self, x, y):
        return self.hit

    def parent(self, node):
        return self.parents.get(node)

    def same(self, a, b):
        return a == b


def collect(backend, **limits):
    return MacOSAccessibility(backend=backend, limits=DiscoveryLimits(**limits)).snapshot()


def test_complete_target_and_cleanup():
    backend = Backend()
    result = collect(backend)
    assert result.status == "ok"
    assert len(result.targets) == 1
    assert result.targets[0].rect.center == (40, 40)
    assert backend.closed


def test_permission_denial_does_not_read_context():
    backend = Backend()
    backend.permission = False
    assert collect(backend).status == "unavailable"
    assert backend.calls == 0 and backend.closed


@pytest.mark.parametrize("kind", ["disabled", "occluded", "offscreen", "unknown_role", "no_action"])
def test_ineligible_targets_not_offered(kind):
    backend = Backend()
    role, rect, enabled, actions = backend.info["button"]
    if kind == "disabled":
        enabled = False
    if kind == "occluded":
        backend.hit = "other"
    if kind == "offscreen":
        rect = TargetRect(900, 900, 50, 50)
    if kind == "unknown_role":
        role = "AXUnknown"
    if kind == "no_action":
        actions = ()
    backend.info["button"] = role, rect, enabled, actions
    assert collect(backend).targets == ()


def test_verified_descendant_hit_and_ancestry_bound():
    backend = Backend()
    backend.hit = "label"
    backend.parents["label"] = "button"
    assert len(collect(backend).targets) == 1
    backend = Backend()
    backend.hit = "a"
    backend.parents.update(a="b", b="c", c="button")
    assert collect(backend, max_depth=2).targets == ()


@pytest.mark.parametrize("limits", [{"max_nodes": 1}, {"max_depth": 1}, {"max_children": 1}])
def test_caps_discard_all_targets(limits):
    backend = Backend()
    backend.tree["button"] = ["child", "child2"]
    backend.info.update(child=backend.info["button"], child2=backend.info["button"])
    result = collect(backend, **limits)
    assert result.status == "incomplete" and not result.targets
    assert backend.closed


def test_truncation_and_context_change_discard_targets():
    backend = Backend()
    backend.truncated = True
    assert collect(backend).status == "incomplete"
    backend = Backend()
    backend.changed = True
    result = collect(backend)
    assert result.status == "context_changed" and not result.targets


def test_cycles_terminate_and_closed_menus_are_skipped():
    backend = Backend()
    backend.tree["button"] = ["window"]
    assert collect(backend).status == "ok"
    backend = Backend()
    backend.tree["window"] = ["menu"]
    backend.info["menu"] = ("AXMenu", None, None, ("AXPress",))
    backend.tree["menu"] = ["must-not-read"]
    assert collect(backend).targets == ()


def test_missing_required_state_is_incomplete():
    backend = Backend()
    role, rect, _, actions = backend.info["button"]
    backend.info["button"] = role, rect, None, actions
    assert collect(backend).status == "incomplete"


def test_timeout_discards_partial_results():
    backend = Backend()
    ticks = iter([0, 0, 0, 1, 1, 1, 1])
    result = MacOSAccessibility(backend=backend, clock=lambda: next(ticks)).snapshot()
    assert result.status == "incomplete" and not result.targets
    assert backend.closed


def test_rect_is_clipped_to_window():
    backend = Backend()
    backend.info["button"] = ("AXButton", TargetRect(480, 20, 40, 40), True, ("AXPress",))
    assert collect(backend).targets[0].rect == TargetRect(480, 20, 20, 40)


@pytest.mark.parametrize(
    "kwargs",
    [{"max_nodes": 0}, {"seconds": float("nan")}, {"message_timeout": -1}, {"max_depth": 1.5}],
)
def test_invalid_limits(kwargs):
    with pytest.raises(ValueError):
        DiscoveryLimits(**kwargs)
