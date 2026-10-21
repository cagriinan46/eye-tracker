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


@pytest.mark.parametrize("cycle", [False, True])
def test_unresolved_competitor_discards_previously_verified_target(cycle):
    backend = Backend()
    backend.tree["window"] = ["button", "second"]
    backend.info["second"] = ("AXButton", TargetRect(70, 20, 40, 40), True, ("AXPress",))
    backend.hit_test = lambda x, y: "button" if x < 60 else "label"
    backend.parents = {"label": "parent", "parent": "label" if cycle else "second"}
    result = collect(backend, max_depth=2)
    assert result.status == "incomplete"
    assert result.targets == ()


def test_default_scan_reaches_control_through_deep_ui_wrappers():
    backend = Backend()
    nodes = [f"group-{n}" for n in range(30)]
    backend.tree["window"] = [nodes[0]]
    for index, node in enumerate(nodes):
        backend.info[node] = ("AXGroup", None, None, ())
        backend.tree[node] = [nodes[index + 1]] if index + 1 < len(nodes) else ["button"]
    result = MacOSAccessibility(backend=backend, clock=lambda: 1).snapshot()
    assert result.status == "ok"
    assert len(result.targets) == 1


def test_default_scan_completes_large_tree_before_offering_target():
    backend = Backend()
    groups = [f"group-{n}" for n in range(19)]
    backend.tree["window"] = groups
    for group in groups:
        backend.info[group] = ("AXGroup", None, None, ())
        leaves = [f"{group}-leaf-{n}" for n in range(30)]
        backend.tree[group] = leaves
        for leaf in leaves:
            backend.info[leaf] = ("AXStaticText", None, None, ())
    backend.tree[groups[-1]].append("button")
    result = MacOSAccessibility(backend=backend, clock=lambda: 1).snapshot()
    assert result.status == "ok"
    assert len(result.targets) == 1


def test_session_retains_context_until_exit_then_rejects_use():
    backend = Backend()
    provider = MacOSAccessibility(backend=backend)
    with provider.session() as session:
        assert session.snapshot.status == "ok"
        assert not backend.closed
        assert session.current_context() == session.snapshot.context_id
    assert backend.closed
    assert session.current_context() is None


@pytest.mark.parametrize("change", ["window", "screen", "permission"])
def test_session_invalidates_permanently_on_context_change(change):
    backend = Backend()
    with MacOSAccessibility(backend=backend).session() as session:
        original_screen = backend.screen
        if change == "window":
            backend.changed = True
        elif change == "screen":
            backend.screen = lambda: TargetRect(0, 0, 2000, 800)
        else:
            backend.permission = False
        assert session.current_context() is None
        backend.changed = False
        backend.screen = original_screen
        backend.permission = True
        assert session.current_context() is None
    assert backend.closed


def test_failed_discovery_session_never_offers_context():
    backend = Backend()
    backend.truncated = True
    with MacOSAccessibility(backend=backend).session() as session:
        assert session.snapshot.status == "incomplete"
        assert session.current_context() is None
    assert backend.closed


def test_hashed_visited_lookup_avoids_quadratic_equality_work():
    backend = Backend()
    groups = [f"group-{n}" for n in range(20)]
    backend.tree["window"] = groups
    for group in groups:
        backend.info[group] = ("AXGroup", None, None, ())
        backend.tree[group] = [f"{group}-{n}" for n in range(30)]
        for leaf in backend.tree[group]:
            backend.info[leaf] = ("AXStaticText", None, None, ())
    calls = []
    backend.identity_hash = hash
    backend.same = lambda a, b: calls.append((a, b)) or a == b
    result = MacOSAccessibility(backend=backend, clock=lambda: 1).snapshot()
    assert result.status == "ok"
    assert len(calls) < 1000


def test_hash_collision_keeps_distinct_targets_and_cycle_terminates():
    backend = Backend()
    backend.identity_hash = lambda node: 0
    backend.tree["window"] = ["button", "other", "window"]
    backend.info["other"] = ("AXButton", TargetRect(100, 20, 40, 40), True, ("AXPress",))
    backend.hit_test = lambda x, y: "other" if x > 80 else "button"
    result = collect(backend)
    assert result.status == "ok"
    assert len(result.targets) == 2
    assert len({t.target_id for t in result.targets}) == 2


def test_equal_aliases_deduplicate_by_native_equality_not_python_identity():
    backend = Backend()
    backend.tree["window"] = ["button", "alias"]
    backend.identity_hash = lambda node: 1 if node in {"button", "alias"} else 0
    backend.same = lambda a, b: a == b or {a, b} == {"button", "alias"}
    # No describe data for alias: equality must suppress traversal of it.
    result = collect(backend)
    assert result.status == "ok" and len(result.targets) == 1


