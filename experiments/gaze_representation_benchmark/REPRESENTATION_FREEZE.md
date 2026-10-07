# Stage B1 — immutable gaze representation freeze

These definitions were frozen before geometry-2 outcome evaluation.

Exactly **R0, R1, R2** exist. This document and their implementation must be
identified by the full immutable Git commit SHA in the PR and task report.
Never amend/rewrite that commit after outcome evaluation begins. This is a
formulation freeze, not a result, success claim or production decision. The
[original preregistration](../raw_geometry_gaze_diagnostic/PREREGISTRATION.md)
remains authoritative; its windows, metrics and five-part gate are unchanged.

## Data and coordinate boundary

- geometry-1 is development. Stage B1 consumes only its identity fields and
  `calibration_presentations`; its validation labels, summaries, residuals and
  outcomes do not select, tune or check these formulas.
- geometry-2 is the untouched final holdout. Stage B1 does not open it, including
  for schema checks. Stage B2 may evaluate the frozen definitions once, only
  after this commit exists. No subsequent formula replacement or retuning.
- At later evaluation each session derives its own references and screen maps
  from its own nine ordinary calibrations; geometry-1 references/maps are never
  transported into geometry-2.
- Formula APIs receive numerical geometry and fixed calibration references only;
  no target label, block, time, eye-opening condition, future frame or prediction.
  Known **calibration** targets are used only for the independent screen maps.
- Normalized image x increases right, y down. Screen targets use normalized
  coordinates in [0,1]; predictions remain unclipped. Names left/right follow
  the detector topology, not mirrored display placement. Original point order
  and iris-ring averaging remain unchanged.
- R0/R2 pixel XY = (x W, y H). R1 pseudo-pixel XYZ = **(x W, y H, z W)**,
  using each frame's recorded positive integer width W and height H. No alternate
  z scaling is permitted. Float64 arithmetic is used for numerical transforms.

**This is not metric 3D.** MediaPipe z is relative estimated depth; camera
intrinsics are unavailable. R1 tests geometric normalization, not physical
head-pose truth. It uses no optional native pose matrix, model, camera intrinsics
estimate or alternate depth/pose fallback.

## Shared production equations and topology

Production `extract_eye_features` and `extract_binocular_features` implement
all feature equations and aggregation. Production files remain unchanged.
For an eye's contour P, four-point iris ring with mean I, corners A/B,
upper lid U and lower lid L:

1. C = (A+B)/2; s = ||B-A||; a = (B-A)/s.
2. n = (-a_y, a_x), reversing its sign if (L-U) dot n < 0.
3. h = (I_x - min(P_x)) / (max(P_x) - min(P_x)).
4. v = ((I-C) dot n) / s.
5. Both valid eyes are required for binocular features:
   h_bin = (h_left+h_right)/2; v_bin = (v_left+v_right)/2.
   Monocular outputs are retained when possible; one eye never substitutes for two.

The production degeneracy guard is 1e-6 in the coordinate units passed to the
formula: corner span, contour x/y spans and oriented lid gap must exceed it;
||I-U||+||I-L|| must exceed it. R0 uses pixels, R1 aligned pseudo-pixels, R2
fixed dimensionless local-reference units. No clipping, blink gate or temporal
filter is added. Missing required points and arithmetic nonfinite results are
unavailable. R0's ordinary valid input behavior is exactly production.

| Geometry | Left | Right |
| --- | --- | --- |
| Contour (correspondence order) | 249,263,362,373,374,380,381,382,384,385,386,387,388,390,398,466 | 7,33,133,144,145,153,154,155,157,158,159,160,161,163,173,246 |
| Iris ring | 474,475,476,477 | 469,470,471,472 |
| A / B | 263 / 362 | 33 / 133 |
| U / L | 386 / 374 | 159 / 145 |

Detector iris centers 473/468 never replace ring means. Corners and lid points
already belong to the contours. No landmark subset search is permitted.

## R0 — unchanged production baseline

Apply the shared equations to original pixel-scaled XY. Neither face geometry
nor z is required. Reconstruct every usable calibration observation from saved
raw XY and compare to its logged production h/v with absolute and relative
1e-10 tolerance (the existing raw-capture reconstruction convention). This
checks capture integrity; it does not alter the formula. Missing z does not
change R0 availability. No alternative representation may alter R0.

