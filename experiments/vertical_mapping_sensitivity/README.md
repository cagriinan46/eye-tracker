# Offline vertical mapping sensitivity diagnostic

## Question and scope

Does a high fitted independent-linear y slope coincide with a narrow or weakly separated 3×3 calibration vertical-feature range? How strongly does that slope convert a measured feature change into normalized screen-y movement? This is an **offline diagnostic**, not a correction or a physical-cause test. It uses existing derived-numerical human reports only. No camera collection, production change, new mapping family, clipping, smoothing, gate, offset, or ML is involved.

## Inputs and reproduction

The seven locally available, Git-ignored JSON reports are two fixed-CENTER live sessions (`fixed-center-live-cagri-{1,2}.json`), two Issue #44 collapse sessions (`vertical-collapse-cagri-{A,B}.json`), two Issue #46 drift sessions (`vertical-drift-cagri-{A,B}.json`), and the Issue #52 controlled repeat run (`vertical-position-cagri-controlled-1.json`). All are Çağrı sessions on the development Mac. No Fatih numerical diagnostic dataset is present locally. The controlled repeat run has no 16-trial held-out validation block and is reported with held-out metrics absent.

From the repository root:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_mapping_sensitivity.report \
  .venv/fixed-center-live-cagri-1.json .venv/fixed-center-live-cagri-2.json \
  .venv/vertical-collapse-cagri-A.json .venv/vertical-collapse-cagri-B.json \
  .venv/vertical-drift-cagri-A.json .venv/vertical-drift-cagri-B.json \
  .venv/vertical-position-cagri-controlled-1.json
```

The command prints one JSON array with independent per-session records and writes no files. Input files remain local; do not commit derived human data. If they are unavailable elsewhere, the measurements in [RESULTS.md](RESULTS.md) cannot be regenerated from prose alone.

## Method

For Issue #44, the analyzer uses the original recorded nine per-target median calibration features. For #46 and #52, it rebuilds those nine medians from recorded usable calibration frames with the existing production aggregator and verifies the fitted mapping against the stored coefficients. The two live reports save calibration predictions, not all calibration feature medians. For these **calibration targets only**, it exactly inverts the existing independent-linear identity `predicted_y = y_slope * vertical_feature + y_intercept` to obtain `vertical_feature = (predicted_y - y_intercept) / y_slope`. The recorded calibration CENTER feature is checked against the reconstructed value. This inversion requires a finite, nonzero slope; it is algebraic reconstruction of a saved fitted-model output, not a new measurement or fit. The live reports do not permit recovery of the raw frame distribution.

For each session the analyzer prints all nine calibration target features, the median/min/max and across-X spread of each row, the full nine-target feature span, signed top-to-center and center-to-bottom row-median separations, and their minimum. It reports the stored or reproduced calibration-fit y MAE and y ordering, held-out baseline y MAE/median/p95/ordering when present, and the fitted y slope/intercept. Row spread is `max(feature) - min(feature)` across the three X positions; the fixed row-major calibration order means it is not an isolated X effect.

Repeated identical-target comparisons use the first and last presentations in chronological order, computing **later minus earlier**. For #44/#46/#52, each usable presentation's original vertical frames are reduced by median; its output change is `y_slope * feature_change`, using the session's saved slope. The diagnostic also reports per-target feature span where more than two presentations exist. The live JSONs have only baseline per-trial y predictions, so their repeated-target **prediction differences** are reported; their actual repeated-target feature differences remain unavailable. Held-out predictions are never used to reconstruct calibration features. Missing held-out or raw repeat measurements remain `null`/absent in the report.

The fixed illustrative feature changes 0.001, 0.003, and 0.005 are multiplied by each session's slope. These are sensitivity examples, not assumed observed changes or tuned thresholds. A vertical feature can change independently of the mapping; the slope only determines how strongly a given change affects predicted y. This accounting identity does not show what caused the feature change or the fitted slope. All comparisons are descriptive across short sessions from one participant, with differing checkpoint/repeat protocols. They do not establish a statistical relationship, physical cause, cross-user reliability, or a production policy.
