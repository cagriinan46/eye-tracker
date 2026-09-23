# Experiment 006 — Limited 2D gaze-mapping feasibility

## Question and hypothesis

Can the previously explored binocular horizontal feature and `binocular_vertical_local_axis`, after a short **session-local** calibration, estimate held-out 2D target positions with useful directional/spatial consistency? We hypothesize that simple within-session mappings can recover an approximate relationship despite between-session feature offsets. This is a controlled feasibility experiment, **not** a production gaze tracker, cursor controller, or permanent calibration method.

Experiment #14 found clear LEFT/CENTER/RIGHT horizontal separation. Experiment #16 identified the binocular local-eye-axis value as the leading vertical candidate, with UP/CENTER/DOWN mean ordering but overlapping frames, eyelid sensitivity, and session offsets. Experiment #18 found no temporal or blink-aware filter that consistently improved all three human runs. This experiment keeps those two feature definitions and does **not** adopt a production filter.

## Features and verified geometry

The capture script imports Experiment 004's `measure_features` and `blink_scores` rather than copying or changing its verified landmark geometry. The primary features are:

- Horizontal: arithmetic mean of the left/right `(iris_x - eye_contour_min_x) / (eye_contour_max_x - eye_contour_min_x)` values (`binocular_horizontal_control`). This is the same normalized horizontal formulation tested in Experiment 003.
- Vertical: arithmetic mean of each iris center's projection on the eye-corner line's oriented perpendicular, divided by eye-corner distance (`binocular_vertical_local_axis`). The eye normal points toward the lower lid. See [Experiment 004's verified landmark definitions](../004-vertical-gaze/README.md#verified-landmarks-and-feature-formulas).

These are **experimental feature values**, not screen coordinates. The local numerical CSV retains left/right feature values, `eyeBlinkLeft`, `eyeBlinkRight`, their mean `binocular_blink` when both are available, binocular eye opening, and a coarse head-center-y proxy for failure-mode inspection. Rows also identify the phase, target, trial, camera resolution, and target-window dimensions. The declared CSV header includes these derived fields; unavailable optional measurements are blank. No head-pose compensation is performed. MediaPipe and OpenCV remain experiment-only candidates, not accepted production choices.

## Target layouts

All target locations are normalized to the actual OpenCV target-window image area; the script attempts a full-screen window and records its measured image-area width/height. The calibration grid avoids extreme edges:

| Calibration row | Left | Center | Right |
| --- | --- | --- | --- |
| Top | (0.20, 0.20) | (0.50, 0.20) | (0.80, 0.20) |
| Middle | (0.20, 0.50) | (0.50, 0.50) | (0.80, 0.50) |
| Bottom | (0.20, 0.80) | (0.50, 0.80) | (0.80, 0.80) |

The eight **held-out** validation locations are (0.35, 0.35), (0.65, 0.35), (0.35, 0.65), (0.65, 0.65), (0.50, 0.35), (0.65, 0.50), (0.50, 0.65), and (0.35, 0.50). None duplicates a calibration coordinate. Each validation location is shown twice in reproducibly shuffled order (default seed 42). The user sees only the current target, never predicted coordinates.

Defaults are 0.8 seconds of settling plus 1.2 seconds of sampling per presentation: nine calibration presentations and sixteen validation presentations, approximately 50 seconds plus runtime overhead. The human should keep their head approximately stable, use a comfortable normal viewing distance and natural eye opening, blink normally, avoid intentional winks, and wear glasses normally if needed. Do **not** artificially widen the eyes. Press `q` or Esc to cancel. Cancellation or insufficient calibration samples exits without claiming a completed experiment.

## Setup and run

Use the existing Python 3.12 `.venv` from the repository root:

```bash
.venv/bin/python -m pip install -r experiments/006-2d-gaze-mapping/requirements.txt
.venv/bin/python experiments/006-2d-gaze-mapping/gaze_mapping_experiment.py --check-model
.venv/bin/python experiments/006-2d-gaze-mapping/gaze_mapping_experiment.py --camera-index 1 --output .venv/2d-gaze-mapping.csv
.venv/bin/python experiments/006-2d-gaze-mapping/analyze_mapping.py .venv/2d-gaze-mapping.csv
```

The exact **human run command** is the third line. It uses the [official float16 Face Landmarker model bundle](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker#models) already stored at `.venv/models/face_landmarker.task`; the local SHA-256 during setup was `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. If absent, follow [Experiment 004's model setup](../004-vertical-gaze/README.md#setup). Its `latest` download could change, so verify the asset. MediaPipe 0.10.35 initialized on the tested Mac, whereas 1.0.1 previously caused a native SIGABRT on this environment. Camera index 1 previously selected the Mac's built-in camera; camera ordering is not guaranteed. The output path must not already exist. Omit `--output` to print analysis without saving the derived CSV. `--check-model` verifies model initialization only; it does **not** validate camera capture or gaze mapping.

## Sample quality and mapping candidates

Each presentation requires at least five usable samples after settling; its horizontal and vertical calibration values are the **medians** of those samples, not single frames. Frames without a face, valid eye geometry, or finite feature values are excluded. The script reuses Experiment #18's **experimental-only** conservative blink/near-closure rule: either eye's blink score at least `0.65` **and** binocular opening no more than `70%` of the median of at least three prior accepted openings within 250 ms. Low eye opening alone is not discarded because vertical gaze may change eyelid opening. This gate is not a gesture classifier, a validated production threshold, or a temporal smoother. Rejected and unusable counts are reported; no samples are silently filled.

Two small least-squares candidates are fit **only to the nine calibration-target medians**:

1. Independent linear: `x = a·horizontal + b`, `y = c·vertical + d` (four fitted coefficients).
2. 2D affine: `x = a·horizontal + b·vertical + c`, `y = d·horizontal + e·vertical + f` (six fitted coefficients).

Insufficient or rank-deficient calibration data causes a clear failure. Coefficients are never saved or reused between sessions. Predictions are not clipped to `[0,1]`, because clipping would conceal edge/extrapolation error. No polynomial, neural network, broad parameter search, or direction-specific threshold is used.

## Analysis and interpretation

The console and optional `analyze_mapping.py --json` output report **calibration-fit and held-out validation separately** for each candidate. For every held-out presentation: target vs predicted normalized x/y, horizontal and vertical absolute errors, normalized 2D Euclidean error, and window-pixel-equivalent error (`sqrt((dx·window_width)^2 + (dy·window_height)^2)`). Mean, median, and p95 are reported for each error type, alongside mean signed x/y bias, repeated-target behavior, and descriptive left-to-right/top-to-bottom ordering. The window-pixel figure is relative to the measured OpenCV image area, **not** a physical-distance/visual-angle measure or necessarily the monitor's hardware-pixel count.

Inspect horizontal/vertical asymmetry, systematic offsets, edge degradation, calibration target inconsistency (per-target feature MAD), left/right eye disagreement, possible head-center changes, blink exclusions, and any poor repeated-trial consistency. These are observations, not automatic corrections. Held-out evidence matters more than calibration-fit error. There is **no predeclared pixel pass/fail threshold** and no single-user statistical-significance claim.

## Privacy and limitations

Camera processing and analysis are local. Only derived numeric samples/target metadata may be saved in the ignored `.venv/` CSV; no images, raw frames, or video are saved or uploaded. Treat derived features as potentially sensitive, and do not commit a human CSV without explicit review. Model download is a separate setup operation, not a real-time dependency.

This one-session protocol cannot establish cross-session calibration persistence, multi-user generalization, universal accuracy, real-world accessibility usability, or production-ready eye tracking. Window geometry, display scaling, head motion, eyelids, lighting, glasses, camera distance, and individual anatomy can affect results. The full-screen target-window image area is the coordinate system under test; the script does not move the cursor or execute OS actions. Actual human measurements and the bounded conclusion belong in [RESULTS.md](RESULTS.md) only after the run.
