# GazeFollower: MacBook feasibility probe

An isolated, local-only experiment for normal seated gaze accuracy. It does not
replace the production gaze pipeline or train a large model. Optional OS pointer
movement is available only after measurement and a separate Enter; it never clicks.
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
4. Results are saved and displayed as a quality summary: average filtered pixel
   distance and valid-frame percentage per region. These are measurements, not an
   automatic pass/fail accuracy threshold. Enter opens yellow/blue live visualization;
   Enter cycles targets there. This view is excluded from accuracy measurements.
5. Escape exits at any stage. Exiting after measurement keeps the completed result.

## Data and interpretation

### Optional movement-only desktop mode

Append `--control-pointer` to the command (the default six-target check takes ~23 s).
Calibration target appearance, sounds, timing, model and fitting remain unchanged.
After reviewing the quality summary, Enter enables movement using the filtered
prediction. There is no dwell detector or click call in this mode. Tab minimizes
the live window to reveal the desktop; global Escape stops even without window
focus or usable gaze. The yellow/blue view is available before switching to desktop.

The existing `PyAutoGUIPointer` platform adapter provides native OS execution and
Escape detection. The experiment action wrapper rejects out-of-bounds/nonfinite
coordinates and requires the calibrated drawable size to match the primary desktop
logical size (avoids Retina pixel/point mismatch). Insufficient evaluation data
prevents pointer activation. Successful data collection does not imply precision
sufficient for small buttons. Minimize is platform/window-manager dependent.

macOS requires Accessibility permission for the launching application. A permission
error stops pointer startup; measurements already saved remain available. Only the
new isolated environment adds PyAutoGUI 0.9.54 and its dependencies. No real OS
movement is exercised by automated tests. `pointer-control.json` records successful
activation after the quality-screen Enter; session metadata distinguishes requested
live control from measurement, during which OS control remains disabled.

### Local live diagnostics

The yellow/blue view and desktop mode now automatically write `live.jsonl` in the
new session directory. No additional calibration, targets or Enter gates are added.
Each row links one frame's host monotonic capture time, live mode, eligibility/
prediction status, raw and filtered pixel estimates, inference duration, active
model selection and pointer outcome. Estimates remain unclipped. `command_px` is
the rounded/clamped coordinate passed to a successfully returned backend move call;
it is **not** an OS cursor readback or proof that the cursor reached that position.
On a backend exception, the outcome is `backend_error`/`interrupted` with no
confirmed command coordinate; a failing call might still have had an OS effect.
Visual-only, invalid and offscreen cases explicitly record why no command was sent.

`live-trace.json` identifies the original or accepted candidate weights by path and
SHA256 and records the trace policy. `live-trace-summary.json` records logging
status, row/byte counts, skipped rows and live exit reason. These are separate from
`completion.json`, whose `completed` status describes the earlier evaluation.
No images, landmarks or feature vectors are added to the live trace. The files
remain local participant data under ignored `validation/results/`; do not upload.
Live data has no independently verified fixation and is not used to calculate
accuracy, select models, or refit calibration.

Writes use exclusive creation, buffered append and a flush about once per second
while frames arrive, plus a close flush on normal exit/Escape. There is no per-frame
terminal output or retained in-memory history. The JSONL file is capped at 32 MiB:
at the cap a single stderr warning announces that recording stops while live
control continues; the preserved prefix is never rotated or overwritten.
Write/flush/close failures propagate and stop live mode through normal resource
cleanup, with a visible error and a failed summary if storage still permits it.
Counts describe writes accepted by the buffer, not durable storage guarantees;
abrupt termination/storage failure can lose buffered rows or leave a partial final
line and no summary. Disk I/O is synchronous; this change does not claim a measured
camera FPS or real-world latency improvement.

### One-round selective calibration repair

Append `--repair-calibration` (optionally with `--control-pointer`). This requires
the default six-target check and cannot combine with `--repeat-calibration-targets`.
After a sufficiently sampled quality check, **R** selects the two highest-error
validation locations (filtered mean error) and recollects their nearest original
calibration locations by pixel distance. Coincident selections are deduplicated:
one or two calibration locations are recollected. **Enter** skips repair and keeps
the original model. There is no claimed absolute good/bad threshold.

Recollection starts after a separate Enter on its target screen. It uses the same
upstream 1.5 s settling, 45 accepted frames and 0.5 s completion wait, with a 15 s
timeout per target. All other training samples stay unchanged in a copied dataset.
A separate Ridge instance fits once. Original weights/data are never overwritten.
Initial validation samples do not enter fitting. A timeout retains the original.

A further Enter starts a fresh ~23 s six-target comparison. Old and candidate models
predict the **same new frames**, without prediction feedback. Selection uses raw,
unclipped mean pixel distance, equally weighted across targets. Initial filtered
quality scores are not the baseline for this paired comparison. Fixed initial policy:

- At least 20 valid pairs and 80% paired availability on every target.
- At least 10% reduction overall and on **each** selected problem target.
- No other target may worsen by more than 10 px.
- Failure of any condition keeps the original model; only one repair round exists.

These are engineering selection rules, not statistically validated thresholds or
a guarantee of accuracy. The comparison selects a model, so its winning score is
not an independent final accuracy estimate. No silent offset correction, global
hyperparameter changes, clicks, or repeated optimization are introduced.

The result screen identifies which model will be used and reports old/candidate
raw errors on the paired comparison. Enter then starts the selected model's live
view/movement; Escape exits. Fresh session subdirectory `repair-1/` stores the
proposal/policy/code hash, completed replacement samples, candidate dataset/weights,
fit diagnostics, comparison plan/rows and `decision.json`. Initial `report.json`
remains the original quality report, including if repair fails or is cancelled.

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