## R1 — 3D face-canonicalized eye representation

The only face-anchor indices, in correspondence order, are:
**6,197,195,5,4,1,127,234,454,356,10,152**. No eye, brow or lip points enter
alignment. Every anchor and all 40 production eye contour/ring points require
finite XYZ; optional detector centers are ignored.

### Calibration reference

Take calibration samples whose recorded production feature status is usable,
whose reconstructed R0 is usable, and whose required R1 XYZ is complete/finite.
Convert each sample's points to pseudo-pixels. For each of the 12 anchors j
independently form Q_j = (median X_j, median Y_j, median Z_j) across those frames.
This is a frame-weighted component median, not a target-weighted pose fit.
No validation sample participates. An empty eligible set gives no R1 reference.

### One proper similarity transform per frame

Let P be the 12 current points and Q the reference, stored as N-by-3 row arrays,
N=12. Let pbar/qbar be arithmetic means and Pc/Qc their centered arrays.
Minimize sum_j ||c R P_j + t - Q_j||^2 with uniform c>0, R orthogonal,
det(R)=+1, and translation t. Use this deterministic Umeyama-style SVD:

```text
H = Qc.T @ Pc / N
U, sigma, Vt = svd(H, full_matrices=False)
d = (1, 1, -1 if det(U @ Vt) < 0 else 1)
D = diag(d)
R = U @ D @ Vt
variance_P = sum(Pc * Pc) / N
c = dot(sigma, d) / variance_P
t = qbar - c * (R @ pbar)
aligned_rows = c * (point_rows @ R.T) + t
```

This forbids reflection even for reflected input; it does not select the
unconstrained reflected fit. Require numerical rank 3 for Pc, Qc and H. Numerical
rank uses singular values greater than sigma_max * max(matrix.shape) * eps64,
where eps64 = 2.220446049250313e-16. This is a numerical degeneracy criterion,
not a tuned signal threshold. No weights or regularization exist.

Apply this same transform to both full contours, both iris rings, corners and
lids (52 required face/eye points overall). Retain aligned XY, discard aligned z
only at projection, and apply the shared R0 equations in those aligned units.
R1 changes representation; it retains the independent-linear mapping family.

### Availability

Missing/nonfinite required XYZ, absent reference, non-full-rank centered anchor
sets/covariance, SVD failure, nonpositive scale, nonfinite coefficients/transformed
coordinates, or production feature degeneracy makes R1 unavailable. There is
**no R0 or 2D fallback**. A failure of the shared face transform invalidates both
eyes; projected eye degeneracy follows the shared binocular rule. No physical
pose quality or post-hoc target-error threshold is used.

## R2 — periocular affine canonicalization

### Current local coordinates and calibration contour

For each eye independently convert its 16 contour and four iris-ring points to
pixel XY, form current C=(A+B)/2 and s=||B-A||, and use
**p_local=(p-C)/s**. Require finite XY and s>1e-6 pixels. No rotation is added
to this normalization. Use the same C/s for contour and iris ring.

Using ordinary calibration frames with usable recorded/reconstructed R0, take
for each corresponding contour landmark j the component-wise median of local
XY. This gives one fixed 16-by-2 reference Q per eye, with equal frame weight.
Iris positions are not part of the affine fitting reference. Reference corners,
U/L, midpoint, span and oriented n are derived from Q's named contour points
using the shared definitions; they are never replaced by current-frame values
when computing candidate h/v. An empty eligible contour set gives no reference.

### One ordinary affine transform per eye/frame

Let P be the current 16 local contour points. Construct B=[P_x,P_y,1], shape
16-by-3. Solve **M = argmin_M ||B M - Q||_F^2** by
`numpy.linalg.lstsq(B, Q, rcond=None)`; M has shape 3-by-2. All landmarks carry
weight one. The numerical singular cutoff is eps64 * max(16,3) * sigma_max.
Require design rank 3, finite M, and rank 2 of its 2-by-2 linear part using
the same float64 rank convention. No subset, weights, ridge term, search,
polynomial or alternate transform exists. Affine reflection is neither forced
nor separately optimized; ordinary full-rank OLS is the sole fit.

