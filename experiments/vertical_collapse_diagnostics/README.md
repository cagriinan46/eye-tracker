# Vertical gaze collapse diagnostics — Issue #44

This is a Phase 1 **diagnostic experiment**, not a production change. Real calibration validation on two machines showed different vertical behavior: Çağrı's held-out y ordering was 21/21 with vertical MAE about 0.1257 and signed y bias about -0.1229; Fatih's was 4/21 with y predictions clustered near 0.50–0.518, despite vertical MAE about 0.1170. The latter error alone does not establish useful vertical tracking. The question is where the vertical information is lost: before aggregation, during aggregation, or after mapping.

## Protocol

Use the same [merged validation protocol](../../validation/README.md): nine calibration targets on the 0.20/0.50/0.80 grid, eight distinct interstitial validation targets shown twice (16 held-out trials), seed 42 by default, 0.8 s settling and 1.2 s sampling per presentation, and at least five usable observations per presentation. The existing production Vision feature extraction, per-target median aggregation, independent-linear session fitter, and gaze estimator are called; none is reimplemented. The familiar target window is validation-only tooling. Camera index is explicit at runtime.

Each participant should complete Session A in a normal, comfortable posture. Before Session B, leave/reset/reseat and fit a **new** calibration in another normal posture. Keep the camera reasonably centered, head approximately stable, natural eye opening/blinking, normal glasses usage, and no intentional winks. Do not deliberately change eye opening, tilt, camera angle, or posture to obtain a desired result. The four desired datasets are Çağrı A/B and Fatih A/B, kept separate. Press `q` or Esc to cancel; an incomplete run saves no dataset.

From the repository root, use the existing Python 3.12 `.venv`, production Vision dependencies, and local Face Landmarker model:

```bash
PYTHONPATH=src .venv/bin/python -m experiments.vertical_collapse_diagnostics.run --participant cagri --session A --camera-index 1 --output .venv/vertical-collapse-cagri-A.json
```

After leaving/reseating, run again with `--session B` and a distinct output such as `.venv/vertical-collapse-cagri-B.json`. Fatih substitutes his own camera index, participant ID, and output filenames. `--model` defaults to `.venv/models/face_landmarker.task`; `--seed` defaults to 42. The output path must be new and under Git-ignored `.venv/`.

Summarize one or more completed numerical datasets without pooling the people:

```bash
PYTHONPATH=src .venv/bin/python -m experiments.vertical_collapse_diagnostics.report .venv/vertical-collapse-cagri-A.json .venv/vertical-collapse-cagri-B.json
```

## Measurements and interpretation

Per sampling attempt, the local JSON records participant/session, phase, target/trial, sequence and monotonic time, status, binocular horizontal and local-axis vertical features, optional left/right eye features, normalized lid-point opening, coarse face-center y proxy, and held-out predictions when available. It also records per-calibration-target aggregated feature medians, fitted x/y slopes/intercepts, calibration-fit and held-out metrics, and read/no-face counts. Camera frames, photographs, video, and facial imagery are **never written or uploaded**. The numerical data may still be sensitive; do not commit it.

Analysis reports each calibration row's raw and aggregated medians, range, IQR and overlap; row ordering; held-out x/y prediction spans, ordering, MAE and signed bias; and same-user session offsets. Where available, it reports *within-target association* of vertical feature with lid opening and the coarse head-center proxy. Association is not causation. The head-center proxy cannot distinguish head translation from pitch. Blink blendshape scores are omitted because the current vendor-neutral `LandmarkObservation` does not expose them; changing a production contract for optional diagnostics is outside this issue.

There is no invented collapse threshold or statistical-significance claim. The result can support a finding that information is lost before calibration, after calibration, drifts across sessions, correlates with a measured diagnostic, or remains inconclusive. Do not introduce bias correction, smoothing, filtering, new models, or production thresholds based on this experiment alone. Unlike Experiment 006, the current production path has no validated experimental blink gate; that protocol difference remains in these runs.

See [RESULTS.md](RESULTS.md) for measured outcomes, once the independent human sessions are completed and reviewed.
