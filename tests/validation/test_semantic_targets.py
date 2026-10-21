import json

import pytest

from eye_tracker.intent.targets import TargetRect, UISnapshot, UITarget
from validation.semantic_targets import main


@pytest.mark.parametrize(
    "status", ["ok", "unavailable", "incomplete", "context_changed", "unsupported_coordinates"]
)
def test_cli_summary_and_exit_codes(status, capsys):
    rect = TargetRect(0, 0, 100, 100)
    target = UITarget("private-id", "AXButton", rect, True, "press")
    snapshot = UISnapshot(
        "private-snapshot", 1, "private-context", rect, (target,) if status == "ok" else (), status
    )

    class Provider:
        def snapshot(self):
            return snapshot

    assert main([], provider=Provider()) == (0 if status == "ok" else 2)
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status"] == status
    assert result["target_count"] == (1 if status == "ok" else 0)
    assert result["roles"] == ({"AXButton": 1} if status == "ok" else {})
    assert "private-" not in output and "rect" not in output


def test_empty_complete_scan_is_success(capsys):
    class Provider:
        def snapshot(self):
            return UISnapshot("s", 1, "c", TargetRect(0, 0, 1, 1), (), "ok")

    assert main([], provider=Provider()) == 0
    assert json.loads(capsys.readouterr().out)["target_count"] == 0


def test_help_does_not_create_native_backend(monkeypatch, capsys):
    import validation.semantic_targets as cli

    monkeypatch.setattr(
        cli, "MacOSAccessibility", lambda **kwargs: pytest.fail("native initialization")
    )
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
