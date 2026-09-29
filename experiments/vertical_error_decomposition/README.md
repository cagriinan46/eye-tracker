# Vertical error decomposition (Issue #48)

This is an offline diagnostic of the two completed Çağrı sessions from Issue #46. It does not capture camera data, change production gaze behavior, or estimate a correction. Input is the Git-ignored, derived-numerical JSON in `.venv/`.

Run from the repository root with the existing virtual environment:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_error_decomposition.report \
  .venv/vertical-drift-cagri-A.json .venv/vertical-drift-cagri-B.json
```

The analyzer reconstructs the nine per-target median calibration samples and fitted mapping using the existing production aggregation and fitter. It refuses a dataset if reconstructed coefficients disagree with those stored by the human run. Calibration residuals are `target - prediction`; held-out signed bias and CENTER accounting use `prediction - target`, the opposite sign.

At each identical `(0.5, 0.5)` CENTER checkpoint, the model-output identity is exact:

```text
checkpoint predicted - 0.5
  = (calibration-center predicted - 0.5)
  + (checkpoint predicted - calibration-center predicted)
```

The second term is the output change attributable *within this fixed fitted linear model* to the measured feature change; it does not identify the physical cause of that change. A zero arithmetic remainder is not evidence that all sources of gaze error are known.

Held-out targets are not the calibration CENTER target. Some have different y levels, and those with y=0.5 have different x positions. The corresponding calibration-time feature for each held-out target was not measured at that same target. Thus held-out MAE and bias can be reported, but a unique held-out split into fit residual, later drift, and remaining error cannot be calculated. The analyzer deliberately reports the attributable held-out remainder as unavailable rather than estimating it from unmatched targets.

Only numerical features and predictions are read; images and video are neither loaded nor saved. Do not commit the human session JSON or generated reports containing per-frame data. The summarized observations are in [RESULTS.md](RESULTS.md).
