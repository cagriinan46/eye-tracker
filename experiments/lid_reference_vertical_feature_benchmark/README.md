# Final bounded offline lid-reference feature round

## Question and fixed data split

Can either of **exactly two** lid-referenced vertical features preserve natural upper/center/lower gaze discrimination while reducing opening-state and repeated-target mapped changes relative to production? This is offline engineering evaluation, not physical-cause inference or a production change. No new camera samples are collected.

Primary `face_reference_corner_stability` protocol-v1 captures for `cagri`: **development live-1 and live-2; held-out decision live-3**. Evaluate the development sessions first. The formulas and six-part rule below are fixed before live-3 is inspected. After that decision, use the three compatible `eye_geometry_decomposition` protocol-v1 captures only as a secondary historical check; they cannot overturn a failed primary rule. The analyzers reject incompatible protocol versions and pilot data. The numerical input files remain Git-ignored.

## Production baseline and predeclared formulas

All geometry is in pixels. Production computes each eye's iris center `I` from its four iris-ring landmarks; corners `A,B` give midpoint `M=(A+B)/2`, span `s=||B-A||`, and unit normal `n=(-(B_y-A_y), B_x-A_x)/s`, flipped if necessary so the projected upper-to-lower lid gap is positive. Production monocular vertical is `(I-M)·n/s`. Binocular vertical is the mean of simultaneous left/right values. Existing strict capture validators verify the saved production values. Production code is unchanged.

From **usable natural ordinary calibration frames only**, separately for each eye, compute `s_cal` as median corner span and `n_cal` as the normalized component-wise medians of the lid-oriented corner normals. No target-specific or diagnostic reference is used. This is the prior benchmark's calibration reference rule.

1. `lid_midpoint_fixed_scale`: current lid midpoint `L=(upper+lower)/2`; feature `(I-L)·n_cal/s_cal`.
2. `lid_fraction`: project upper `u`, lower `l`, and iris `i` onto `n_cal`; feature `(i-u)/(l-u)-0.5`, algebraically `(I-L)·n_cal/((lower-upper)·n_cal)`. Reject a sample if the **signed projected aperture is ≤ 1e-6 pixel**; never flip the axis per diagnostic frame. Any such rejection is counted and reported. The fixed axis is oriented from calibration upper to lower, so a nonpositive later aperture is unavailable geometry.

No blends, correction coefficients, condition inputs, polynomial, target-row formula, ML, clipping, or post-hoc candidate will be added. Both formulas use only current landmarks and a standard session calibration reference. Binocular values average the two simultaneously valid monocular values.

## Mapping and evaluation

For production and each candidate separately, per eye and binocular, aggregate a presentation by the median of its usable sample feature values, then fit ordinary least-squares `y = slope × feature + intercept` on **nine ordinary calibration presentation medians only**. No diagnostic sample changes a feature reference or mapping. Report calibration span, slope, MAE, and residuals. On natural diagnostic presentations report y MAE, median and p95 absolute error, bias, predicted row medians, ordering, and adjacent margins. For each target × block, report narrow and wide minus natural feature and mapped-y shifts (median and p95 absolute, with signed counts). For each target × condition, compare all three block pairs (feature and mapped-y median, p95, maximum). Keep left/right separate before binocular interpretation. All predictions remain unclipped.

**Amplification metric:** because the three features have different units, raw slope magnitudes are not directly comparable. Use only calibration samples: within each calibration presentation compute median absolute sample deviation from that presentation's feature median; take the median of the nine deviations, then multiply by `abs(fitted_slope)`. This is the mapped-y equivalent of observed calibration sample-scale feature variation. It is a diagnostic of mapping amplification, not a new quality threshold.

## Predeclared live-3 eligibility rule

A candidate is eligible only if its **held-out live-3 binocular** results satisfy all six checks against the live-3 production baseline:

1. Natural row medians have strict upper < center < lower order.
2. Natural diagnostic y MAE ratio ≤ **1.15**.
3. At least one of narrow/wide median absolute mapped-y shift ratios ≤ **0.85**.
4. The other shift ratio ≤ **1.15**.
5. Median absolute repeated-target mapped-y variation ratio ≤ **1.15**.
6. Calibration amplification metric ratio ≤ **1.15**.

Ratios use candidate/baseline, with a zero baseline handled as ineligible if the candidate is nonzero; if both are zero, ratio is 1. No threshold will be adjusted after observing live-3. If both pass, prefer the simpler and more cross-session-consistent candidate. If neither passes, declare **NO WINNER**, stop hand-crafted feature search, retain production for now, and return to Phase 1 interaction/cursor-targeting validation with coarse targets and documented vertical limitations. Do not request another feature experiment or live candidate comparison on a failed rule.

The analysis module prints structured per-session metrics and a separate holdout eligibility record. It does not collect data or modify production. Run locally with `PYTHONPATH=src:. .venv/bin/python -m experiments.lid_reference_vertical_feature_benchmark.analysis <development-live-1> <development-live-2> <holdout-live-3>`. Historical captures may be passed only after this decision.
