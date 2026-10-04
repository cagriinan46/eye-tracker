# Fixed-window gaze diagnostic

## Purpose and boundary

Measure whether the **current production** horizontal/vertical representation is
stable, separable, and transferable from calibration to validation, independently
of its screen mapping. Feature instability and mapping error may coexist.

[The offline v2 benchmark](../gaze_failure_solution_benchmark/RESULTS.md) selected
no filter or mapping replacement. Its source targeting trials stopped when
production succeeded, so they cannot fairly replay an arbitrary future estimator
over the full intended target window. This protocol records a complete fixed
window regardless of predictions. It is a measurement experiment, not another
hand-crafted feature search or an interaction success test.

No live findings exist yet. No estimator, feature, calibration fitter, mapping,
smoothing, clipping, ML, cursor movement, or clicking is added to production.

## Frozen protocol

Identity: `fixed_window_gaze_diagnostic`, version **1**.

| Phase | Count | Timing and display |
| --- | ---: | --- |
| READY | 1 | SPACE required before model initialization/camera opening |
| Standard calibration | 9 | Target only; 0.8 s settling, then 1.2 s sampling |
| Validation cue | 27 | Cue only for 0.75 s; instructional, never accuracy-gated |
| Validation target | 27 | Target only for 3.0 s; all observations recorded |
| Neutral transition | 27 | Blank screen for 0.5 s |

Both calibration and validation use the nine centers at
`x, y ∈ {0.2, 0.5, 0.8}`. Calibration remains the established row-major grid.
Validation has three blocks, each containing every target exactly once. The
existing v1/v2 schedule is reused: `random.Random(20261006).sample` generates one
permutation and each later block rotates it by three positions. The order is
fixed before collection, never selected from results.

For non-center targets the cue is `(1-target_x, 1-target_y)`; for `(0.5, 0.5)` it
is `(0.2, 0.2)`. The target immediately replaces the cue. No extra validation
settling delay is added; the **entire** three-second window is the primary record.
The cue is not an acquisition task. No gaze cursor, predictions, debug text,
acceptance region, dwell timer, success, timeout, or reset failure is shown or
computed during collection. Poor predictions and unavailability cannot skip,
shorten, extend, or terminate a target window. q/Esc can abort the whole run.

Nominal timed duration is `9×2.0 + 27×(0.75+3.0+0.5) = 132.75 s`, approximately
**2 min 13 s**, plus startup, READY waiting, and display/processing overhead.
Allow approximately 2–3 minutes after SPACE. The GUI runs elapsed-time deadlines
independently of the single camera/processing worker. OS scheduling/rendering is
not a precision display clock: actual onset/end and deadline overrun are logged.
A slow camera call cannot gate target removal. Only observations begun and
completed inside the nominal sampling window enter its sample log; queued,
already-completed observations are drained without waiting for future frames.
Unavailable attempts inside the window are retained, never interpolated.

## Human instructions — read before SPACE

- This is a **measurement experiment, not a game**. Target acquisition is never
  graded, and gaze output will not be shown.
- Use natural, relaxed eye opening. **Do not intentionally narrow or widen** your
  eyes. Blink naturally.
- Sit in your normal comfortable computer-use posture. Keep the physical setup
  reasonably consistent after calibration; do not intentionally steer with your
  head. You need not rigidly freeze yourself.
- During calibration, look at the **center** of the visible target until it goes
  away.
- During validation, look at the fixation cue while it is shown. When the target
  replaces it, look at the **center of the target** and continue looking there
  for the entire time it remains visible. There is no success/failure task.
- The brief blank interval is neutral, not feedback about performance.
- Press SPACE on READY to start; q/Esc aborts. Do not change setup midway through
  a session. Every new run gets a fresh calibration.

## Production path and calibration

Reuse `OpenCVCameraSource` → `MediaPipeFaceLandmarkExtractor` → production
`eye_geometry_from_observation` → production `extract_binocular_features`.
Calibration uses `collect_features_once`, per-target independent medians,
the established minimum five usable observations per calibration target, and
`fit_session_calibration` / production `IndependentLinearMapping`.

