# Issue #50 — Alternative vertical calibration mappings

This is an **offline** comparison of the current session-local independent-linear y mapping and one experiment-only monotonic piecewise-linear y mapping. It addresses calibration fit, not the cause of later vertical-feature movement. It does not modify the production fitter, estimator, validation harness, or horizontal mapping.

## Input and run

Use the two completed, separately calibrated Çağrı sessions from Issue #46. They contain derived numerical sampling rows for nine calibration targets and 16 held-out trials per session. No new camera run is required. From the repository root:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_mapping_evaluation.report \
  .venv/vertical-drift-cagri-A.json .venv/vertical-drift-cagri-B.json
```

The script prints a numerical JSON report to stdout; it does not create an output file. The input files are Git-ignored and must not be committed. It never opens a camera or reads/saves images or video.

## Fair comparison

For each session independently, the nine calibration-target feature pairs are reconstructed as medians of that target's usable frames, using the existing production aggregator. The current production independent-linear mapping is refitted from those same nine samples and checked against the coefficients recorded in the human run. The analyzer also replays its 16 held-out trial predictions and verifies that they match the saved baseline. A mismatch stops analysis.

The only new candidate uses the same nine **calibration** samples. For each of the top, center, and bottom y rows, its feature anchor is the median of that row's three per-target vertical-feature medians. The anchor's y is the known row target y. Anchors must be strictly monotonic in feature value as screen y increases; nonmonotonic or coincident features cause a clear error instead of an invented mapping. The model linearly interpolates between top→center or center→bottom anchors. Values outside the outer anchors extend the nearest segment linearly; predictions are **not clipped**. This policy is declared before inspecting held-out outcomes and reveals extrapolation failures. There is no fitted correction constant, filtering, smoothing, or model search.

For both candidates, x always comes from the original independent-linear mapping. Held-out samples are **never** used to fit anchors, select parameters, recenter, or correct bias. Each usable validation frame is replayed through the candidate; the existing validation summarizer then takes the per-trial median prediction and computes errors and spatial ordering with the same metric definitions as Experiment 006. Calibration-target fit and distinct held-out results are reported separately. Signed residual/bias means **prediction minus target**; MAE, median absolute error, and p95 absolute error are nonnegative. A lower calibration-fit error alone is not evidence of better held-out mapping.

## Scope and limitations

The experiment uses two short sessions from one person. It is not a statistical or cross-user validation, and it cannot isolate calibration-model effects from the already observed calibration-to-use feature changes. The two held-out evaluations are repeated observations from the same local protocol, not independent population samples. The piecewise model is an experimental candidate only; even a favorable result would require further validation before any production change. See [RESULTS.md](RESULTS.md) for measured outcomes and the bounded conclusion.
