# Fixed CENTER offset — fresh live validation

## Question and scope

Does one known CENTER observation, collected immediately after a fresh nine-target calibration, provide a **fixed additive vertical offset** that improves later held-out predictions without changing y slope or directional ordering? The prior [offline experiment](../vertical_offset/RESULTS.md) made this worth testing; it did not validate a production correction. This directory contains experimental capture and evaluation code only. It does not change `src/eye_tracker/`.

## Protocol

The run reuses the [real-session validation harness](../../validation/README.md): nine 3×3 calibration targets at x/y = 0.20, 0.50, 0.80, followed by the same 16 held-out presentations (eight distinct targets twice, shuffled with seed 42). It inserts **one** exact `(0.50, 0.50)` CENTER presentation between calibration and held-out trials. There are 26 presentations total. Each uses the existing 0.8-second settling period, 1.2-second sampling period, and minimum of five usable sampling frames. These are validation-protocol settings, not production calibration requirements.

Calibration uses the current per-target median aggregator and independent-linear fitter. The additional CENTER feature is aggregated by the same median rule, then passed through the already-fitted mapping. Before any held-out target appears, the experiment computes:

```text
fixed_offset = 0.50 - baseline_prediction_y(post_calibration_CENTER_feature)
corrected_y = baseline_y + fixed_offset
```

The offset stays constant for all 16 held-out trials. The CENTER anchor is not added to the nine fitting samples and the mapping is not refitted. Each usable held-out frame passes through the existing one-frame production gaze pipeline once; its baseline `GazeEstimate` is used unchanged for baseline scoring and shifted in y for corrected scoring. Both methods therefore use the same held-out observations and have identical x predictions. No held-out target, label, error, or future checkpoint contributes to the offset. Predictions are not clipped. There is no smoothing, blink gate, or checkpoint refresh.

The on-screen display shows only the target dot and presentation status, never gaze predictions. Use normal comfortable posture and viewing distance, natural eye opening and blinking, normal glasses if needed, a reasonably centered camera, and approximately stable head position. Avoid intentional winks or deliberate posture/camera adjustments to influence the result. Look at each dot during its sampling interval. Press `q` or Esc to cancel; an incomplete run saves no report.

## Run on the development Mac

From the repository root, use the existing Python 3.12 `.venv`, installed Vision dependencies, and local Face Landmarker model:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.fixed_center_live_validation.run \
  --participant cagri --session live-1 --camera-index 1 \
  --model .venv/models/face_landmarker.task \
  --output .venv/fixed-center-live-cagri-1.json
```

Camera index `1` selected the built-in camera on Çağrı's earlier Mac setup; verify it on the machine used for this run and change the argument if necessary. Choose a **new** output filename for each session. The program refuses to overwrite an existing file and requires the result path to remain under Git-ignored `.venv/`. It does not download a model or intentionally use a network service.

## Report and interpretation

The local JSON contains camera index and resolution, measured target-window image area, elapsed time, shuffle seed, timing settings, per-presentation sampling attempts/usable/unavailable counts, total/failed camera reads, and no-face observations. It also contains fitted x/y coefficients, the calibration CENTER vertical feature, post-calibration CENTER horizontal and vertical feature medians, baseline CENTER prediction, and the fixed offset.

Calibration-fit results remain separate from held-out results. For each of the 16 held-out presentations, the report includes target y, baseline/corrected predicted y, signed and absolute vertical errors, identical x predictions, and usable-frame count. Baseline and corrected held-out summaries reuse the validation harness's mean, median, linearly interpolated p95, signed bias, and distinct-target spatial ordering definitions. The main comparison is **held-out vertical MAE, signed bias, median/p95 absolute vertical error, and y ordering**. An improvement in calibration fit or one CENTER anchor alone is not a successful held-out result. A useful candidate should improve held-out behavior without damaging ordering or substantially worsening the tail; no numeric pass threshold is predetermined.

The report contains derived human measurements and must not be committed. The program does not save raw camera frames, facial images, or video. Third-party MediaPipe telemetry behavior remains a separate unresolved privacy question described in `docs/PROJECT_STATUS.md`. One live session cannot establish cross-user benefit, production safety, stable performance, cursor usability, or acceptable transition latency. Record actual human measurements in `RESULTS.md` only after a completed real session; do not infer them from tests.