Validation uses `process_gaze_frame` unchanged. An experiment-only observation
tap reads the same frame/landmarks and calls the identical production feature
extractor to retain h/v alongside the gaze result. It does not feed anything back
or change output. The fitted map is `x = x_slope*h + x_intercept`,
`y = y_slope*v + y_intercept`. Only the nine calibration medians fit it; no
validation target labels enter calibration. All predictions and errors remain
**unclipped**. The worker is a recording/display scheduling boundary, not a
filter: it retains every eligible usable/unavailable observation.

## Local capture and commands

Use the existing local Face Landmarker model
`.venv/models/face_landmarker.task` and installed vision dependencies. Camera
indices are machine-specific; these commands use Çağrı's established index 1.
Run **after human review and merge**, from the repository root:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.fixed_window_gaze_diagnostic.run --participant cagri --session diagnostic-1 --camera-index 1 --output .venv/fixed-window-gaze-cagri-diagnostic-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.fixed_window_gaze_diagnostic.run --participant cagri --session diagnostic-2 --camera-index 1 --output .venv/fixed-window-gaze-cagri-diagnostic-2.json
```

The CLI supports independent participant/session identifiers; the same fresh
calibration and frozen schedule apply to every run. Existing files are never
overwritten. Aborted/failed attempts retain available partial numerical records
in a sibling `.invalid.json`; that marker is rejected by analysis. Preserve and
document technical invalidations/protocol violations rather than silently
replacing inconvenient measurements. Accuracy is not a validity gate.

## JSON record

Session metadata includes protocol name/version, participant/session, seed,
calibration and validation timings, cue assignment, target centers, READY usage,
camera index/resolution, window dimensions, calibration-only coefficients,
elapsed time, camera-read counts, failed reads, and no-face observations.

Each presentation retains identity, block/order, target/cue coordinates as
applicable, actual onset/end, and its numerical samples and summary. Each sample
contains target/block identity, absolute monotonic processing-completion time,
presentation-relative time, measurement-start time, frame timestamp when
available, camera-frame availability, production h/v, raw mapped x/y, separate
feature/gaze availability, and the production unavailable reason. Calibration
has no mapped prediction until the map is fitted. Camera counters include
settling, cues, and transitions; sample availability uses logged target attempts
only. No personally unnecessary face geometry is retained.

Timestamps are **not camera-to-photon latency**. Frame time and completion time
are separate; sampling membership requires measurement start and completion
inside the nominal interval. Border-crossing in-flight frames are excluded
consistently, not classified by gaze accuracy. Display end/overrun allows later
inspection of timing faults; no hidden timing-tolerance threshold is declared.

## Predeclared analysis

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.fixed_window_gaze_diagnostic.analysis .venv/fixed-window-gaze-cagri-diagnostic-1.json --output .venv/fixed-window-gaze-diagnostic-1-analysis.json
PYTHONPATH=src:. .venv/bin/python -m experiments.fixed_window_gaze_diagnostic.analysis .venv/fixed-window-gaze-cagri-diagnostic-1.json .venv/fixed-window-gaze-cagri-diagnostic-2.json --output .venv/fixed-window-gaze-comparison.json
```

Analysis recomputes summaries from raw observations, verifies the complete
9-calibration/27-validation schedule and timings, rejects incompatible protocol
metadata, and refits calibration solely to verify the saved mapping. Mapped
samples must agree with that mapping. Empty attempt logs are incomplete;
availability losses otherwise remain measured evidence. No/all-but-one usable
samples in a validation window are flagged as signal limitations, not replaced
with fabricated zero errors. Incomplete/singular calibration is a technical
invalidation under the established calibration convention.

Primary summaries use the **full [0,3) s** target window:

1. **Presentation feature space:** horizontal/vertical median, MAD (median
   absolute deviation from the median), IQR (p75−p25), and p95−p05; percentiles
   use the repository's linear interpolation convention. Also first-half
   `[0,1.5)` and second-half `[1.5,3)` medians and signed second−first shift.
