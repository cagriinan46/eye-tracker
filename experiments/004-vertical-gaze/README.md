# Experiment 004 — Vertical gaze feature stability

## Purpose

Experiment #14 found a clear, repeatable horizontal LEFT/CENTER/RIGHT signal but **not** a reliable vertical UP/CENTER/DOWN signal. Its combined vertical means were UP `0.4107`, CENTER `0.4094`, and DOWN `0.4019`; the raw ranges overlapped, and repeated UP/DOWN trial means varied substantially. All 896 sampling frames were usable, with no face loss, invalid geometry, failed reads, or tracking loss. The weakness therefore needs investigation in the feature representation and possible confounds, not an assumption of face-tracking failure.

**Question:** Can alternative normalized eye/iris geometry produce a more repeatable vertical gaze signal than Experiment #14's feature?

**Hypothesis:** Eyelid geometry, small head motion, or the previous normalization may have made the vertical feature unstable. Comparing local-eye features while recording those possible confounds may identify a more promising representation. This experiment is intended to improve vertical directional features **before any full 2D screen-calibration implementation**. It does not estimate screen coordinates or control the cursor.

## Verified landmarks and feature formulas

All geometry uses MediaPipe Face Landmarker 0.10.35 output. Eye-contour and iris-ring sets come from the installed `FaceLandmarksConnections` definitions, cross-checked against [Google's official Face Landmarker Python source](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py). The following selected points are present on those verified contour paths; upper/lower refers to the path in the camera image, not a gesture detector:

| Eye | Outer contour corners | Central upper lid | Central lower lid | Iris ring |
| --- | --- | --- | --- | --- |
| MediaPipe left | 263, 362 | 386 | 374 | 474, 475, 476, 477 |
| MediaPipe right | 33, 133 | 159 | 145 | 469, 470, 471, 472 |

The left contour endpoints are `249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466`; the right contour endpoints are `7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246`. The script obtains these sets from named MediaPipe connections rather than maintaining guessed indices. Its chosen corner and lid indices are checked against the contour sets at startup.

For geometry, normalized landmark coordinates are converted to pixel-equivalent x/y using input width/height so vector lengths and angles respect image aspect ratio. Let `I` be the mean of an eye's four iris-ring points; `A` and `B` its corners; `U` and `L` its central upper and lower lid points; `M=(A+B)/2`; `W=|B-A|`; and `N` the unit perpendicular to `B-A`, oriented so `(L-U)·N` is positive. These are **experimental features**, not calibrated gaze coordinates:

| CSV suffix | Definition | What differs |
| --- | --- | --- |
| `vertical_bbox` | `(I_y - min(contour_y)) / (max(contour_y) - min(contour_y))` | Exact Experiment #14 vertical baseline: image-aligned, normalized by contour height. |
| `vertical_local_axis` | `(I-M)·N / W` | Iris displacement along the corner-defined local vertical, normalized by eye width rather than eyelid height. |
| `vertical_lid_distances` | `(|I-U| - |I-L|) / (|I-U| + |I-L|)` | Relative 2D distances to the two central lid points; the denominator scales with local iris-to-lid geometry. |

Each formula is produced separately as `left_*` and `right_*`; `binocular_*` is their arithmetic mean. The local-axis and lid-distance signs are oriented so movement toward the lower lid is generally positive, but **observed** UP/CENTER/DOWN ordering must be determined from the run, not assumed. Values are not clipped. Near-zero geometry, non-finite coordinates, or insufficient landmarks mark a frame invalid rather than creating a misleading measurement.

The `*_horizontal_control` fields reproduce Experiment #14's `(I_x - min(contour_x)) / (max(contour_x) - min(contour_x))` for reference only; this experiment does not optimize horizontal gaze. `*_eye_opening` is `(L-U)·N / W`. `head_center_y` is the mean eye-corner midpoint y divided by frame height: a coarse vertical head-position proxy, **not** a measured head-pitch angle or head-pose compensation. `eyeBlinkLeft` and `eyeBlinkRight` are Face Landmarker blendshape scores. Neither scores nor eye opening set blink or command thresholds.

## Setup

From the repository root using the existing Python 3.12 virtual environment:

```bash
.venv/bin/python -m pip install -r experiments/004-vertical-gaze/requirements.txt
mkdir -p .venv/models
curl -fL -o .venv/models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
shasum -a 256 .venv/models/face_landmarker.task
```

The model is the [official float16 Face Landmarker bundle](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker#models) used in Experiments 002–003. Its previously recorded SHA-256 was `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`; verify it because the `latest` asset can change. The model stays in ignored `.venv/`. Experiment-only dependencies are `mediapipe==0.10.35` and `opencv-python`; no production framework choice or new ADR is made. MediaPipe 1.0.1 previously caused a native SIGABRT on the tested macOS ARM64 / Python 3.12 environment, while 0.10.35 initialized successfully.

## Primary run and optional observation

From the repository root:

```bash
.venv/bin/python experiments/004-vertical-gaze/vertical_gaze_experiment.py --camera-index 1 --condition stable --output .venv/vertical-gaze-stable.csv
```

The window presents UP, CENTER, and DOWN as visible points. Defaults are five trials per direction, a one-second transition, two seconds of sampling per trial, and reproducible shuffled order with seed `42` (about 45 seconds, plus runtime overhead). Look at each point, keep the head approximately stable, move primarily the eyes, blink naturally, and remain at a comfortable normal distance. Avoid discomfort or unnecessary eye fatigue. Press `q` or Esc in the window, or Ctrl+C, to cancel. A cancelled run is incomplete.

Camera index `1` previously selected this development Mac's built-in camera; index `0` selected a paired iPhone through Continuity Camera. Device ordering is not portable. Use `--camera-index`, `--model`, `--trials`, `--sample-seconds`, `--transition-seconds`, or `--seed` when needed, and record any changed options in `RESULTS.md`.

After interpreting the stable-head run, an **optional, separate** small-natural-head-motion run can use:

```bash
.venv/bin/python experiments/004-vertical-gaze/vertical_gaze_experiment.py --camera-index 1 --condition small-head-motion --output .venv/vertical-gaze-small-motion.csv
```

In that optional run, allow only small comfortable natural head movement; do not deliberately exaggerate it. The condition is a label for comparison, not software head-motion correction. Do not combine the two runs when assessing the primary result. The second run is not required to complete interpretation of the first.

## Measurements and interpretation

The console reports elapsed time, resolution, trial order, sampling/usable counts, camera/detection/geometry failures, and missing blink output. For every left/right/binocular vertical candidate it reports UP/CENTER/DOWN count, mean, standard deviation, raw range, each trial's mean, signed pairwise mean differences, and raw-range overlap. It also reports blink scores, eye opening, the vertical head-position proxy, and the horizontal reference by label. Within-label correlations between candidate values and their matching blink/eye-opening signals or the head proxy are descriptive checks for association, **not** causal evidence or statistical significance.

An optional CSV records only derived numeric features plus target/trial/condition labels, face-detection and geometry-validity flags, and timestamps. Rows with missing faces or invalid geometry retain blank feature fields for failure accounting. `--output` never overwrites an existing file; omit it to avoid writing data. Compare each candidate with the Experiment #14 `vertical_bbox` baseline. A candidate is promising only if measured ordering, trial repeatability, and UP/CENTER/DOWN overlap meaningfully improve; no numerical pass threshold is invented. If none improves, record that negative result.

## Privacy and limitations

Frames, facial images, and video are never saved or uploaded. Processing is local; model download is a separate setup step. Derived numerical CSV data can still be sensitive and should remain local unless deliberately reviewed for sharing. The visible points are directional prompts, not calibrated screen coordinates.

Eye closure, glasses, lighting, screen/window placement, head translation or rotation, posture, distance, and individual anatomy may affect all features. The vertical head-position proxy cannot distinguish pitch from translation, and correlation does not identify a cause. This short, single-user feature study cannot establish general gaze accuracy, a production algorithm, command thresholds, or final product robustness. Leave the conclusion in [RESULTS.md](RESULTS.md) pending until the human run is measured.
