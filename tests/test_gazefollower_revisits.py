from types import SimpleNamespace

import numpy as np
import pytest

from experiments.gazefollower_baseline.revisits import collect_revisits, revisit_plan

POINTS = [(i / 16, 0.5) for i in range(13)]


def test_plan_has_three_separated_visits_with_same_total_budget():
    plan = revisit_plan(POINTS)
    assert len(plan) == 40
    assert plan[0]["target_id"] is None
    assert plan[0]["samples"] == 45
    for target_id in range(1, 14):
        visits = [v for v in plan if v["target_id"] == target_id]
        assert [v["pass"] for v in visits] == [1, 2, 3]
        assert sum(v["samples"] for v in visits) == 45
        assert all(v["target"] == POINTS[target_id - 1] for v in visits)
    for a, b in zip(plan[1:], plan[2:]):
        assert a["target_id"] != b["target_id"]


def harness():
    state = SimpleNamespace(t=0.0, visit=None, onset=0.0, events=[], starts=[], polls=0)

    def begin(visit):
        state.visit = visit
        state.onset = state.t
        state.starts.append(state.t)

    buffer = np.empty(258)

    def observe():
        state.t += 0.1
        # Reusable source buffer must be copied; alternate invalid attempts.
        state.polls += 1
        buffer.fill(state.visit["visit"])
        return buffer if state.polls % 2 else None, state.t

    return state, dict(
        begin=begin,
        observe=observe,
        poll=lambda: None,
        clock=lambda: state.t,
        record=state.events.append,
    )


def test_collect_groups_passes_and_excludes_settling_rejections_and_warmup():
    state, callbacks = harness()
    plan = revisit_plan(POINTS)
    features, labels = collect_revisits(plan, **callbacks)
    assert features.shape == (13, 45, 258)
    assert labels.shape == (13, 45, 2)
    assert len(state.events) == 585
    for i in range(13):
        visits = [v["visit"] for v in plan if v["target_id"] == i + 1]
        assert features[i, :, 0].tolist() == np.repeat(visits, 15).tolist()
        assert np.all(labels[i] == np.asarray(POINTS[i], dtype=np.float32))
        events = [e for e in state.events if e["target_id"] == i + 1]
        assert [e["sample_index"] for e in events] == list(range(45))
        assert [e["pass"] for e in events] == np.repeat([1, 2, 3], 15).tolist()
    for event in state.events:
        assert event["captured_monotonic_s"] - state.starts[event["visit"]] >= 1.5
    assert all(b > a for a, b in zip(state.starts, state.starts[1:]))
    for visit in plan[1:-1]:
        last = max(e["captured_monotonic_s"] for e in state.events if e["visit"] == visit["visit"])
        assert state.starts[visit["visit"] + 1] - last >= 0.5


def test_timeout_when_no_valid_samples():
    state, callbacks = harness()

    def observe():
        state.t += 1
        return None, state.t

    callbacks["observe"] = observe
    with pytest.raises(RuntimeError, match="timed out"):
        collect_revisits(revisit_plan(POINTS), **callbacks)
    assert state.events == []


def test_cancellation_propagates_before_observing():
    state, callbacks = harness()

    def cancel():
        raise KeyboardInterrupt

    callbacks["poll"] = cancel
    with pytest.raises(KeyboardInterrupt):
        collect_revisits(revisit_plan(POINTS), **callbacks)
    assert state.polls == 0


def test_record_failure_stops_collection():
    state, callbacks = harness()

    def fail(event):
        raise OSError("disk full")

    callbacks["record"] = fail
    with pytest.raises(OSError, match="disk full"):
        collect_revisits(revisit_plan(POINTS), **callbacks)
    assert len(state.starts) == 2


@pytest.mark.parametrize("flags, enabled", [([], False), (["--revisit-calibration"], True)])
def test_cli_preserves_default_and_explicit_opt_in(monkeypatch, flags, enabled):
    from experiments.gazefollower_baseline import run

    monkeypatch.setattr("sys.argv", ["runner", *flags])
    seen = []
    monkeypatch.setattr(run, "run", lambda args: seen.append(args))
    run.main()
    assert seen[0].revisit_calibration is enabled


def test_cli_rejects_repair_combination_before_loading_camera(monkeypatch):
    from experiments.gazefollower_baseline import run

    monkeypatch.setattr("sys.argv", ["runner", "--revisit-calibration", "--repair-calibration"])
    monkeypatch.setattr(run, "run", lambda args: pytest.fail("must reject before run"))
    with pytest.raises(SystemExit) as error:
        run.main()
    assert error.value.code == 2


@pytest.mark.parametrize("bad", [np.full(258, np.nan), np.zeros(257)])
def test_invalid_vectors_do_not_complete_warmup(bad):
    state, callbacks = harness()

    def observe():
        state.t += 0.1
        return bad, state.t

    callbacks["observe"] = observe
    with pytest.raises(RuntimeError, match="timed out"):
        collect_revisits(revisit_plan(POINTS), **callbacks)
    assert state.events == []