2. **Separability:** per-block and pooled vertical row/horizontal column medians
   at levels 0.2/0.5/0.8. Each presentation has equal weight for these medians.
   Infer each axis's sign from strict calibration-level ordering; if calibration
   is flat/nonmonotonic, report no inferred direction. Report signed adjacent
   separations, ordering, minimum absolute separation, and each target's IQR
   divided by that separation. Raw sample-level distributions/quantiles are
   reported alongside presentation-level distributions to inspect overlap.
   Ratios are descriptive; zero separation gives no finite ratio.
3. **Calibration transfer:** exact-coordinate matching, calibration median versus
   each validation block and median across three block medians; signed/absolute
   shifts, pooled target summaries, row and column summaries.
4. **Repeatability:** per-target block1/2/3 h/v medians, all three signed pair
   differences, maximum absolute shift, block3−block1, strict directional drift,
   and mapped equivalent residual changes using the unchanged fitted slopes.
5. **Mapping:** trial medians, signed/absolute errors, sample-weighted x/y MAE,
   signed biases, mean/median/p95 Euclidean error, grouped by row, column,
   individual target, and block. Calibration residuals and raw spreads are also
   recomputed; diagnostic residuals never fit a correction.
6. **Availability/timing:** usable/unavailable target attempts, reasons, camera
   failures/no-face counts, actual window timings, and low-signal presentations.
7. **Session comparison:** keep sessions separate, show per-target median feature
   changes. Do not pool raw feature scales across differently calibrated runs or
   claim population reliability.

**Secondary, declared before collection:** report separability and mapped
residuals on `[0.8,3)` s. The cue-to-target gaze movement can affect early samples
and first-half shifts; those are not automatically evidence of feature drift.
The settled interval does not replace primary full-window results or shorten
recording. Trial/target summaries retain all primary observations.

No automatic statistical significance test, clinical threshold, quality gate,
feature correction, alternative mapping, or engineering pass/fail is selected.

## Interpretation framework

| Outcome | Evidence to inspect | Bounded next direction |
| --- | --- | --- |
| A: feature representation implicated | Same-target h/v changes between calibration and validation; block drift; overlapping row distributions; inconsistent ordering | Bounded representation/normalization redesign |
| B: mapping structure implicated | Stable ordered raw features and small same-target transfer shifts, but systematic mapped residuals by row/column/position | Bounded calibration/mapping redesign |
| C: both | Representation instability and systematic mapped error coexist | Prioritize the earlier representation layer unless evidence establishes a clearer dependency |
| D: inconclusive | Tracking loss, protocol violation, incomplete windows, insufficient signal, or ambiguous geometry | Report the measurement limitation; do not force A/B/C |

No numerical definition of “small” or “material” is invented here. Inspect
feature spreads and transfer shifts relative to measured adjacent-level margins,
plus mapped residual magnitudes and session consistency. Target identity is
experimental gaze intent, not an independent eye-tracking fixation ground truth.
Neither ordered features nor mapped bias alone establishes a physical cause.
The early cue movement, normal blinking, temporal autocorrelation, and
single-participant design limit causal and population inference.

## Privacy and checks

Only derived numerical observations are saved locally under Git-ignored
`.venv/`; no raw images/video, uploads, or OS input. These numerical data may
still be sensitive. Existing MediaPipe telemetry uncertainty remains documented
in [PROJECT_STATUS](../../docs/PROJECT_STATUS.md); the harness does not resolve it.
No new dependency or production file change is required.

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
git diff --check
```

Synthetic tests cover timing independent of gaze/camera queues, READY-before-
camera orchestration, full-window records, schedule/cue identity, feature spread,
ordering, transfer/drift, unclipped residuals, unavailable data, deterministic
session comparison, and invalid/protocol mismatch rejection. Live camera/UI
behavior and scientific conclusions await the two human sessions.
