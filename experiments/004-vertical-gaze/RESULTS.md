# Experiment 004 — Results

## Environment

Pending the human-controlled development-Mac run. Record actual macOS/Python versions, camera, installed MediaPipe/OpenCV versions, model checksum, lighting, seating position, and any relevant visual aids. MediaPipe 0.10.35 remains an experiment-only pin; MediaPipe 1.0.1 previously produced a native SIGABRT during model initialization on the tested macOS ARM64 / Python 3.12 setup.

## Configuration

Planned defaults: camera index 1, official float16 Face Landmarker model, `stable` condition, five trials per direction, one-second transition, two-second sampling, shuffled order with seed 42. Record actual options, resolution, elapsed time, and whether the run was interrupted.

## Previous Baseline

Experiment #14's combined vertical means were UP `0.4107`, CENTER `0.4094`, DOWN `0.4019`; raw ranges overlapped and repeated UP/DOWN trial means varied substantially. Its horizontal LEFT/CENTER/RIGHT separation was clear and repeatable. All 896 sampling frames were usable, with zero no-face frames, invalid geometry, failed reads, or tracking loss. The current study must compare new features against that measured vertical weakness, without assuming face-tracking failure caused it.

## Protocol

Pending. The primary run should use visible UP/CENTER/DOWN targets with the head approximately stable and eyes moving primarily. Record any deviations or discomfort. A separate small-natural-head-motion run is optional and should not replace the primary run.

## Candidate Features

Pending actual values. The script will report left/right/binocular versions of `vertical_bbox` (Experiment #14 control), `vertical_local_axis` (corner-defined perpendicular coordinate normalized by eye width), and `vertical_lid_distances` (relative iris-to-upper/lower-lid distances). Exact formulas and verified landmark sets are in [README.md](README.md).

## Measurements

Pending real data. Record sampling/usable counts, failed camera reads, no-face frames, invalid geometry, tracking loss, and per-candidate/per-direction sample count, mean, and standard deviation. Do not invent values or commit camera imagery.

## Directional Separation

Pending. For each candidate compare UP vs CENTER, CENTER vs DOWN, and UP vs DOWN ordering, mean shifts, raw-range overlap, and within-direction spread. Compare against the Experiment #14 baseline without a predetermined pass threshold.

## Trial-to-Trial Repeatability

Pending. Record all five trial means per label for each candidate and note whether ordering persists across trials.

## Confounding Signals

Pending. Examine left/right blink blendshape scores, eye opening, coarse vertical head-position proxy, detection state, and geometry validity. Distinguish observed associations from causal conclusions; no blink threshold or production head-pose correction is defined.

## Observations

Pending. Record tracking interruptions, eye closure, lighting, head movement, comfort, and any noteworthy differences between eyes. If the optional second run occurs, report it separately.

## Limitations

This will be a short single-user directional study rather than ground-truth screen calibration. The eye-center y proxy cannot isolate pitch from translation. Candidate comparison may be affected by lighting, eyelids, glasses, posture, camera placement, and individual differences. A stable technical run alone will not validate full 2D gaze estimation or select a production framework.

## Conclusion

Pending the primary human run and measured comparison. If no candidate meaningfully improves vertical ordering, overlap, and repeatability, report that negative result rather than proceeding as though full screen calibration were validated.

## Human execution command

From the repository root after the setup in [README.md](README.md):

```bash
.venv/bin/python experiments/004-vertical-gaze/vertical_gaze_experiment.py --camera-index 1 --condition stable --output .venv/vertical-gaze-stable.csv
```
