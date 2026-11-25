# Comfortable-posture gaze replay, 2026-11-25

The working target is ≤20 logical screen pixels of mean radial error during comfortable posture, including small head movements. The four archived sessions come from one participant on one day at 1512 × 982 logical pixels. None establishes that target. The desktop application and the personal calibration procedure were not modified.

## Procedure

Each session supplies 13 personal calibration targets, with 20 evenly spaced jointly valid frames from the successful attempt at each. Evaluation uses the original scored frames on eight other locations, with equal weight for each target and session. All candidates use the same causal replay of the upstream look-ahead filter with three samples of history lag once warmed up. The entire recorded evaluation stream, including transitions, reaches the filter. Invalid observations reset it. The script also reports raw results and availability.

The small-motion subset is an exploratory proxy inside normal-posture blocks. Relative to the calibration median, the estimated 3D face-center displacement is at most 4% of calibration depth and the head rotation at most 7°. At least one lower bound must also be reached (0.5% of depth or 1°). These thresholds describe displacement from calibration, not physical millimeters, head speed or verified participant comfort. It includes 1,030 of 1,101 eligible unseen-target frames across the normal blocks, covering all eight targets per session. Deliberate tilt and lateral shift each have just one block and are reported separately.

## Filtered results

Mean radial error in logical pixels. Columns average sessions equally except for the single deliberate movement blocks.

| Mapping | Normal | Small motion | Deliberate tilt | Deliberate lateral shift |
|---|---:|---:|---:|---:|
| UniGaze angles, linear baseline | 39.2 | 39.5 | 97.4 | 330.1 |
| MGaze, replay from its recorded predictions | 83.0 | 82.9 | 468.8 | 159.8 |
| Face center + ray projected to camera-depth zero | 40.6 | 40.9 | 126.1 | 58.6 |
| Projected ray, quadratic mapping | 37.5 | 37.7 | 132.4 | 59.5 |
| Projected ray + four iris coordinates | 44.5 | 44.9 | 188.0 | 51.3 |
| Equal blend of projected ray and MGaze | 47.4 | 47.6 | 285.0 | 95.1 |
| UniGaze angles, quadratic mapping | 36.2 | 36.5 | 99.0 | 329.0 |
| Quadratic angles, median features per calibration target | 36.4 | 36.7 | 97.8 | 326.6 |
| Quadratic projected ray, median features per target | 38.2 | 38.5 | 132.7 | 61.8 |

The first round compared the two baselines, projected ray, quadratic projected ray, iris augmentation and equal model blend. The second round added quadratic angle features and the two calibration-median variants. Calibration labels, target order, clicks and trial identifiers never enter the prediction features. This retrospective exploration informed round two, so the archived sessions are not a prospective confirmation set.

## Across sessions and the 20 px target

For each held session, rank the nine mappings on the other three sessions by the average of normal and small-motion mean error. Fit the chosen mapping on the held session's own calibration and score its separate targets. This selects quadratic angles twice and the median variant twice. Small-motion error goes from **39.5 to 37.5 px**, but the equal-target fraction of samples within 20 px goes from **29.7% to 27.7%**. The improvement in mean does not translate into more observations inside the desired radius. No production change is justified.

| Held session | Baseline small-motion mean | Selected small-motion mean |
|---|---:|---:|
| c3275f969f8a | 46.3 | 37.4 |
| d069108b792e | 35.7 | 34.0 |
| 8e67745ab828 | 35.4 | 36.3 |
| ddd92abcda8c | 40.5 | 42.2 |

For the baseline, the distance from each target to its mean predicted position averages **34.9 px** on the small-motion subset. Even perfectly averaging the existing predictions for each fixation would leave substantial spatial bias. Investigate whether this bias is repeatable across fresh sessions and whether it changes direction with natural head movement. A prospective comparison should use unseen spatial locations, comfortable motion during fixation, and both mean error and fraction within 20 px. Keep the substantial deliberate movements as separate stress tests.

## Replay

Use the prepared local research environment containing NumPy and the original pinned GazeFollower filter. Supply the four archived session directories, each containing session.json, training-selection.json, samples.jsonl and filter-stream.jsonl.

```sh
PYTHONPATH=src:. python -m experiments.comfortable_gaze.replay \
  "$RESULTS/unigaze-paired-unseen-c3275f969f8a" \
  "$RESULTS/unigaze-paired-unseen-d069108b792e" \
  "$RESULTS/unigaze-posture-8e67745ab828" \
  "$RESULTS/unigaze-posture-ddd92abcda8c"
```

The JSON output includes per-session sample and target counts, filtered and raw mean radial error, average per-target bias magnitude, average per-target 90th percentile error and fraction within 20 px.

