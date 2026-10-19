# GazeFollower: MacBook feasibility probe

An isolated, local-only experiment for normal seated gaze accuracy. It does not
replace the production gaze pipeline, move the OS pointer, or train a large model.
No head-movement task is requested. Human accuracy has not yet been established.

## Method and provenance

- Upstream: <https://github.com/GanchengZhu/GazeFollower>, pinned to
  `c61ffe20cd8c16b35291e5ac198d1b76c7702290` in a separate checkout.
- The public pretrained MGazeNet `base.mnn` consumes face/eye images and rectangle
  features, producing 258 features. It is the public 7-million-training-image model,
  not the paper's 32-million-image model; published accuracy is not a promise here.
- Original `CalibrationController`: 13 training targets, 45 accepted frames each,
  1.5 s settling and 0.5 s after collection. An initial center warm-up is discarded.
- Original `MultivariateRidgeCalibration(alpha=0.1)` and `HeuristicFilter` defaults.
  Calibration labels are normalized screen coordinates, converted using the actual
  pygame drawable size. No guessed physical display dimensions are supplied.
- Face alignment uses MediaPipe Tasks. The wrapper rejects upstream's 12-landmark
  BlazeFace fallback, nonfinite features and frames failing the original eye-opening
  threshold (10). This threshold is not independently validated blink detection.
- The adapter sends BGR to face alignment and RGB to MGazeNet, matching the component
  contracts. It leaves upstream tracked files untouched and checks their commit/diff.
- Six upstream validation targets are disjoint from the training targets. Each has
  0.8 s settling and 3 s recorded measurement. Prediction feedback is hidden during
  measurement; fitting never uses validation rows. Timing uses host frame-read
  completion, not a hardware exposure timestamp.
- Model inference, camera reads and rendering are synchronous. This is an accuracy
  probe, not a 30 FPS claim or an exact reproduction of the paper's whole application.

Upstream is CC BY-NC-SA 4.0; review its license before redistribution/commercial use.
No third-party source or model binary is vendored here. See its pinned LICENSE and
the paper: <https://doi.org/10.1145/3729410>.

## Prepared local installation (2026-10-19)

- Python 3.12.13 environment: `~/.virtualenvs/eye-tracker-gazefollower-20261019`
- Support directory: `~/.virtualenvs/eye-tracker-gazefollower-20261019-support`
- External source: support directory's `upstream/`
- MediaPipe model: support directory's `face_landmarker.task`
- Installed versions: `requirements-macos.lock.txt` (Apple Silicon/macOS snapshot).
  OpenCV 4.11 avoids duplicate SDL Objective-C classes observed with OpenCV 5 and
  pygame. Production dependency pins and existing environments are unchanged.

For another installation, create a **new** Python 3.12 environment, install this
experiment's lock file, clone the upstream repository into a **new** directory at
the pinned commit, and supply an existing FaceLandmarker task model using
`--face-model`. Use `--upstream` for a different checkout location. Do not install
the upstream project's stale pinned requirements over an existing environment.
The local face model must exist before launch; no setup downloads are performed by
this runner. The upstream checkout includes the pretrained `base.mnn`.

From the project root, synthetic inference without a camera or human session:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python \
-m experiments.gazefollower_baseline.run --check
```

Start only when the participant is ready:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python \
-m experiments.gazefollower_baseline.run
```

The MacBook device name is resolved on every launch; during preparation it was
FaceTime HD Kamera, index 1, 640×480. `--camera-index` is available for explicit
selection. Index ordering can change. Display check: 1512×982 drawable/window.

## Participant flow

1. Live, unrecorded camera preview. Sit normally, check the eyes are visible and
   `HAZIR` appears. Enter opens the calibration readiness screen.
2. Press Enter **again on that screen** when ready. Follow the yellow targets with
   the eyes; no deliberate head movement. Calibration is approximately one minute,
   depending on usable frame rate. A target with insufficient usable data stops
   after 15 s; the system does not silently fabricate samples.
3. On the six-target readiness screen press Enter to begin ~23 s of measurement.
   Continue sitting normally and looking at the yellow target. No blue point yet.
4. Results are saved. Enter optionally opens yellow/blue live visualization; Enter
   cycles targets there. This view is excluded from accuracy measurements.
5. Escape exits at any stage. Exiting after measurement keeps the completed result.

## Data and interpretation

### Optional trained-location repeatability check

Append `--repeat-calibration-targets` to the launch command for the follow-up probe.
Calibration is still performed once with the original 13-target protocol. After
the separate evaluation Enter gate, 13 trained locations and six unseen locations
are shown in a reproducible mixed order (seed 20261019), approximately 73 seconds
total. The trained locations come directly from that session's calibration labels.
All evaluation samples are new; weights remain frozen and blue feedback stays hidden.

`evaluation-plan.json` records the exact order, normalized targets and timing.
Rows identify `target_set` (`repeated` or `unseen`) and its `target_id`.
In this mode `report.json` contains separate `by_target_set` summaries, requiring
all 13 and six respective targets to have sufficient data. The original six-target
mode and its report layout remain available without the flag.

Poor performance at repeated locations suggests that matching training samples did
not carry over to subsequent samples. Good repeated-location performance with poor
unseen-location performance directs attention to spatial generalization. Neither
outcome proves a cause: target geometry, fixation and time effects can also differ.
No head movement is requested, no thresholds/models are tuned, and no previous
session weights or participant records are loaded.

Each session creates a unique `validation/results/cagri-gazefollower-DATE-UUID/`.
Files use exclusive creation; historical records, Stage B2 and old environments
are not inputs. Raw images/video are not saved or uploaded. Learned features are
participant data and should remain local.

- `session.json`: model/runner hashes, upstream revision, camera/display/config.
- `calibration.npz`: accepted features (13×45×258) and normalized labels.
- `ridge_weights.npy`, `calibration-fit.json`: fitted weights and training error.
- `evaluation.jsonl`: target, host-relative time, raw/filtered unclipped pixel
  estimates, missing attempts and processing duration.
- `report.json`: per-target and equal-target-weight mean radial errors, p95,
  bias, centered RMS, availability and fraction within 30 px. Missing samples
  remain in the hit-rate denominator. Fewer than five valid samples on any of
  six targets marks the report insufficient, not successful.
- `completion.json`: completed/cancelled/failed, written when the runner exits.

Low training error is not validation accuracy. The participant is instructed to
fixate but fixation has no independent ground truth. A single same-session probe
does not establish across-session reliability or statistically controlled superiority
to the old SVR logs. Evaluate stationary accuracy first, then decide whether to
integrate this estimator or stop this approach; do not tune on these six targets
and reuse their error as an unbiased result.
