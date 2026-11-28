"""Hardware-free checks for Issue #158: frozen conditions, gain, recentring, rule."""

import json

import pytest

from experiments.head_pointer import analysis as base_analysis
from experiments.head_pointer import protocol as base
from experiments.head_pointer.pointer import Line, Mapping, OneEuroFilter2D
from experiments.head_pointer_tuning import analysis, protocol, run
from experiments.head_pointer_tuning.pointer import GainedPointer


def test_frozen_conditions_and_order() -> None:
    assert protocol.SIGNAL == "RAY"
    assert [(c.name, c.min_cutoff, c.beta, c.gain) for c in protocol.CONDITIONS] == [
        ("BASE", 1.0, 0.01, 1.0),
        ("STEADY", 0.3, 0.03, 1.0),
        ("STEADY_GAIN", 0.3, 0.03, 1.5),
    ]
    assert protocol.SESSION_ORDER == {
        "A": ("BASE", "STEADY", "STEADY_GAIN"),
        "B": ("STEADY_GAIN", "STEADY", "BASE"),
    }
    # The #156 rule and test mechanics are reused unchanged.
    assert (base.MAX_TIMEOUTS_PER_SESSION, base.TIE_FRACTION) == (1, 0.05)
    assert (base.DWELL_SECONDS, base.TIMEOUT_SECONDS, base.TARGET_DIAMETERS) == (0.8, 8.0, (30, 60))


def test_target_schedule_matches_the_156_block_design() -> None:
    for session, order in protocol.SESSION_ORDER.items():
        trials = protocol.target_schedule(session)
        assert trials == protocol.target_schedule(session)
        assert tuple(dict.fromkeys(t.candidate for t in trials)) == order
        for name in order:
            block = [t for t in trials if t.candidate == name]
            scored = [t for t in block if not t.practice]
            assert len(block) == base.PRACTICE_TRIALS + 16 and len(scored) == 16
            assert sorted(t.diameter for t in scored) == [30] * 8 + [60] * 8
            assert all((a.x, a.y) != (b.x, b.y) for a, b in zip(scored, scored[1:], strict=False))
    with pytest.raises(ValueError):
        protocol.target_schedule("C")


IDENTITY = Mapping(Line(0.0, 1.0), Line(0.0, 1.0))


def test_gain_scales_around_the_centre() -> None:
    pointer = GainedPointer(IDENTITY, 1.5)
    assert pointer((0.5, 0.5)) == pytest.approx((0.5, 0.5))
    assert pointer((0.7, 0.3)) == pytest.approx((0.8, 0.2))
    assert GainedPointer(IDENTITY)((0.7, 0.3)) == pytest.approx((0.7, 0.3))


def test_recentre_puts_current_signal_on_centre_and_keeps_gain() -> None:
    pointer = GainedPointer(IDENTITY, 1.5)
    pointer.recentre((0.6, 0.45))
    assert pointer((0.6, 0.45)) == pytest.approx((0.5, 0.5))
    assert pointer((0.7, 0.45)) == pytest.approx((0.65, 0.5))
    pointer.recentre((0.7, 0.45))
    assert pointer((0.7, 0.45)) == pytest.approx((0.5, 0.5))


def test_steady_filter_is_calmer_at_rest_than_base() -> None:
    def rest_spread(min_cutoff, beta):
        f = OneEuroFilter2D(min_cutoff, beta)
        f.update(0.0, (100.0, 100.0))
        out = [f.update(i / 30, (100.0 + (3 if i % 2 else -3), 100.0)) for i in range(1, 90)]
        return max(abs(o[0] - 100.0) for o in out[-30:])

    steady = protocol.BY_NAME["STEADY"]
    assert rest_spread(steady.min_cutoff, steady.beta) < rest_spread(1.0, 0.01)


def test_comfort_keys() -> None:
    assert [run.comfort_from_key(ord(k)) for k in "012345 6"] == [None, 1, 2, 3, 4, 5, None, None]


def _session(name, outcomes):
    trials = []
    for condition, (timeouts, time, jitter) in outcomes.items():
        for i in range(16):
            selected = i >= timeouts
            trials.append(
                {
                    "candidate": condition,
                    "practice": False,
                    "diameter": (30, 60)[i % 2],
                    "outcome": "selected" if selected else "timeout",
                    "elapsed": time if selected else 8.0,
                    "entries": 1,
                    "hold_jitter_px": jitter if selected else None,
                }
            )
    return {
        "session": name,
        "completed": True,
        "mappings": dict.fromkeys(outcomes),
        "trials": trials,
        "comfort": dict.fromkeys(outcomes, 4),
        "recentres": dict.fromkeys(outcomes, 2),
    }


def test_rule_adopts_a_tuned_condition_only_when_it_beats_base() -> None:
    better = {"BASE": (0, 3.8, 7.0), "STEADY": (0, 3.0, 4.0), "STEADY_GAIN": (2, 2.5, 5.0)}
    summary = analysis.summarize([_session("A", better), _session("B", better)])
    assert summary["winner"] == "STEADY" and summary["adopted"] == "STEADY"
    assert summary["candidates"]["STEADY_GAIN"]["passes"] is False
    assert summary["candidates"]["BASE"]["comfort"] == {"A": 4, "B": 4}
    assert summary["candidates"]["BASE"]["recentres"] == {"A": 2, "B": 2}
    json.dumps(summary)

    base_wins = {"BASE": (0, 3.0, 4.0), "STEADY": (0, 3.8, 7.0), "STEADY_GAIN": (0, 3.9, 5.0)}
    summary = analysis.summarize([_session("A", base_wins), _session("B", base_wins)])
    assert summary["winner"] == "BASE" and summary["adopted"] is None

    nothing = {"BASE": (3, 3.0, 4.0), "STEADY": (2, 3.8, 7.0), "STEADY_GAIN": (5, 3.9, 5.0)}
    summary = analysis.summarize([_session("A", nothing), _session("B", nothing)])
    assert summary["winner"] is None and summary["adopted"] is None


def test_shared_rule_default_names_unchanged() -> None:
    assert tuple(base_analysis.summarize([])["candidates"]) == ("NOSE", "ANGLES", "RAY")


def test_run_arguments() -> None:
    args = run.parse_args(
        [
            "--participant", "p", "--session", "B", "--camera-index", "0",
            "--screen-size", "1512x982", "--output", "x.json",
        ]
    )  # fmt: skip
    assert (args.session, args.screen_size) == ("B", (1512, 982))
