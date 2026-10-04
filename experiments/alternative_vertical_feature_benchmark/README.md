# Offline benchmark of vertical geometry features

## Question and data boundary

Can a simple feature computed from current landmarks and **ordinary calibration only** preserve upper/center/lower gaze separation while reducing eye-opening and block variation compared with `binocular_vertical_local_axis`? This is an offline diagnostic, not a production change. No frames, video, new live sessions, condition labels, target identity, future samples, or diagnostic values are used to define a candidate or fit its mapping.

The **primary** dataset is the three protocol-v1 `face_reference_corner_stability` captures for `cagri` (`live-1/2/3`). The **secondary** dataset is the three protocol-v1 `eye_geometry_decomposition` captures. Existing strict analyzers verify protocol identity, expected schedule, saved geometry, counts, and sample reconstruction. The older dataset lacks broader-face anchors, so `face_iris_y` is unsupported there. These datasets are analyzed separately, never pooled as if they were one protocol. Protocol-invalid pilots and earlier eye-opening reports are excluded.

## Production geometry and bounded candidates

Production computes each eye's iris center as the mean of its four iris-ring points, in pixel coordinates. Let `a,b` be production eye corners, `m=(a+b)/2`, `s=||b-a||`, and `n=(-(b_y-a_y),b_x-a_x)/s`. Flip `n` if the projected upper-to-lower lid gap is negative. The monocular vertical feature is `((iris-m)·n)/s`; binocular vertical is the arithmetic mean of both monocular values. Degenerate geometry is unavailable in production. The saved samples' reconstructed production vertical values are verified by the upstream protocol analyzers.

Candidate set is fixed before evaluating outcomes:

1. **`production`**: saved exact current production monocular feature and its per-frame binocular mean.
2. **`face_iris_y`**: each iris center's pixel y after the existing calibration-template non-eye face similarity alignment; binocular mean. It does not depend on dynamic eye-corner span. The template is formed from ordinary calibration anchors only. Primary dataset only.
3. **`stable_span`**: `((iris-m)·n)/s_cal`, keeping current midpoint and oriented normal but replacing per-frame span by that eye's median span among all usable **ordinary calibration** samples.
4. **`stable_frame`**: `((iris-m)·n_cal)/s_cal`, keeping current midpoint but replacing normal and span with the per-eye calibration reference. `n_cal` is the normalized vector of component-wise medians of calibration-frame lid-oriented normals. This tests stronger stabilization without freezing frame translation.

All four are deployable in principle from current geometry and post-calibration state; this experiment does not establish their practical production quality. No label-dependent, diagnostic-target-specific, polynomial, or eye-opening correction is fitted. There is no optional hybrid.

## Calibration and evaluation

For each candidate and each eye/binocular output independently, compute the median feature over usable samples in each presentation. Fit `y = slope × feature + intercept` by ordinary least squares on the **nine natural calibration presentation medians only**. This matches the project's simple vertical mapping concept. Calibration feature span, slope, and calibration MAE are retained. Predictions are never clipped.

Evaluate each session separately on natural diagnostic presentations: y MAE, median/p95 absolute error, bias, upper/center/lower predicted medians, ordering, and adjacent row margins. For each target and block, compare `comfortably_narrow` and `comfortably_wide` to `natural` in feature and mapped-y space, including signed direction and row-specific absolute changes. For each target × condition, use all three unordered block pairs to summarize repeated-target feature and mapped-y differences; natural-only repeats are reported separately. Use linear-interpolated p95 on the sorted values. Left and right receive their own calibration fits and evaluations before binocular aggregation.

Selection is a multi-axis comparison: natural row discrimination and accuracy, eye-opening sensitivity, repeated-target stability, mapping slope/amplification, consistency across rows/sessions, and compatibility with secondary captures. A constant or compressed feature is not useful merely because it is stable. The benchmark does not tune formulas on diagnostic labels or choose a winner from one scalar score.

Run the analysis locally with `PYTHONPATH=src:. .venv/bin/python -m experiments.alternative_vertical_feature_benchmark.analysis <capture.json> ...`. It prints structured numerical output, including every matched pair. `RESULTS.md` records the measured comparison and bounded recommendation.
