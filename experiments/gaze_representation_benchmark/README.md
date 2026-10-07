# Gaze representation benchmark — Stage B1 only

Implement and freeze exactly R0 (production), R1 (3D face canonicalization) and
R2 (periocular affine canonicalization). The exact definitions, numerical guards,
future metrics and unchanged holdout gates are in
[REPRESENTATION_FREEZE.md](REPRESENTATION_FREEZE.md), under the existing
[preregistration](../raw_geometry_gaze_diagnostic/PREREGISTRATION.md).

Production code is unchanged. There is no formula search, ML, temporal filter,
validation fitting, winner selection or outcome report. All geometry remains
local; captures are not committed. The development capture is only used for
calibration availability, reconstruction and numerical conditioning. No human
capture or additional collection is triggered.

## API boundaries

- `representations.py`: numerical frame/reference input; per-eye and binocular
  features or explicit unavailability. No labels, time, conditions or screen maps.
- `calibration.py`: `parse_presentations(capture_calibration_array)` and
  `fit_candidates(tuple_of_CalibrationPresentation)`; only nine ordinary
  calibration presentations. Fit each candidate independently with production
  per-presentation medians and independent-linear mapping.
- `analysis.py`: a fixed-path development-only prefix reader. It decodes identity
  and the calibration array, then stops before validation data. Other paths and
  symlinks are rejected before opening. It does not call the full-capture
  inspection/analysis functions, which would traverse validation.

From repository root, optional calibration-only sanity inspection:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.gaze_representation_benchmark.analysis
```

There is deliberately no capture-path CLI argument, holdout switch or outcome
command. Output contains calibration sample availability, mapping evaluability
and numerical conditioning only; no target accuracy, residuals or ranking.
The allowlisted path is `.venv/raw-geometry-gaze-cagri-geometry-1.json`.

## Dependencies and checks

NumPy, already used in Experiment 006, is explicitly listed in
`requirements-dev.txt` for experiment SVD/least squares and deterministic CI
tests. No production or camera dependency is added. Transforms use float64;
the freeze documents exact numerical rank conventions.

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
git diff --check
```

Synthetic tests cover production reconstruction, similarity/reflection rules,
affine contour/iris equivalence, references, missing geometry/rank failures,
calibration-only mapping and the guarded prefix reader. They never access a
participant capture or the real holdout path.

## Freeze handoff

Record the full freeze commit SHA in the task report and PR. Do not amend or
rewrite it after holdout outcomes are opened. Stage B1 stops after committing,
pushing and opening the PR. Stage B2 requires a separate instruction; only then
may the frozen definitions be evaluated once against geometry-2. Each later
session builds its own references and maps from that session's calibration.
