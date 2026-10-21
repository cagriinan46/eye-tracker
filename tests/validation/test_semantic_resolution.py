import json

from validation.semantic_resolution import main, run_comparison


def test_comparison_counts_and_known_tradeoffs():
    report = run_comparison()
    assert report["synthetic_only"] is True
    scenarios = report["scenarios"]
    assert set(scenarios) == {
        "isolated_offset",
        "dense_boundary",
        "nested_overlap",
        "tracking_loss",
    }
    for scenario in scenarios.values():
        assert set(scenario["methods"]) == {"coordinate", "nearest", "conservative"}
        for metrics in scenario["methods"].values():
            assert (
                metrics["correct"] + metrics["wrong"] + metrics["abstentions"]
                == scenario["samples"]
            )
    isolated = scenarios["isolated_offset"]["methods"]
    assert isolated["coordinate"]["correct"] == 0
    assert isolated["nearest"]["correct"] == 5
    assert isolated["conservative"]["correct"] == 3
    assert isolated["conservative"]["first_correct_seconds"] == 0.12
    dense = scenarios["dense_boundary"]["methods"]
    assert dense["nearest"]["wrong"] > 0
    assert dense["nearest"]["switches"] > 0
    assert dense["conservative"]["abstentions"] == 5
    assert dense["conservative"]["first_correct_seconds"] is None
    assert scenarios["nested_overlap"]["methods"]["conservative"]["abstentions"] == 5
    assert scenarios["tracking_loss"]["methods"]["conservative"]["correct"] == 1


def test_json_command(capsys):
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == run_comparison()
