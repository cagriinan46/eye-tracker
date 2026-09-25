"""Controlled, session-local validation of the merged production gaze path.

Target layout and metric definitions follow Experiment 006; this module is
validation tooling, not a production calibration GUI or gaze algorithm.
"""

import argparse
import json
import random
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from math import hypot, isfinite
from pathlib import Path
from statistics import fmean, median

from eye_tracker.app.gaze_pipeline import process_gaze_frame
from eye_tracker.gaze.calibration import (
    CalibrationSample,
    IndependentLinearMapping,
    aggregate_calibration_observations,
    fit_independent_linear,
)
from eye_tracker.gaze.estimator import (
    GazeEstimate,
    GazeUnavailable,
    UnavailableReason,
    estimate_gaze,
)
from eye_tracker.vision.camera import OpenCVCameraSource
from eye_tracker.vision.contracts import FrameSource, LandmarkExtractor
from eye_tracker.vision.eye_features import EyeFeatures, extract_binocular_features
from eye_tracker.vision.eye_topology import eye_geometry_from_observation
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor

# Experiment 006 capture and analyzer defaults, not permanent product settings.
SETTLE_SECONDS = 0.8
SAMPLE_SECONDS = 1.2
MIN_USABLE_SAMPLES = 5


@dataclass(frozen=True, slots=True)
class Target:
    name: str
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Presentation:
    phase: str
    target: Target
    trial: int


@dataclass(frozen=True, slots=True)
class TrialEstimate:
    target: Target
    trial: int
    estimates: tuple[GazeEstimate, ...]


CALIBRATION_TARGETS = tuple(
    Target(f"C-{row}-{column}", x, y)
    for row, y in enumerate((0.20, 0.50, 0.80), start=1)
    for column, x in enumerate((0.20, 0.50, 0.80), start=1)
)
VALIDATION_TARGETS = (
    Target("V-1", 0.35, 0.35),
    Target("V-2", 0.65, 0.35),
    Target("V-3", 0.35, 0.65),
    Target("V-4", 0.65, 0.65),
    Target("V-5", 0.50, 0.35),
    Target("V-6", 0.65, 0.50),
    Target("V-7", 0.50, 0.65),
    Target("V-8", 0.35, 0.50),
)


def build_presentations(seed: int = 42) -> tuple[Presentation, ...]:
    """Keep Experiment 006's calibration order and shuffled held-out repeats."""
    calibration = [Presentation("calibration", target, 1) for target in CALIBRATION_TARGETS]
    validation = [
        Presentation("validation", target, trial)
        for trial in (1, 2)
        for target in VALIDATION_TARGETS
    ]
    random.Random(seed).shuffle(validation)
    return tuple(calibration + validation)


def fit_session_calibration(
    observations: list[tuple[Target, list[tuple[float, float]]]],
) -> tuple[IndependentLinearMapping, tuple[CalibrationSample, ...]]:
    """Apply existing per-axis medians and fitter to one session's targets."""
    samples = []
    for target, features in observations:
        if len(features) < MIN_USABLE_SAMPLES:
            raise ValueError(f"{target.name}: need five usable calibration samples")
        samples.append(aggregate_calibration_observations(features, target.x, target.y))
    return fit_independent_linear(samples), tuple(samples)


def collect_features_once(
    source: FrameSource, extractor: LandmarkExtractor
) -> EyeFeatures | GazeUnavailable:
    """Compose production Vision components for pre-calibration collection."""
    frame = source.read()
    if frame is None:
        return GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    observation = extractor.extract(frame)
    try:
        geometry = eye_geometry_from_observation(observation)
    except ValueError:
        return GazeUnavailable(UnavailableReason.INVALID_FEATURES)
    if geometry is None:
        return GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    return extract_binocular_features(*geometry, frame.width, frame.height) or GazeUnavailable(
        UnavailableReason.INVALID_FEATURES
    )


