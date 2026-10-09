# Gaze representation benchmark

Implement and freeze exactly R0 (production), R1 (3D face canonicalization) and
R2 (periocular affine canonicalization). The exact definitions, numerical guards,
future metrics and unchanged holdout gates are in
[REPRESENTATION_FREEZE.md](REPRESENTATION_FREEZE.md), under the existing
[preregistration](../raw_geometry_gaze_diagnostic/PREREGISTRATION.md).

Production code is unchanged. There is no formula search, ML, temporal filter,
validation fitting or production winner selection. All geometry remains
local; captures are not committed. Stage B1 used the development capture only for
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

The B1 reader has no capture-path CLI argument, holdout switch or outcome
command. Its output contains calibration sample availability, mapping evaluability
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

## Stage B2 — separately authorized one-shot evaluation

The immutable representation commit is
`c4ad261b63fcce3b3998ce8335f8d81fa2118b32`. PR #70 was squash-merged: its merged
tree is byte-identical to this original freeze; the original commit is preserved
but is not an ancestor of `main`.

`evaluate.py` accepts only the final local geometry-1 and geometry-2 captures
under `.venv`, rejects alternative paths/symlinks, and validates both identities,
complete schedules, raw schema, R0 reconstruction and fresh calibration before
outcome calculation. Frozen source files are checked byte-for-byte against the
original commit. References and all binocular/monocular maps use each session's
calibration only; validation projection follows fitting. `evaluation_metrics.py`
performs the frozen window/transfer/ordering/error/coverage calculations without
any fitting or representation calls. Common-frame analysis preserves maps.

After committing and reviewing the evaluator, the authorized one-shot command is:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.gaze_representation_benchmark.evaluate
```

The runner requires a clean working tree, seals the evaluator commit and capture
hashes in ignored `.venv/stage-b2-one-shot-evaluation.json` before outcomes, then
writes aggregate-only `results_summary.json` and deterministic `RESULTS.md`.
Existing marker/output prevents another run, including after failure. Do not
delete the marker, rerun the holdout, or tune anything after outcomes appear.
The same five primary criteria must have support in both native and common-frame
coverage; neither view can conceal/rescue a failure in the other. There is no new
threshold or missing-frame cutoff. Secondary results cannot replace primary.
Undefined required values fail. Synthetic tests do not open participant captures.
