# Phase 1 real session calibration validation

This is Issue #42's controlled validation harness, not the production calibration GUI or a cursor controller. It composes the current production camera, landmark, eye-feature, median-aggregation, independent-linear calibration, and gaze-pipeline components. No algorithm or production contract is changed here.

## Protocol

The target positions and timing come from [Experiment 006](../experiments/006-2d-gaze-mapping/gaze_mapping_experiment.py), and its sample/metric rules come from [its analyzer](../experiments/006-2d-gaze-mapping/analyze_mapping.py). Nine calibration positions form a 3×3 grid with x and y each at 0.20, 0.50, 0.80. The eight separate held-out positions are (0.35, 0.35), (0.65, 0.35), (0.35, 0.65), (0.65, 0.65), (0.50, 0.35), (0.65, 0.50), (0.50, 0.65), and (0.35, 0.50). Each held-out position appears twice in a reproducibly shuffled order (default seed 42), giving 16 validation trials.

Each presentation has 0.8 seconds to settle and 1.2 seconds to sample. At least five usable samples are needed for each presentation; this is an **experiment protocol** rule, not a production calibration requirement. Calibration uses the existing per-axis median aggregator and session-local independent-linear fitter. During held-out trials, each usable frame goes through the existing `process_gaze_frame` pipeline, then the trial's predicted x/y are summarized by per-axis medians. Because the current mapping is independent linear, this gives the same per-axis median prediction as mapping median features; no mapping formula is duplicated. Calibration-fit and held-out metrics are reported separately.

Look at the displayed dot with a comfortable normal viewing distance, natural eye opening and blinking, approximately stable head, no intentional winks, and glasses worn normally if needed. The user sees only targets, not predictions. Press `q` or Esc to cancel; an incomplete run writes no result. The camera index is always selected at runtime because camera ordering varies by machine.

## Setup and run

Use the repository's Python 3.12 `.venv` with its already-configured production Vision dependencies and a local Face Landmarker model. From the repository root, after installing the existing Vision dependency group if needed, run:

```bash
PYTHONPATH=src .venv/bin/python -m validation.real_calibration --camera-index 1 --model .venv/models/face_landmarker.task --output .venv/real-calibration-cagri.json
```

Index `1` selected the built-in camera on Çağrı's development Mac during Phase 0, but is not universal. Fatih must substitute his own available camera index and use a distinct ignored output name such as `.venv/real-calibration-fatih.json`. The output path must be a new path under `.venv/` to keep human-derived numerical results Git-ignored. Omit `--output` to print the completed report without saving it. The script does not download a model or use a network service during the run.

The JSON report includes camera index/resolution, target-window image dimensions, total/successful/failed camera reads and no-face counts (including settling), sampling **attempts** and usable counts per presentation, separate calibration-fit and held-out trial metrics, and the protocol difference below. A sampling attempt may be a failed camera read and must not be equated with Experiment 006's captured-frame count. For each trial it reports actual/predicted normalized coordinates, horizontal and vertical absolute error, normalized 2D Euclidean error, and window-pixel-equivalent error. Each error type has mean, median, and linearly interpolated p95 summaries; signed x/y bias and descriptive ordering of distinct held-out targets are also reported. Pixel-equivalent error uses the measured target-window image area, **not necessarily monitor hardware pixels** or physical viewing angle. There is no predetermined accuracy pass threshold.

## Protocol difference and limitations

Experiment 006 used an **experimental** blink/near-closure gate. The production Vision/Gaze path has no validated blink filter or blendshape signal in its public contracts, so this harness **does not apply that gate**. Missing frames, missing face, and invalid features are not filled in; unavailable estimates are counted. Comparisons with Experiment 006 must mention this difference. The harness also reports total reads and no-face observations including settling, unlike Experiment 006's sampling-frame count.

No raw camera images or video are saved or uploaded. An optional local JSON contains derived target/prediction metrics, which may still be sensitive and must not be committed. One person/session cannot establish general accuracy, accessibility usability, production readiness, cross-session calibration persistence, or multi-user validity. Record Çağrı's result in the PR, then Fatih's independent run separately before merge; do not average the users together.
