# Offline one-point vertical offset experiment

This experiment asks whether a single known CENTER presentation can correct an additive vertical bias in the existing session-local independent-linear gaze estimate. It uses only the two previously recorded Issue #46 drift sessions. It does not collect camera data, change the slope, fit a new mapping, or modify production Vision/Gaze code.

## Reproduce

From the repository root, with the existing Python 3.12 environment:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_offset.report \
  .venv/vertical-drift-cagri-A.json .venv/vertical-drift-cagri-B.json
```

The command prints separate session results as JSON and writes no files. The input files contain derived human measurements, are Git-ignored, and must stay local. If they are absent, the published numerical results cannot be reproduced from committed source alone. No raw image or video is read or saved.

## Predeclared comparison

For each session, the analyzer reconstructs the nine calibration medians with the production aggregator, refits the existing independent-linear mapping, verifies its stored coefficients, and replays the 16 held-out trial predictions. The replay must match the saved baseline predictions before any correction is scored.

Every candidate uses `offset = known_center_y - baseline_prediction(center_feature)` and `corrected_y = baseline_y + offset`. The known CENTER y is 0.50. The slope, x prediction, per-trial median rule, and unclipped output remain unchanged. Signed vertical bias means prediction minus target.

The three anchors are: (1) the exact calibration CENTER median, (2) checkpoint 0 immediately after calibration, and (3) the most recent completed CENTER checkpoint for each following held-out block. For refresh, checkpoint 0 applies only to the next four trials, checkpoint 1 to the next four, and so on through checkpoint 3. Checkpoint 4 occurs after all 16 trials and cannot score any earlier trial. The analyzer reads recorded chronological presentation order, requires all expected trials/checkpoints and four trials per applicable block, and rejects a held-out trial before checkpoint 0. No held-out target or error fits an offset or selects a parameter.

Metrics are per session and based on 16 held-out presentation medians: vertical MAE, signed bias, median and p95 absolute error, and descriptive y ordering using the validation protocol's distinct-target pair rule. Refresh also reports the four chronological blocks separately. A block's ordering uses only target pairs represented within that block, so its denominator can be less than 21.

The work tests an additive-output correction, not the physical cause of feature movement. Two short sessions from one person cannot establish cross-user effectiveness, live latency, stable fixation, or production suitability. See [RESULTS.md](RESULTS.md).