## Follow-up: transfer of bias and personal calibration residuals

The baseline is the archived filtered UniGaze prediction. The small-motion subset, personal calibrations and metrics are identical to the preceding experiment. For each of the 32 session/location combinations, compare the mean signed error with the mean error at the same location in the other three sessions. The vectors pointed into the same half-plane (positive dot product) in **16/32** cases. These are dependent observations from one participant.

For predictive transfer, leave out the entire test session and exclude its evaluated spatial location from all donor fixations. Average donor errors locally using predicted screen positions and a Gaussian width of 0.25 normalized units. Separately estimate how error changes within a fixation as face translation and rotation change, using centered donor fixations with equal weight and ridge shrinkage. Apply the fitted slope relative to the held session's calibration pose. Labels are used for fitting, fold assignment and scoring. No held evaluation label enters the prediction. Within-target RMS deviation changed from **21.09 to 21.03 px** after donor pose correction. This tests a transferable linear relationship and does not rule out an individual or nonlinear effect.

| Small-motion method | Mean radial error, px | Within 20 px |
|---|---:|---:|
| Baseline | 39.47 | 29.72% |
| Donor spatial correction | 43.69 | 18.96% |
| Donor pose correction | 39.97 | 26.44% |
| Both donor corrections | 44.28 | 19.62% |
| Personal local correction on angles | 36.46 | 26.97% |
| Personal local correction on projected ray | 37.73 | 25.39% |

In the personal correction experiment, derive 13 anchor positions from the median calibration features, then fit a smooth Gaussian residual on top of the original linear mapping. Kernel width is the median nearest-anchor distance and ridge penalty is 0.25. The same stream filter runs after correction. The angle variant reduced small-motion mean error in each session (46.29→39.0, 35.74→32.6, 35.36→35.1, 40.49→39.1 px), but fewer observations landed within 20 px overall. In the deliberate lateral-shift block its error was 328.0 px. The ray variant scored 60.3 px there, but 136.5 px in the tilt block. These results do not justify changing the desktop model.

Run the same command and four session paths above with module names
`experiments.comfortable_gaze.bias_transfer` and `experiments.comfortable_gaze.local_residual` to reproduce the two follow-ups.

## Prospective same-frame model comparison

Run `PYTHONPATH=src:. validation/results/unigaze-preflight-kit-20261029/venv/bin/python -m experiments.comfortable_gaze.live_pair` on the prepared Mac. Space starts the camera session and each evaluation block. Esc exits. The experiment shows a fixation point and stores only numeric features, target locations, timestamps, model provenance and results locally.

ETH-XGaze uses the local hysts ResNet18 checkpoint (SHA-256 d1c91b2aa6a0c73856c16890d337afdecdb05563ed52182dfdb77742f1c856bc). The two angle models receive the same normalized 224 × 224 RGB face tensor and inverse rotation. This isolates the prediction networks using UniGaze's shared face normalization. MGaze uses its own preprocessing on the same original frame. Each model receives a separate personal Ridge mapping fitted on identical samples (16 jointly valid scored frames per calibration target). The two angle models use standardized features; MGaze uses its original feature scale.

Score eight unseen locations in a comfortable posture, then the same locations in a rotated order while making mild head movements. Allow one second to settle at each location before collecting 14 jointly valid observations. Insufficient coverage retries the location. Results include raw and filtered equal-target radial error in macOS logical pixels, fraction within 20 px and measured small-motion subset coverage. Attempt counts cover the accepted target visits. Report small-motion error with its target and frame counts. Block order and a single participant limit interpretation.

Before live acquisition, both networks produced finite outputs on three repeated presentations of the same local public fixture, and an empty frame produced no prediction. This verifies the inference path only.

## Native keyboard transfer experiment

On the prepared Mac, run `PYTHONPATH=src:. ~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python -m experiments.comfortable_gaze.keyboard_transfer`. Start the exercise in the editor window. The camera supplies 16 fresh UniGaze observations per point after a one-second settling period on 13 targets. The baseline and the previously specified Gaussian residual use this same fresh calibration.

A separate process presents the native FocusKeyboard for the exercise editor's focused text field. It highlights ten letter keys one at a time and reports their actual button rectangles in macOS logical screen coordinates. Each visit allows a second to settle and at least two seconds to score. Loss of focus or a change of key geometry restarts that visit. Baseline and corrected predictions are filtered separately and scored on identical usable frames. The paired measures are mean distance to key center, fraction within 20 px, and fraction inside the instructed key rectangle, weighting each key equally. This measures prompted gaze targeting. It does not measure typing speed or autonomous click success. Numeric results and completion status are written under `validation/results/keyboard-transfer-*.json`.
