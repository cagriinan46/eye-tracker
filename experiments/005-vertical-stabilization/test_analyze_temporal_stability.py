"""Deterministic checks for causal, label-independent offline filtering."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("analyze_temporal_stability.py")
SPEC = importlib.util.spec_from_file_location("temporal_stability", SCRIPT)
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def sample(time, value, blink=0.0, opening=0.1, valid=True):
    return {
        "timestamp_s": time,
        "binocular_vertical_local_axis": value,
        "eyeBlinkLeft": blink,
        "eyeBlinkRight": blink,
        "binocular_eye_opening": opening,
        "face_detected": 1,
        "geometry_valid": int(valid),
    }


def test_rolling_median_is_causal_and_resets_after_sampling_gap():
    rows = [sample(0.00, 0.0), sample(0.05, 9.0), sample(0.10, 1.0), sample(1.0, 4.0)]
    assert analysis.stabilize(rows, "median_120") == [0.0, 4.5, 1.0, 4.0]


def test_blink_filter_requires_high_score_and_opening_collapse():
    rows = [
        sample(0.00, 1.0),
        sample(0.04, 1.0),
        sample(0.08, 1.0),
        sample(0.12, 9.0, blink=0.7, opening=0.03),
        sample(0.16, 2.0, blink=0.2, opening=0.03),
    ]
    assert analysis.stabilize(rows, "blink_median_120") == [1.0, 1.0, 1.0, None, 1.0]


def test_invalid_geometry_is_never_injected_into_aggregation():
    rows = [sample(0.0, 1.0), sample(0.04, 10.0, valid=False), sample(0.08, 3.0)]
    assert analysis.stabilize(rows, "mean_120") == [1.0, None, 2.0]


def test_interval_excludes_inter_trial_gap():
    rows = [sample(0.0, 1.0), sample(0.04, 1.0), sample(1.0, 1.0)]
    assert analysis.sampling_interval(rows) == 0.04


def test_jump_count_excludes_transition_gap_and_missing_output():
    rows = [sample(0.0, 0.0), sample(0.04, 3.0), sample(1.0, 10.0), sample(1.04, 11.0)]
    assert analysis.count_jumps(rows, [0.0, 3.0, 10.0, 11.0], 2.0) == 1
    assert analysis.count_jumps(rows, [0.0, None, 10.0, 11.0], 2.0) == 0
