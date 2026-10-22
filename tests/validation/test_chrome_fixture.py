from collections import Counter

import pytest

from validation import chrome_fixture as fixture


class Clock:
    value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


def observation(status="ok", signature=("same",)):
    return fixture.Observation(status, signature)


def run_gate(values, **kwargs):
    clock = Clock()
    samples = iter(values)
    return fixture.wait_ready(lambda: next(samples), clock=clock, sleep=clock.sleep, **kwargs)


def test_incomplete_and_missing_targets_reset_consecutive_readiness():
    report = run_gate(
        [
            observation(),
            observation(),
            observation("incomplete"),
            observation(),
            observation("missing_targets"),
            observation(),
            observation(),
            observation(),
        ]
    )
    assert report["status"] == "ready"
    assert len(report["attempts"]) == 8
    assert [r["streak"] for r in report["attempts"]] == [1, 2, 0, 1, 0, 1, 2, 3]


def test_changed_geometry_restarts_streak():
    report = run_gate(
        [
            observation(),
            observation(),
            observation(signature=("moved",)),
            observation(signature=("moved",)),
            observation(signature=("moved",)),
        ]
    )
    assert report["status"] == "ready"
    assert len(report["attempts"]) == 5
    assert "moved" not in str(report)  # geometry is not persisted


@pytest.mark.parametrize("status", ["context_changed", "unavailable", "unsupported_coordinates"])
def test_terminal_failure_does_not_retry(status):
    report = run_gate([observation(), observation(status)])
    assert report["status"] == status
    assert len(report["attempts"]) == 2


def test_timeout_does_not_accept_late_success():
    clock = Clock()

    def scan():
        clock.value += 1
        return observation()

    report = fixture.wait_ready(scan, clock=clock, sleep=clock.sleep, seconds=2)
    assert report["status"] == "timeout"


def test_attempt_limit_stops_persistent_incomplete():
    report = run_gate([observation("incomplete")] * 4, max_attempts=4)
    assert report["status"] == "attempt_limit"
    assert len(report["attempts"]) == 4


def test_only_exact_fixture_roles_count():
    expected = Counter(
        {"AXButton": 1, "AXLink": 1, "AXCheckBox": 1, "AXRadioButton": 1, "AXPopUpButton": 1}
    )
    assert fixture.matches_fixture(expected)
    assert not fixture.matches_fixture(Counter({"AXButton": 5}))
    assert not fixture.matches_fixture(expected + Counter({"AXButton": 1}))


def test_failed_readiness_never_launches_preview():
    launches = []
    assert fixture.launch_preview({"status": "timeout"}, True, lambda: launches.append(1)) is None
    assert fixture.launch_preview({"status": "ready"}, False, lambda: launches.append(1)) is None
    assert launches == []
    fixture.launch_preview({"status": "ready"}, True, lambda: launches.append(1))
    assert launches == [1]


def test_web_ancestry_excludes_toolbar_targets(monkeypatch):
    from eye_tracker.intent.targets import TargetRect

    backend = fixture.FixtureBackend.__new__(fixture.FixtureBackend)
    backend.web, backend.selected = set(), []
    monkeypatch.setattr(
        fixture.AXBackend,
        "describe",
        lambda self, node: ("AXWebArea" if node == "web" else "AXGroup", None, None, ()),
    )
    monkeypatch.setattr(
        fixture.AXBackend,
        "children",
        lambda self, node, limit: (
            ("page_button",) if node == "web" else ("toolbar_button",),
            False,
        ),
    )
    backend.describe("web")
    backend.children("web", 128)
    backend.children("toolbar", 128)
    rect = TargetRect(0, 0, 40, 40)
    backend.identity("toolbar_button", "AXButton", rect)
    backend.identity("page_button", "AXButton", rect)
    assert backend.selected == [("AXButton", 0, 0, 40, 40)]


def test_partial_verified_targets_cannot_pass_incomplete_scan(monkeypatch):
    from types import SimpleNamespace

    backend = fixture.FixtureBackend.__new__(fixture.FixtureBackend)
    backend.web, backend.selected, backend.initial_context = set(), [], None
    monkeypatch.setattr(backend, "_frontmost_pid", lambda: 1)
    monkeypatch.setattr(backend, "create_application", lambda pid: "app", raising=False)
    monkeypatch.setattr(backend, "_own", lambda node: node)
    monkeypatch.setattr(backend, "_attr", lambda node, name: None)

    class Scanner:
        def __init__(self, **kwargs):
            pass

        def snapshot(self, **kwargs):
            backend.selected.extend((role, 0, 0, 40, 40) for role in fixture.EXPECTED)
            return SimpleNamespace(status="incomplete")

    monkeypatch.setattr(fixture, "MacOSAccessibility", Scanner)
    sample = backend.observe()
    assert sample.status == "incomplete"
    assert sample.signature == ()


def test_cleanup_only_terminates_owned_live_process():
    class Process:
        running = True
        terminated = False

        def poll(self):
            return None if self.running else 0

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            self.running = False

    process = Process()
    fixture.stop_owned(process)
    assert not process.running
    process.terminated = False
    fixture.stop_owned(process)
    assert not process.terminated


@pytest.mark.parametrize("trusted, expected", [(True, "incomplete"), (False, "unavailable")])
def test_initial_window_absence_retries_only_with_permission(monkeypatch, trusted, expected):
    from types import SimpleNamespace

    backend = fixture.FixtureBackend.__new__(fixture.FixtureBackend)
    backend.web, backend.selected, backend.initial_context = set(), [], None
    monkeypatch.setattr(backend, "_frontmost_pid", lambda: 1)
    monkeypatch.setattr(backend, "create_application", lambda pid: "app", raising=False)
    monkeypatch.setattr(backend, "_own", lambda node: node)
    monkeypatch.setattr(backend, "_attr", lambda node, name: None)
    monkeypatch.setattr(backend, "trusted", lambda: trusted, raising=False)
    monkeypatch.setattr(
        fixture,
        "MacOSAccessibility",
        lambda **kw: SimpleNamespace(snapshot=lambda **kw: SimpleNamespace(status="unavailable")),
    )
    assert backend.observe().status == expected


def test_focus_restore_preserves_user_switch():
    assert fixture.should_restore_focus(42, (42, 43))
    assert not fixture.should_restore_focus(99, (42, 43))
    assert not fixture.should_restore_focus(None, (42, None))
