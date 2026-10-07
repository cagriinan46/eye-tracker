"""Typed calibration-only input; no validation-fitting or outcome API."""

from dataclasses import dataclass
from math import isclose

from experiments.raw_geometry_gaze_diagnostic.protocol import CALIBRATION_TARGETS
from eye_tracker.gaze.calibration import (
    IndependentLinearMapping,
    aggregate_calibration_observations,
    fit_independent_linear,
)
from validation.real_calibration import MIN_USABLE_SAMPLES

from . import representations as rep


@dataclass(frozen=True)
class CalibrationPresentation:
    target_id: str
    target_x: float
    target_y: float
    samples: tuple[dict, ...]

    def __post_init__(self):
        if any(s.get("phase") != "calibration" for s in self.samples):
            raise ValueError("only calibration-phase samples are permitted")


@dataclass(frozen=True)
class CandidateCalibration:
    reference: object
    mapping: IndependentLinearMapping | None
    usable_counts: tuple[int, ...]
    presentation_medians: tuple
    unavailable_reason: str | None


def parse_presentations(data):
    """Consume only capture['calibration_presentations'], never an entire capture."""
    if not isinstance(data, (list, tuple)) or len(data) != len(CALIBRATION_TARGETS):
        raise ValueError("exactly nine calibration presentations required")
    result = []
    for order, (p, target) in enumerate(zip(data, CALIBRATION_TARGETS, strict=True), 1):
        if (p["order"], p["target_id"], p["target_x"], p["target_y"]) != (
            order,
            target.name,
            target.x,
            target.y,
        ):
            raise ValueError("calibration target/order mismatch")
        presentation = CalibrationPresentation(target.name, target.x, target.y, tuple(p["samples"]))
        for sample in presentation.samples:
            if sample["presentation_order"] != order:
                raise ValueError("calibration sample order mismatch")
            if sample["feature_status"] == "usable":
                geometry = sample["raw_geometry"]
                if (
                    geometry is None
                    or sample["geometry_error"] is not None
                    or geometry["camera_resolution"] != sample["camera_resolution"]
                ):
                    raise ValueError("missing/mismatched calibration geometry")
                baseline = rep.r0(geometry).binocular
                if baseline is None or not all(
                    isclose(
                        getattr(baseline, a), sample[f"{a}_feature"], rel_tol=1e-10, abs_tol=1e-10
                    )
                    for a in ("horizontal", "vertical")
                ):
                    raise ValueError("calibration raw geometry does not reconstruct R0")
        result.append(presentation)
    return tuple(result)


def fit_candidates(calibration_presentations):
    """Freeze/reference and independently fit each candidate from nine calibrations."""
    if (
        not isinstance(calibration_presentations, tuple)
        or len(calibration_presentations) != len(CALIBRATION_TARGETS)
        or not all(isinstance(p, CalibrationPresentation) for p in calibration_presentations)
    ):
        raise TypeError("expected nine typed calibration presentations, not a capture/validation")
    for p, target in zip(calibration_presentations, CALIBRATION_TARGETS, strict=True):
        if (p.target_id, p.target_x, p.target_y) != (target.name, target.x, target.y):
            raise ValueError("calibration target/order mismatch")
        if any(s.get("phase") != "calibration" for s in p.samples):
            raise ValueError("only calibration-phase samples are permitted")
    records = [
        s["raw_geometry"]
        for p in calibration_presentations
        for s in p.samples
        if s["feature_status"] == "usable" and s["raw_geometry"] is not None
    ]
    references = {
        "R0": None,
        "R1": rep.face_reference(records),
        "R2": rep.contour_references(records),
    }
    fits = {}
    for name in rep.REPRESENTATIONS:
        medians, counts = [], []
        for p in calibration_presentations:
            observations = []
            for sample in p.samples:
                if sample["feature_status"] != "usable" or sample["raw_geometry"] is None:
                    continue
                record = sample["raw_geometry"]
                feature = (
                    rep.r0(record)
                    if name == "R0"
                    else rep.r1(record, references[name])
                    if name == "R1"
                    else rep.r2(record, references[name])
                ).binocular
                if feature is not None:
                    observations.append((feature.horizontal, feature.vertical))
            counts.append(len(observations))
            if len(observations) >= MIN_USABLE_SAMPLES:
                medians.append(
                    aggregate_calibration_observations(observations, p.target_x, p.target_y)
                )
        mapping, reason = None, None
        if len(medians) != len(CALIBRATION_TARGETS):
            reason = (
                "not evaluable: fewer than five usable observations at one or more calibrations"
            )
        else:
            try:
                mapping = fit_independent_linear(medians)
            except ValueError as error:
                reason = f"not evaluable: {error}"
        fits[name] = CandidateCalibration(
            references[name], mapping, tuple(counts), tuple(medians), reason
        )
    return fits
