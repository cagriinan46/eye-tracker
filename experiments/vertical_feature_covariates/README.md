# Offline vertical-feature covariate diagnostic

## Question and scope

When the recorded binocular vertical feature changes between visits to the **same target**, do its two monocular components move together, and do the changes co-vary with the recorded face-center-y or eye-opening measures? This analysis uses only the three completed Çağrı live-sensitivity sessions. It collects no new camera data and changes no production behavior.

## Inputs and reproduction

The inputs are the local, Git-ignored derived-numerical reports `.venv/vertical-sensitivity-cagri-live-{1,2,3}.json`. Keep them local; do not commit them or the full analyzer output. From the repository root:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_feature_covariates.analysis \
  .venv/vertical-sensitivity-cagri-live-1.json \
  .venv/vertical-sensitivity-cagri-live-2.json \
  .venv/vertical-sensitivity-cagri-live-3.json
```

The command writes one JSON array to standard output. Each session record includes all 27 presentation summaries, all 27 exact-coordinate pair records, session summaries, descriptive associations, and its five largest absolute binocular differences. The pair records are scatter-friendly numerical data. No prediction is inverted to create a feature; the analyzer reads the original per-sampling-attempt numerical rows and checks each saved binocular presentation median against their recomputed median.

## Predeclared method

For each scheduled presentation, group its usable sampling rows by phase, trial, target ID, and exact coordinates. Take the **median separately for each recorded field**: binocular, left, and right vertical feature; left, right, and binocular eye opening; and head-center y. Also retain usable/unavailable counts. A missing optional monocular or covariate field remains `null`; pair deltas and associations that need it remain unavailable rather than being reconstructed. A usable row without the primary binocular vertical feature is invalid for this analysis. The 27 saved presentations, protocol order/coordinates, usable counts, and saved binocular medians are checked against the raw rows.

At each exact coordinate, calculate later minus earlier for calibration→A, calibration→B, and A→B. Report signed and absolute changes for all measured fields. Define `common_mode_vertical_delta = (delta_left_vertical + delta_right_vertical) / 2` and `differential_vertical_delta = delta_left_vertical - delta_right_vertical`. These use **differences of separate presentation medians**. The capture path forms each frame's binocular vertical feature as the arithmetic mean of left and right. The analyzer checks that frame identity numerically; `median((left + right)/2)` need not equal `(median(left) + median(right))/2`, so it also reports their presentation-level residual instead of assuming equality. `mapped_y_delta = saved_y_slope × delta_vertical` is an output difference, not an independent gaze-error observation.

The same-direction proportion counts pairs with nonzero left and right changes having the same sign. Opposite signs are counted separately; zero or missing changes are excluded from that proportion and reported separately. Per-session summaries use the median absolute change for the binocular, monocular, common-mode, differential, head-center, and binocular-opening measures. The differential tail uses a linearly interpolated p95 and maximum. The five largest pairs per session are sorted by absolute binocular change; no outlier is excluded.

The planned associations are signed and absolute binocular vertical change against head-center-y change, signed and absolute binocular vertical change against binocular eye-opening change, and signed left/right vertical change against the corresponding eye-opening change. Spearman correlation uses average ranks for ties and is `null` when fewer than two complete pairs or a constant rank series make it undefined. Each association reports its available pair count. Correlations are **descriptive per session**; the 27 pair records reuse presentations and are not independent trials. No p-values, significance claims, pooled population estimate, or search over additional variables is used.

As a secondary check, each presentation reports `p95 − p05` of its usable within-presentation binocular vertical, head-center-y, and binocular-opening samples. This spread can distinguish a visit-level median shift from a visit with substantial internal variability, but it is not a validated stability gate.

The face-center-y value is a coarse image-coordinate proxy and cannot distinguish translation from pitch. Eye-opening and vertical features are derived from related landmarks. Fixation, prior gaze targets, elapsed time, and eye/face geometry were not independently controlled. Associations cannot identify physical or software causes, and no correction, threshold, filtering, clipping, mapping change, or production policy follows from this diagnostic. See [RESULTS.md](RESULTS.md) for the measured observations and bounded interpretation.