def collect_presentation(
    presentation: Presentation,
    measure: Callable[[], EyeFeatures | GazeEstimate | GazeUnavailable],
    show: Callable[[Presentation, bool, float], bool],
    clock: Callable[[], float] = time.monotonic,
) -> tuple[tuple[EyeFeatures | GazeEstimate, ...], dict]:
    """Collect after Experiment 006's settling interval; never return partial trials."""
    began = clock()
    samples: list[EyeFeatures | GazeEstimate] = []
    counts: dict = {"sampling_attempts": 0, "unavailable": {}}
    duration = SETTLE_SECONDS + SAMPLE_SECONDS
    while (elapsed := clock() - began) < duration:
        sampling = elapsed >= SETTLE_SECONDS
        remaining = duration - elapsed if sampling else SETTLE_SECONDS - elapsed
        if show(presentation, sampling, remaining):
            raise InterruptedError("validation cancelled")
        result = measure()
        if not sampling:
            continue
        counts["sampling_attempts"] += 1
        if isinstance(result, GazeUnavailable):
            key = result.reason.value
            counts["unavailable"][key] = counts["unavailable"].get(key, 0) + 1
        else:
            samples.append(result)
    if len(samples) < MIN_USABLE_SAMPLES:
        raise ValueError(f"{presentation.target.name}: need five usable sampling frames")
    return tuple(samples), counts