def test_colliding_hashes_do_not_bypass_node_cap():
    backend = Backend()
    backend.identity_hash = lambda node: 0
    result = collect(backend, max_nodes=1)
    assert result.status == "incomplete" and result.targets == ()


def test_default_scan_covers_measured_thousand_node_ui():
    backend = Backend()
    backend.identity_hash = hash
    groups = [f"group-{n}" for n in range(34)]
    backend.tree["window"] = groups
    for group in groups:
        backend.info[group] = ("AXGroup", None, None, ())
        backend.tree[group] = [f"{group}-{n}" for n in range(38)]
        for leaf in backend.tree[group]:
            backend.info[leaf] = ("AXStaticText", None, None, ())
    backend.tree[groups[-1]].append("button")
    result = MacOSAccessibility(backend=backend, clock=lambda: 1).snapshot()
    assert result.status == "ok" and len(result.targets) == 1


def test_session_refresh_preserves_native_identity_but_not_position_only():
    backend = Backend()
    backend.identity_hash = lambda node: 0  # Collisions never prove identity.
    with MacOSAccessibility(backend=backend).session() as session:
        first = session.snapshot.targets[0]
        assert first.continuity_id
        first_snapshot_id = session.snapshot.snapshot_id
        second = session.refresh()
        assert second.snapshot_id != first_snapshot_id
        assert second.targets[0].continuity_id == first.continuity_id
        backend.tree["window"] = ["replacement"]
        backend.info["replacement"] = backend.info["button"]
        backend.hit = "replacement"
        third = session.refresh()
        assert third.targets[0].rect == first.rect
        assert third.targets[0].continuity_id != first.continuity_id


def test_session_does_not_bridge_target_disappearance():
    backend = Backend()
    with MacOSAccessibility(backend=backend).session() as session:
        token = session.snapshot.targets[0].continuity_id
        backend.tree["window"] = []
        assert session.refresh().targets == ()
        backend.tree["window"] = ["button"]
        assert session.refresh().targets[0].continuity_id != token


def test_refresh_failure_invalidates_session_and_tokens():
    backend = Backend()
    with MacOSAccessibility(backend=backend).session() as session:
        backend.truncated = True
        assert session.refresh().status == "incomplete"
        backend.truncated = False
        assert session.current_context() is None
        assert session.refresh() is None


def test_native_session_scan_and_time_bounds():
    backend = Backend()
    now = [1]
    with MacOSAccessibility(backend=backend, clock=lambda: now[0]).session() as session:
        for _ in range(3):
            assert session.refresh().status == "ok"
        assert session.refresh() is None
        assert session.current_context() is None
    with MacOSAccessibility(backend=Backend(), clock=lambda: now[0]).session() as session:
        now[0] = 3.01
        assert session.current_context() is None
        assert session.refresh() is None


def test_one_shot_does_not_claim_cross_snapshot_identity():
    assert collect(Backend()).targets[0].continuity_id is None


@pytest.mark.parametrize(
    "change", ["geometry", "role", "disabled", "occluded", "context", "screen"]
)
def test_session_refresh_requires_unchanged_visible_control_and_context(change):
    backend = Backend()
    with MacOSAccessibility(backend=backend).session() as session:
        first = session.snapshot.targets[0].continuity_id
        role, rect, enabled, actions = backend.info["button"]
        if change == "geometry":
            rect = TargetRect(21, 20, 40, 40)
        elif change == "role":
            role = "AXCheckBox"
        elif change == "disabled":
            enabled = False
        elif change == "occluded":
            backend.hit = None
        elif change == "context":
            backend.changed = True
        elif change == "screen":
            backend.screen = lambda: TargetRect(0, 0, 800, 600)
        backend.info["button"] = role, rect, enabled, actions
        result = session.refresh()
        if change in {"context", "screen"}:
            assert result is None and session.current_context() is None
        elif change in {"disabled", "occluded"}:
            assert result.targets == ()
        else:
            assert result.targets[0].continuity_id != first


def test_native_alias_across_scans_keeps_identity_and_exit_invalidates():
    backend = Backend()
    backend.identity_hash = lambda node: 0
    backend.same = lambda a, b: a == b or {a, b} == {"button", "alias"}
    with MacOSAccessibility(backend=backend).session() as session:
        token = session.snapshot.targets[0].continuity_id
        backend.tree["window"] = ["alias"]
        backend.info["alias"] = backend.info["button"]
        backend.hit = "alias"
        assert session.refresh().targets[0].continuity_id == token
    assert backend.closed
    assert session.refresh() is None
