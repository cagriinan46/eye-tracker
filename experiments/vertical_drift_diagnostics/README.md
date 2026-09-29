# Calibration-to-use vertical-feature drift — Issue #46

This is a bounded Phase 1 **diagnostic experiment**, not a gaze correction. Issue #44 found that Çağrı's vertical calibration targets remained ordered in two sessions, yet Session B's held-out center feature was about `-0.00464` below its calibration-center value. With that session's fitted y slope, the difference was close to the observed signed y bias. The cause remains unknown, and this finding does not explain Fatih's earlier near-flat predictions.

## Question and protocol

When does the center-target vertical feature move after calibration, and do per-eye, eyelid-opening, or coarse face-position measures move with it?

The run reuses the [production validation protocol](../../validation/README.md): nine calibration targets on the `0.20/0.50/0.80` grid, then the same eight held-out interstitial targets twice in the same shuffled order (seed 42 by default). Each presentation has 0.8 seconds of settling followed by 1.2 seconds of sampling and requires at least five usable observations. These are **experimental** settings, not product requirements. A `(0.50, 0.50)` CENTER target appears immediately after calibration (checkpoint 0) and after each consecutive block of four held-out trials (checkpoints 1–4). The 16 held-out trials are not reordered; predictions are never shown to the participant. The full sequence is 30 presentations and lasts roughly one minute plus startup.

Run two fresh-calibration sessions on Çağrı's development Mac. For A, sit in a normal comfortable posture. Before B, leave/reset/reseat normally. Use natural blinking and eye opening, normal glasses use, a reasonably centered camera, and an approximately stable head. Do not deliberately change eye opening, camera angle, head tilt, or posture to seek a result. Look at each on-screen dot. Press `q` or Esc to cancel; incomplete runs save no dataset. Fatih/cross-user validation is deferred.

## Setup and commands

Use the existing Python 3.12 `.venv`, installed production Vision dependencies, and local Face Landmarker model at `.venv/models/face_landmarker.task`. From the repository root:

```bash
PYTHONPATH=src .venv/bin/python -m experiments.vertical_drift_diagnostics.run --participant cagri --session A --camera-index 1 --output .venv/vertical-drift-cagri-A.json
```

After leaving/reseating, run the same command with `--session B` and `--output .venv/vertical-drift-cagri-B.json`. Each output path must be new and inside Git-ignored `.venv/`; an existing file is never overwritten. `--camera-index` is explicit because camera ordering varies. `--model` and `--seed` may be supplied, but changing the seed would alter the held-out order. Use seed 42 for both planned sessions.

Compare both completed datasets with:

```bash
PYTHONPATH=src .venv/bin/python -m experiments.vertical_drift_diagnostics.report .venv/vertical-drift-cagri-A.json .venv/vertical-drift-cagri-B.json
```

## Derived measurements and limits

Each sampling attempt records availability, monotonic time, target and checkpoint identifiers, binocular horizontal/local-axis vertical features, left/right vertical features, numerical lid-point opening, and a coarse face-center-y proxy. The production median aggregator, session fitter, and gaze estimator remain unchanged. The exact calibration-center target median is the reference; checkpoints additionally compare to checkpoint 0. Each checkpoint reports usable count, median, range, IQR, per-eye/opening/position medians, and descriptive between-checkpoint co-movement. Held-out prediction metrics are retained to relate feature movement to mapped y behavior.

Camera frames and biometric imagery are never saved or uploaded. Derived numerical JSON stays local and may still be sensitive; do not commit it. The current vendor-neutral observation has no blink blendshape score, so that optional diagnostic is omitted rather than changing a production contract. No blink filtering, smoothing, or correction is applied. Unlike Experiment 006, the current production path does not have its experimental blink gate.

Five fixed-center checkpoints can describe an immediate shift or changes associated with elapsed time, intervening gaze movement, per-eye behavior, opening, or face position. They cannot isolate causes: time and gaze movement are not independently controlled, the face-center proxy cannot separate pitch from translation, and correlation does not establish causation. Two short sessions from one user do not support statistical or cross-user claims. [RESULTS.md](RESULTS.md) records only completed measured evidence.
