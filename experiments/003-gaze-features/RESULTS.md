# Experiment 003 — Results

## Environment

Pending human execution on the development Mac. Record macOS version, Python version, camera used, installed MediaPipe/OpenCV versions, lighting, approximate seating position, and any relevant visual aids. MediaPipe 0.10.35 is pinned for this experiment because Experiment 002 succeeded with it; MediaPipe 1.0.1 produced a native SIGABRT during Face Landmarker initialization on the tested macOS ARM64/Python 3.12 setup. This is a compatibility observation, not a permanent framework decision.

## Configuration

Planned defaults: camera index 1, official float16 Face Landmarker model, five target directions, three trials per direction, one-second transition, two-second sampling, shuffled order with seed 42. Record actual options, model checksum, display/window arrangement, and whether the run was interrupted.

## Protocol

Pending. The participant should keep their head approximately stable and look directly at each visible target. Record deviations, discomfort, or interrupted trials.

## Measurements

Pending real camera data. Record total usable samples, no-face frames, invalid-geometry frames, failed camera reads, and per-label sample count and combined horizontal/vertical means and standard deviations. Preserve the derived numerical CSV locally if needed for review; do not add invented data or camera images.

## Directional Separation

Pending. Compare horizontal LEFT/CENTER/RIGHT and vertical UP/CENTER/DOWN feature shifts and their observed ranges/overlap. Determine the observed numerical sign rather than assuming it.

## Trial-to-Trial Repeatability

Pending. Compare each label's three trial means and within-trial spread.

## Observations

Pending. Note tracking interruptions, blink/eyelid effects, lighting, and any obvious head movement suggested by the coarse eye-center proxy.

## Limitations

The upcoming run will be a short single-user directional study, not ground-truth screen calibration. Window placement, head movement, eye closure, camera/lighting variation, and individual differences can affect the features. Results will not establish final gaze accuracy, generalize across users or devices, or select MediaPipe as production architecture.

## Conclusion

Pending the controlled human experiment. Do not infer that calibration is justified until actual directional separation and repeatability have been reviewed.

## Human execution command

From the repository root after the setup in [README.md](README.md):

```bash
.venv/bin/python experiments/003-gaze-features/gaze_feature_experiment.py --camera-index 1 --output .venv/gaze-features.csv
```