Apply **[iris_local_x,iris_local_y,1] @ M** to each current iris-ring point,
then average the four transformed points. Use that iris with **fixed Q**,
including Q's contour extrema/corners/lids, in the shared R0 definitions.
Contour shape has been canonicalized before measuring the iris. This is neither
`lid_fraction` nor `lid_midpoint_fixed_scale`: both iris coordinates undergo the
same two-dimensional affine fitted to all 16 corresponding contour points.

### Availability

Missing/nonfinite required per-eye XY, degenerate current span, absent reference,
rank-deficient affine design/linear part, least-squares failure, nonfinite
coefficients/transformed iris or degenerate fixed-reference feature geometry
makes that eye unavailable. Z and face anchors are not required. Both valid eyes
are required for the production arithmetic binocular mean; retain surviving
monocular output, without substituting it for binocular output. No R0 fallback.

## Calibration-only screen mapping

For each candidate and session, first build references from that session's
ordinary calibration only; recompute that candidate's calibration features with
those fixed references. Never fit references jointly across sessions. Only
recorded R0-usable calibration observations are eligible; candidate failures
remain unavailable, without imputation. There are no validation inputs to this API.

For every one of the nine calibration presentations compute separate medians
of candidate h and v across its usable frames using production
`aggregate_calibration_observations`. The existing acquisition minimum is five
usable observations per presentation. If any of the nine lacks five candidate
observations, do not fit a subset map: report candidate not evaluable.

Fit production `fit_independent_linear` with the nine equally weighted medians:

```text
x = x_slope * h + x_intercept
y = y_slope * v + y_intercept
slope = sum((f-fbar)*(target-targetbar)) / sum((f-fbar)^2)
intercept = targetbar - slope*fbar
```

Each axis uses only its own feature; coefficients are candidate- and
session-specific. Nonvarying features/targets or nonfinite coefficients make
mapping unavailable. Never reuse R0 coefficients for R1/R2. Monocular features
remain exposed for the preregistered later eye diagnostics; any later monocular
screen diagnostic uses the identical calibration-only procedure for that eye.
No validation fitting, target-specific offset, blending or temporal dependence.

## Frozen future analysis windows and all preregistered metrics

Stage B1 implements no outcome evaluator. The following are fixed requirements
for Stage B2, not measured outcomes. Use every usable observation in primary
**[0,3) seconds**. Label secondary **[0.8,3)** explicitly; it cannot replace
primary. Features/predictions are never clipped. First/second primary halves are
[0,1.5) and [1.5,3). Secondary halves retain this fixed 1.5 s boundary.

For each R0/R1/R2 and session report left and right before binocular aggregation,
plus binocular statistics. For either feature axis:

- Per-presentation feature medians; exact target, row and column feature medians.
  Each presentation contributes equally: level medians are medians of the
  applicable presentation medians. The same-target validation reference is the
  median of its three block medians. Never silently drop a missing target/block.
- Infer direction only from the three calibration level medians: +1 for strictly
  increasing, -1 for strictly decreasing; otherwise undefined. Report both signed
  adjacent-level separations and their minimum absolute magnitude. A strict
  ordering check requires both adjacent differences times that direction >0.
- Report level ordering in each of three validation blocks and the pooled
  session; vertical ordering in each screen column and horizontal ordering in
  each screen row, for every block and pooled. Report each named check, not just
  an aggregate count. An undefined candidate check cannot preserve a correct R0
  check. No cross-session raw-feature pooling creates a new calibration direction.
- Within-target unscaled MAD = median(|f-median(f)|), IQR = p75-p25, and their
  ratios to minimum adjacent validation level separation. Percentiles use the
  existing linear interpolation: position (n-1)*p/100 between sorted values.
  Report target-level and distribution summaries, without selection/tuning.
- Exact-coordinate calibration-to-validation signed shift = validation target
  reference minus calibration target median; absolute shift = |signed shift|.
  Report each target, row/column summaries and session median absolute shift.
  **Primary vertical transfer ratio** = median of nine absolute vertical target
  shifts / min(|middle-upper|, |lower-middle|), where levels are session-pooled
  validation presentation medians for that representation. Report analogous
  calibration-separation ratios as secondary context. Zero/undefined separation
  means undefined ratio, never a passing transfer result.