def percentile(values: list[float], percentage: float) -> float:
    """Linear interpolation matching Experiment 006's np.percentile default."""
    if not values or not 0 <= percentage <= 100:
        raise ValueError("percentile needs data and a percentage in [0, 100]")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage / 100
    lower = int(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def _error_summary(trials: list[dict]) -> dict:
    summary = {}
    for name in (
        "horizontal_absolute_error",
        "vertical_absolute_error",
        "normalized_error",
        "pixel_equivalent_error",
    ):
        values = [item[name] for item in trials]
        summary[f"mean_{name}"] = fmean(values)
        summary[f"median_{name}"] = median(values)
        summary[f"p95_{name}"] = percentile(values, 95)
    summary["mean_signed_x_bias"] = fmean(item["predicted_x"] - item["target_x"] for item in trials)
    summary["mean_signed_y_bias"] = fmean(item["predicted_y"] - item["target_y"] for item in trials)
    return summary


def _spatial_ordering(trials: list[dict]) -> dict:
    by_target: dict[str, list[dict]] = {}
    for item in trials:
        by_target.setdefault(item["target_id"], []).append(item)
    centers = [
        {
            "x": rows[0]["target_x"],
            "y": rows[0]["target_y"],
            "pred_x": median(row["predicted_x"] for row in rows),
            "pred_y": median(row["predicted_y"] for row in rows),
        }
        for rows in by_target.values()
    ]
    result = {}
    for coordinate, predicted in (("x", "pred_x"), ("y", "pred_y")):
        consistent = total = 0
        for index, left in enumerate(centers):
            for right in centers[index + 1 :]:
                actual_delta = right[coordinate] - left[coordinate]
                if abs(actual_delta) < 0.05:
                    continue
                total += 1
                consistent += (right[predicted] - left[predicted]) * actual_delta > 0
        result[coordinate] = {"consistent_pairs": consistent, "total_pairs": total}
    return result


def summarize_held_out(
    trial_estimates: list[TrialEstimate], window_width: int, window_height: int
) -> dict:
    """Report per-presentation medians and Experiment 006 error metrics."""
    if window_width <= 0 or window_height <= 0 or not trial_estimates:
        raise ValueError("positive window dimensions and held-out trials are required")
    points = []
    for trial in trial_estimates:
        if len(trial.estimates) < MIN_USABLE_SAMPLES:
            raise ValueError(f"{trial.target.name}: need five usable held-out estimates")
        x = median(item.x for item in trial.estimates)
        y = median(item.y for item in trial.estimates)
        points.append((trial.target, trial.trial, x, y))
    return _evaluate_predictions(points, window_width, window_height)


def summarize_calibration_fit(
    mapping: IndependentLinearMapping,
    observations: list[tuple[Target, list[tuple[float, float]]]],
    samples: tuple[CalibrationSample, ...],
    window_width: int,
    window_height: int,
) -> dict:
    """Score fitted calibration targets separately from held-out targets."""
    if len(observations) != len(samples):
        raise ValueError("calibration observations and samples do not match")
    points = []
    for (target, _), sample in zip(observations, samples):
        result = estimate_gaze(mapping, sample.horizontal_feature, sample.vertical_feature)
        if not isinstance(result, GazeEstimate):
            raise ValueError(f"{target.name}: calibration fit prediction unavailable")
        points.append((target, 1, result.x, result.y))
    return _evaluate_predictions(points, window_width, window_height)


def _evaluate_predictions(
    points: list[tuple[Target, int, float, float]], window_width: int, window_height: int
) -> dict:
    trials = []
    for target, trial_number, x, y in points:
        if not all(isfinite(value) for value in (x, y)):
            raise ValueError("held-out estimate must be finite")
        dx, dy = x - target.x, y - target.y
        trials.append(
            {
                "target_id": target.name,
                "trial_number": trial_number,
                "target_x": target.x,
                "target_y": target.y,
                "predicted_x": x,
                "predicted_y": y,
                "horizontal_absolute_error": abs(dx),
                "vertical_absolute_error": abs(dy),
                "normalized_error": hypot(dx, dy),
                "pixel_equivalent_error": hypot(dx * window_width, dy * window_height),
            }
        )
    return {
        "trials": trials,
        "summary": _error_summary(trials),
        "spatial_ordering": _spatial_ordering(trials),
    }


class RecordingSource:
    """Observe read failures and dimensions without changing FrameSource behavior."""

    def __init__(self, source: FrameSource) -> None:
        self.source = source
        self.reads = 0
        self.failed_reads = 0
        self.last_frame = None
        self.resolution: tuple[int, int] | None = None

    def read(self):
        self.reads += 1
        self.last_frame = self.source.read()
        if self.last_frame is None:
            self.failed_reads += 1
        else:
            self.resolution = (self.last_frame.width, self.last_frame.height)
        return self.last_frame


class RecordingExtractor:
    """Observe no-face output while delegating detection to production Vision."""

    def __init__(self, extractor: LandmarkExtractor) -> None:
        self.extractor = extractor
        self.observations = 0
        self.no_face = 0

    def extract(self, frame):
        self.observations += 1
        observation = self.extractor.extract(frame)
        if observation.landmarks is None:
            self.no_face += 1
        return observation


def _draw_target(
    cv2,
    np,
    presentation: Presentation,
    position: int,
    total: int,
    sampling: bool,
    remaining: float,
    width: int,
    height: int,
):
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    target = presentation.target
    point = (round(target.x * width), round(target.y * height))
    cv2.circle(canvas, point, 24, (255, 255, 255), 3)
    cv2.circle(canvas, point, 7, (0, 190, 255), -1)
    label = "SAMPLING" if sampling else "SETTLING"
    for message, baseline, scale in (
        (f"{presentation.phase.upper()} {target.name} - look at the dot", 50, 0.8),
        (f"Target {position}/{total} | {label} | {remaining:.1f}s", 90, 0.65),
        ("Natural blinking, stable head. q / Esc: cancel", height - 30, 0.55),
    ):
        cv2.putText(
            canvas, message, (30, baseline), cv2.FONT_HERSHEY_SIMPLEX, scale, (225, 225, 225), 2
        )
    return canvas


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--camera-index", type=int, required=True, help="Camera index for this machine"
    )
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Validation shuffle seed; default matches Experiment 006",
    )
    parser.add_argument(
        "--output", type=Path, help="New JSON result path under the ignored .venv directory"
    )
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if args.output is not None:
        ignored_root = Path(".venv").resolve()
        if not args.output.resolve().is_relative_to(ignored_root):
            parser.error("result output must be inside the Git-ignored .venv directory")
    return args


