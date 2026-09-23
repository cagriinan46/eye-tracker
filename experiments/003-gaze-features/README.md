# Experiment 003 — Directional eye features

## Question and hypothesis

With the head approximately stable, do MediaPipe eye and iris landmarks yield repeatable numerical features that distinguish CENTER, LEFT, RIGHT, UP, and DOWN gaze targets? The hypothesis is that iris position normalized to eye geometry shifts with horizontal and vertical gaze direction enough to justify a later screen-calibration experiment. This study does **not** perform screen calibration or cursor control.

MediaPipe 0.10.35 is an **experimental candidate**, not an accepted production architecture decision. Experiment 002 found that 0.10.35 initialized and tracked on the development Mac; MediaPipe 1.0.1 caused a native SIGABRT during Face Landmarker initialization on that macOS ARM64 / Python 3.12 environment.

## Feature definitions and verified topology

The script uses the named `FaceLandmarksConnections` sets in the installed MediaPipe 0.10.35 Face Landmarker implementation, cross-checked with [Google's official Python source](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py). The indices are collected from the connection endpoints rather than guessed:

| Region | Landmark indices |
| --- | --- |
| Left eye contour | 249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466 |
| Left iris ring | 474, 475, 476, 477 |
| Right eye contour | 7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246 |
| Right iris ring | 469, 470, 471, 472 |

For each eye, iris position is the arithmetic mean of its four ring landmarks. The eye box is the minimum and maximum **x** and **y** among its contour landmarks. Horizontal feature = `(iris_x - eye_min_x) / (eye_max_x - eye_min_x)`; vertical feature = `(iris_y - eye_min_y) / (eye_max_y - eye_min_y)`. Left and right features are calculated separately. The combined feature is their arithmetic mean. A near-zero box dimension, missing face, too few landmarks, or non-finite coordinate makes that frame unusable. Values are not clipped.

Coordinates follow MediaPipe's image convention: x increases to the image right and y increases downward. The camera image is not mirrored by this script. The meaning and sign of target-direction shifts must be checked from real data; no left/right or up/down numerical ordering is assumed. A coarse head-position proxy is the mean of the two eye-box centers in normalized image coordinates. It can reveal obvious movement but is **not** head-pose compensation. Normalization reduces dependence on pixel resolution and face size; it does not make features invariant to head pose, eye closure, lighting, or camera distance.

## Setup

From the repository root, with the project's Python 3.12 `.venv`:

```bash
.venv/bin/python -m pip install -r experiments/003-gaze-features/requirements.txt
mkdir -p .venv/models
curl -fL -o .venv/models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
shasum -a 256 .venv/models/face_landmarker.task
```

This is the [official float16 Face Landmarker model bundle](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker#models) used in Experiment 002. Its previously recorded SHA-256 was `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`; verify the download because the `latest` asset can change. The model stays in ignored `.venv/`, not in the repository. Dependencies are local to this experiment: `mediapipe==0.10.35` and `opencv-python` (the latter is intentionally unpinned here). The preceding experiment reported OpenCV 5.0.0.93 in its environment; record the actual installed version for this run in `RESULTS.md`.

## Run and protocol

```bash
.venv/bin/python experiments/003-gaze-features/gaze_feature_experiment.py --camera-index 1 --output .venv/gaze-features.csv
```

The target window shows five directions, three trials each, in a reproducible shuffled order (`--seed 42`). Each target has a one-second transition period followed by approximately two seconds of sampling. Keep the head approximately stable, look directly at the visible target point, and move primarily the eyes. Blink naturally; do not force uncomfortable gaze or eye positions. Press `q` or Esc in the target window, or Ctrl+C, to cancel. A cancelled run is incomplete.

Camera index `1` selected the built-in camera on this development Mac; index `0` selected a paired iPhone through Continuity Camera. Camera ordering is not portable. Use `--camera-index`, `--model`, `--trials`, `--sample-seconds`, `--transition-seconds`, and `--seed` to adjust/reproduce the run. `--output` is optional; without it, no data file is written. The output path must not already exist, to prevent accidental overwriting. A camera/model/window failure exits non-zero with an error message.

## Measurements and interpretation

For each sampling frame, the optional CSV contains elapsed timestamp, target label, per-label trial number, face-detected flag, six normalized left/right/combined eye features, and the optional head-position proxy. Missing features are blank. The console summary reports total usable frames, no-face frames, tracking-loss events, longest no-face streak, invalid geometry, failed camera reads, per-label left/right/combined horizontal/vertical count, mean, standard deviation and range, per-trial combined means, signed between-label mean shifts, and raw-range overlap. A tracking-loss event means a sampling frame without a face immediately followed a sampling frame with a face. Check LEFT/CENTER/RIGHT on the horizontal axis and UP/CENTER/DOWN on the vertical axis, the direction and magnitude of observed shifts, overlap, and repeatability across all three trials. Also inspect face detection failures and the head proxy as possible confounds. These are descriptive measurements from a short single-user experiment, not statistical proof or command thresholds.

## Privacy and limitations

The camera stream, frames, and face imagery remain local and are not saved or uploaded. If requested, the CSV contains only derived numerical features and target/trial metadata; treat it as sensitive experimental data and do not commit it without review. Model download is a separate setup step, not a real-time service dependency.

The visible targets are directional prompts, not calibrated screen locations. Window placement/size, the person's distance and posture, lighting, glasses, eyelid movement, eye anatomy, natural blinking, and residual head motion may affect measurements. Min/max eye-box normalization may be unstable during partial eye closure. One participant and one short run cannot establish population-level performance, gaze accuracy, or suitability for final computer control. The conclusion belongs in [RESULTS.md](RESULTS.md) only after the human-controlled run.
