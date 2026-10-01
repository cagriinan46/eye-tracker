"""Compare the same held-out observations before and after one fixed y shift."""

from collections.abc import Sequence

from experiments.fixed_center_live_validation.protocol import CENTER
from eye_tracker.gaze.calibration import (
    CalibrationSample,
    IndependentLinearMapping,
    aggregate_calibration_observations,
)
from eye_tracker.gaze.estimator import GazeEstimate, estimate_gaze
from validation.real_calibration import (
    MIN_USABLE_SAMPLES,
    VALIDATION_TARGETS,
    TrialEstimate,
    summarize_held_out,
)


def derive_offset(
    mapping: IndependentLinearMapping, anchor_observations: Sequence[tuple[float, float]]
) -> dict:
    """Use only the known CENTER and its post-calibration feature samples."""
    if len(anchor_observations) < MIN_USABLE_SAMPLES:
        raise ValueError("CENTER anchor needs five usable samples")
    anchor = aggregate_calibration_observations(anchor_observations, CENTER.x, CENTER.y)
    prediction = estimate_gaze(mapping, anchor.horizontal_feature, anchor.vertical_feature)
    if not isinstance(prediction, GazeEstimate):
        raise ValueError("CENTER anchor baseline prediction unavailable")
    return {
        "target_x": CENTER.x,
        "target_y": CENTER.y,
        "usable_samples": len(anchor_observations),
        "anchor_horizontal_feature": anchor.horizontal_feature,
        "anchor_vertical_feature": anchor.vertical_feature,
        "anchor_baseline_predicted_y": prediction.y,
        "fixed_vertical_offset": CENTER.y - prediction.y,
    }


def compare_predictions(
    mapping: IndependentLinearMapping,
    calibration_center: CalibrationSample,
    anchor_observations: Sequence[tuple[float, float]],
    held_out: list[TrialEstimate],
    window_width: int,
    window_height: int,
) -> dict:
    """Apply the completed anchor to the unchanged held-out estimate frames."""
    if (calibration_center.target_x, calibration_center.target_y) != (CENTER.x, CENTER.y):
        raise ValueError("calibration center sample must target exact CENTER")
    expected = {(target.name, trial) for target in VALIDATION_TARGETS for trial in (1, 2)}
    actual = {(trial.target.name, trial.trial) for trial in held_out}
    if len(held_out) != len(expected) or actual != expected:
        raise ValueError("comparison requires 16 distinct held-out presentations")
    anchor = derive_offset(mapping, anchor_observations)
    offset = anchor["fixed_vertical_offset"]
    baseline = summarize_held_out(held_out, window_width, window_height)
    corrected_trials = [
        TrialEstimate(
            trial.target,
            trial.trial,
            tuple(GazeEstimate(estimate.x, estimate.y + offset) for estimate in trial.estimates),
        )
        for trial in held_out
    ]
    corrected = summarize_held_out(corrected_trials, window_width, window_height)
    paired = []
    for observation, before, after in zip(
        held_out, baseline["trials"], corrected["trials"], strict=True
    ):
        if (before["target_id"], before["trial_number"]) != (
            after["target_id"],
            after["trial_number"],
        ) or before["predicted_x"] != after["predicted_x"]:
            raise ValueError("baseline and corrected trials differ beyond vertical offset")
        paired.append(
            {
                "target_id": before["target_id"],
                "trial_number": before["trial_number"],
                "target_y": before["target_y"],
                "baseline_predicted_x": before["predicted_x"],
                "corrected_predicted_x": after["predicted_x"],
                "baseline_predicted_y": before["predicted_y"],
                "corrected_predicted_y": after["predicted_y"],
                "baseline_signed_y_error": before["predicted_y"] - before["target_y"],
                "corrected_signed_y_error": after["predicted_y"] - after["target_y"],
                "baseline_absolute_y_error": before["vertical_absolute_error"],
                "corrected_absolute_y_error": after["vertical_absolute_error"],
                "usable_samples": len(observation.estimates),
            }
        )
    return {
        "mapping_coefficients": {
            "x_slope": mapping.x_slope,
            "x_intercept": mapping.x_intercept,
            "y_slope": mapping.y_slope,
            "y_intercept": mapping.y_intercept,
        },
        "calibration_center_vertical_feature": calibration_center.vertical_feature,
        "anchor": anchor,
        "baseline": baseline,
        "corrected": corrected,
        "trials": paired,
    }