def run(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    if args.output is not None and args.output.exists():
        print(f"Refusing to overwrite existing result: {args.output}", file=sys.stderr)
        return 1

    # Import UI dependencies only for an actual human run; CI tests stay hardware-free.
    import cv2
    import numpy as np

    window = "Phase 1 real session gaze validation - q / Esc to cancel"
    source = OpenCVCameraSource(args.camera_index)
    recorded_source = RecordingSource(source)
    window_created = False
    try:
        with MediaPipeFaceLandmarkExtractor(args.model) as detector:
            recorded_extractor = RecordingExtractor(detector)
            source.open()
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            window_created = True
            cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(window, np.full((700, 1200, 3), 24, dtype=np.uint8))
            cv2.waitKey(1)
            _, _, width, height = cv2.getWindowImageRect(window)
            if width <= 0 or height <= 0:
                raise RuntimeError("Could not determine target-window image-area dimensions")

            order = build_presentations(seed=args.seed)
            calibration_observations: list[tuple[Target, list[tuple[float, float]]]] = []
            held_out: list[TrialEstimate] = []
            collection_counts: dict[str, dict] = {}
            mapping = None
            calibration_samples: tuple[CalibrationSample, ...] = ()
            started = time.monotonic()
            for position, presentation in enumerate(order, start=1):

                def show(current: Presentation, sampling: bool, remaining: float) -> bool:
                    cv2.imshow(
                        window,
                        _draw_target(
                            cv2,
                            np,
                            current,
                            position,
                            len(order),
                            sampling,
                            remaining,
                            width,
                            height,
                        ),
                    )
                    return cv2.waitKey(1) & 0xFF in (ord("q"), 27)

                def measure() -> EyeFeatures | GazeEstimate | GazeUnavailable:
                    if presentation.phase == "calibration":
                        return collect_features_once(recorded_source, recorded_extractor)
                    return process_gaze_frame(recorded_source, recorded_extractor, mapping)

                samples, counts = collect_presentation(presentation, measure, show)
                collection_counts[f"{presentation.target.name}/{presentation.trial}"] = {
                    "phase": presentation.phase,
                    "sampling_attempts": counts["sampling_attempts"],
                    "usable_samples": len(samples),
                    "unavailable": counts["unavailable"],
                }
                if presentation.phase == "calibration":
                    calibration_observations.append(
                        (
                            presentation.target,
                            [(item.horizontal, item.vertical) for item in samples],
                        )
                    )
                    if len(calibration_observations) == len(CALIBRATION_TARGETS):
                        mapping, calibration_samples = fit_session_calibration(
                            calibration_observations
                        )
                else:
                    held_out.append(TrialEstimate(presentation.target, presentation.trial, samples))

            elapsed = time.monotonic() - started
            if mapping is None:
                raise RuntimeError("session calibration was not fitted")
            report = {
                "intended_condition": "controlled normal use; natural blinking and eye opening",
                "camera_index": args.camera_index,
                "camera_resolution": recorded_source.resolution,
                "window_image_area": [width, height],
                "elapsed_seconds": elapsed,
                "seed": args.seed,
                "settle_seconds": SETTLE_SECONDS,
                "sample_seconds": SAMPLE_SECONDS,
                "minimum_usable_samples_per_presentation": MIN_USABLE_SAMPLES,
                "calibration_target_count": len(calibration_observations),
                "held_out_trial_count": len(held_out),
                "camera_reads_including_settling": recorded_source.reads,
                "successful_camera_reads_including_settling": (
                    recorded_source.reads - recorded_source.failed_reads
                ),
                "failed_camera_reads_including_settling": recorded_source.failed_reads,
                "no_face_observations_including_settling": recorded_extractor.no_face,
                "collection_counts": collection_counts,
                "calibration_fit": summarize_calibration_fit(
                    mapping, calibration_observations, calibration_samples, width, height
                ),
                "held_out_validation": summarize_held_out(held_out, width, height),
                "protocol_difference": (
                    "Experiment 006's experimental blink/near-closure gate is omitted: "
                    "the production pipeline has no validated blink filter. "
                    "Unavailable/invalid frames are counted, not silently filled."
                ),
            }
            print(json.dumps(report, indent=2))
            if args.output is not None:
                with args.output.open("x", encoding="utf-8") as destination:
                    json.dump(report, destination, indent=2)
                    destination.write("\n")
                print(f"Local derived-numerical result: {args.output}")
            return 0
    except KeyboardInterrupt:
        print("Validation interrupted; no completed result was saved.", file=sys.stderr)
        return 130
    except InterruptedError:
        print("Validation cancelled; no completed result was saved.", file=sys.stderr)
        return 130
    except (cv2.error, RuntimeError, ValueError, OSError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1
    finally:
        source.close()
        if window_created:
            cv2.destroyWindow(window)


def main(argv: list[str] | None = None) -> int:
    return run(_parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