- Repeated-target block range = max(block medians)-min(block medians), with
  signed pairwise block changes and median/maximum nine-target ranges. Report
  first/second-half medians, signed second-minus-first changes, absolute changes,
  and half-specific exact-target transfer. This exposes block drift and within
  presentation transition behavior without filtering or formula selection.
- Calibration-only mapped sample errors dx=x_pred-target_x, dy=y_pred-target_y:
  sample-weighted (x MAE,y MAE) = (mean(|dx|),mean(|dy|)); signed biases =
  (mean(dx),mean(dy));
  mean, median and interpolated p95 of sqrt(dx^2+dy^2). Report signed residuals,
  absolute errors and sample-weighted summaries by target, row, column, block,
  and session, with observation counts. Sample weights are distinct from the
  equal-presentation feature summaries above.
- Calibration presentation predictions/residuals, x/y calibration-median MAE,
  fitted slopes/intercepts (gain), and mapping amplification of feature shifts
  (x_slope*delta_h, y_slope*delta_v). Report availability at calibration/validation,
  per eye/target/block, numerical failure reasons and usable fractions. A stable
  gaze-blind candidate is not useful; transfer takes priority over in-sample fit.
- Show both native candidate coverage and R0/candidate **common-frame** statistics
  separately, with R0 on all its frames and on that pair's shared frames. On
  shared frames recompute both representations' feature/transfer/ordering/error
  summaries with their original fixed calibration maps; never refit on shared
  validation data. Missing alternative observations cannot remove difficult R0
  frames silently. Unsupported required metrics cannot pass. Do not invent a
  post-hoc missing-frame threshold or selectively use the favorable coverage view.

## Unchanged untouched-holdout PROMISING gate

All five criteria from the original preregistration remain required on geometry-2:

1. Primary validation y MAE improves by at least **20%** versus R0:
   candidate/R0 <= **0.80**.
2. Median absolute calibration-to-validation vertical transfer relative to
   adjacent-row separation improves by at least **25%**:
   candidate transfer ratio / R0 transfer ratio <= **0.75**.
3. Vertical ordering is not worse than R0: do not lose any R0-correct pooled,
   per-block or per-column ordering check. Direction comes from each candidate's
   calibration, never validation.
4. Primary x MAE does not worsen by more than **15%**: candidate/R0 <= **1.15**.
5. No target-label leakage, validation-fitted correction, future-frame dependence
   or post-holdout tuning explains the improvement.

Report block drift, within-target variability, availability changes, amplification
and both eyes as well. A required metric unavailable/unsupported by adequate
signal cannot pass. No post-hoc missing-frame threshold. Zero R0 comparison
denominators give undefined ratios, not claimed improvements. The common-frame
and native-coverage views must be explicit; coverage cannot disguise a gate
failure. A gate pass permits considering later live interaction validation,
not choosing a production replacement. A failure remains a failure: no R3,
formula replacement, lowered gate or repeated holdout ranking follows it.

## Implementation and execution boundary

`representations.py` contains exactly the fixed algorithms; `calibration.py`
accepts typed ordinary calibration presentations only; `analysis.py` permits
only the fixed geometry-1 local path (rejecting symlinks/other paths before open),
opens the allowlisted ASCII-escaped capture in unbuffered binary mode, lexically
skips noncalibration metadata and stops immediately after decoding
`calibration_presentations`. It never reads the subsequent validation bytes.
No B1 holdout switch, validation-fitting API, candidate ranking, gate evaluator
or RESULTS.md exists. Freeze tests use synthetic geometry only.

NumPy is already an Experiment 006 dependency and locally installed through the
vision stack. It is now explicitly a development/experiment dependency so CI
can exercise SVD/least squares without installing camera libraries. The standard
library has no suitable SVD solver; production dependencies remain unchanged.
The rank/cutoff conventions follow the official [SVD](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html),
[least-squares](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)
and [rank](https://numpy.org/doc/stable/reference/generated/numpy.linalg.matrix_rank.html)
documentation. No additional numerical library is needed.
