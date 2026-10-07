# Raw-geometry representation preregistration

Frozen before geometry-session collection. This is an engineering protocol for
Çağrı, not a physical-cause study. No geometry session or candidate outcome exists
at registration. Exactly **R0 + R1 + R2** are permitted. No further family,
landmark-ratio enumeration, ML, temporal filter, validation-fitted mapping,
target-specific correction, or production replacement belongs to this task.

## Question and collection

Can richer eye/face geometry support a representation that preserves real gaze
separation and transfers better from calibration to validation? The prior
[fixed-window result](../fixed_window_gaze_diagnostic/RESULTS.md) implicated both
representation transfer and mapping fit. Ordered medians alone were insufficient.
The earlier captures saved only h/v and mapped coordinates, so their missing raw
geometry cannot be reconstructed.

The physical protocol is unchanged: READY, fresh nine-point calibration
(0.8 s settle + 1.2 s sample), three blocks of nine validation targets, seed
20261006, opposite-point non-gated cue 0.75 s, complete target window 3.0 s,
blank transition 0.5 s. No gaze cursor, success/failure, dwell, or early stopping.
Targets are the 3×3 grid at x/y = 0.2, 0.5, 0.8. Natural relaxed eyes and ordinary
comfortable posture are required; perfect head immobility is not requested.

New capture identity: `raw_geometry_gaze_diagnostic`, version 1, geometry schema 1.
Detector/model provenance and selected numerical coordinates are retained from
the same production detector result. Production options are unchanged. Normalized
z and face landmarks are estimates, not anatomical or metric pose ground truth.
An optional native face transform is copied only if already returned; this
protocol does not enable that output. Selected face XYZ supports later approximate
offline orientation/pose investigation, with assumptions recorded explicitly.

## R0 — PRODUCTION BASELINE

Use the unchanged production eye topology and feature functions. For each eye,
convert normalized XY to pixels using the recorded frame width/height:

- Iris center I is the arithmetic mean of the four iris-ring XY coordinates.
- Horizontal h = (I.x − minimum contour x) / (maximum contour x − minimum contour x).
- Let corners A/B define span s = ||B−A|| and midpoint C = (A+B)/2.
  The local vertical unit vector n is perpendicular to (B−A), with its sign
  oriented so (lower lid − upper lid)·n is positive.
- Vertical v = (I−C)·n / s.
- Binocular h/v are the arithmetic average of the two valid eyes. If either eye
  fails the production degeneracy guards, R0 is unavailable. No clipping or new
  blink gate is introduced.

The MediaPipe center points 473/468 are separately logged but do not replace the
production ring means. R0 must reconstruct the logged values numerically before
any alternative is benchmarked. Preserve unavailable-frame semantics.

## R1 — HEAD-CENTRIC EYE REPRESENTATION

Test whether face/head orientation normalization improves transfer. Allowed
ingredients: per-frame iris and corner geometry, the documented independent
non-eye facial anchors, available normalized XYZ, frame size, and approximate
orientation derived offline from those same-frame landmarks. A native face
transform may be used only if present in the captured output.

Express iris displacement relative to eye geometry in a face/head-centric frame,
normalizing scale using documented current-frame facial/ocular geometry. No
known current target, screen row/column, block, eye-opening label, future frame,
or validation-fitted correction is permitted. References needed after calibration
must be constructed from ordinary calibration alone.

Concrete coordinate construction, pose assumptions, depth handling, and scale
choice are intentionally not chosen here: their feasibility needs geometry-1's
recorded fields. Choose **one** formulation from these ingredients using geometry-1
geometry consistency/availability and calibration only. Missing depth/pose must
be explicitly documented; any fallback must be frozen before opening holdout
outcomes. If required geometry is unavailable, report R1 not evaluable rather
than inventing a new family after seeing holdout results.

## R2 — PERIOCULAR GEOMETRY-NORMALIZED REPRESENTATION

Test whether richer local geometry reduces drift relative to the corner-defined
production reference. Allowed ingredients: iris rings/centers, inner/outer
corners, the complete production upper/lower eye-contour arcs, lid references,
and current eye/face scale. Bilateral geometry is permitted, with monocular
results retained before aggregation. Use only the current frame and legitimate
calibration state.

Choose **one** local geometric normalization from these ingredients using
geometry-1 geometry consistency/availability and calibration only. Do not use
validation-target accuracy to search landmark subsets or tune formulas. No
screen-position-specific or target-specific term, condition-specific formula,
weighted blend search, fitted eye-opening regression, or ML is permitted.

R2 must not reproduce the historical `lid_fraction` or
`lid_midpoint_fixed_scale` formulas; neither passed the prior held-out gate.
Merely renaming a failed scalar formula is not a new representation family.
The concrete geometric definition and its rationale must be recorded before
holdout evaluation. Do not enumerate multiple variants under the R2 name.

## Session split and freeze procedure

| Session | Role | Permitted use |
| --- | --- | --- |
| geometry-1 | Development / diagnostic | Schema/geometry inspection, implementation sanity, ordinary calibration; descriptive evaluation after a formulation is fixed |
| geometry-2 | Untouched final holdout | One final benchmark after R1/R2 mathematical definitions and code are frozen |

Both sessions receive independent fresh calibration. Calibration references,
scales, and screen mapping parameters use **only that session's ordinary nine
calibration presentations**. Future candidate screen maps use the same robust
per-presentation aggregation and production IndependentLinearMapping concept,
fitted separately for each candidate; no baseline-coefficient reuse across
incompatible feature scales.

Before inspecting geometry-2 outcomes, record an immutable commit/hash containing
R1/R2 formulas, coordinate/depth conventions, availability rules, parameters,
metrics, and gates. Geometry-2 target labels, residuals, ordering, transfer, and
block drift must not select formulas, thresholds, coefficients, landmark
combinations, or variants. Automated collection/schema inspection can verify
schedule/completeness and R0 reconstruction without reporting holdout accuracy.
Stored holdout samples/summaries must remain unopened for outcome analysis until
this freeze. Evaluate the frozen definitions once; do not retune and re-rank on
geometry-2. Development validation labels are evaluation-only, not optimizer
inputs. Historical captures do not substitute for this holdout.

## Future metrics and aggregation

Primary evaluation retains every usable observation in the full [0,3) s target
window, without clipping. An explicitly labeled secondary [0.8,3) s analysis may
inspect gaze-transition sensitivity but must not replace primary outcomes.

For each representation and each session, retain left/right metrics before
binocular aggregation and report:

- Target/row/column feature medians, calibration-inferred ordering, adjacent-level
  separations, within-target MAD/IQR, and spread/separation ratios.
- Ordering in every validation block, vertical ordering in every screen column,
  horizontal ordering in every screen row, and pooled-session ordering.
- Exact-coordinate calibration-to-validation signed/absolute shifts and
  normalized shift; repeated-target block ranges and first/second-half changes.
- Sample-weighted x/y MAE, signed bias, mean/median/p95 Euclidean error, and
  target/row/column/block residuals after calibration-only fitting.
- Calibration fit/gain and availability; a numerically stable but gaze-blind
  representation is not useful. Transfer takes priority over in-sample fit.

Presentation feature median gives each presentation equal weight. Same-target
validation reference is the median of its three block medians. The vertical
transfer ratio is median absolute nine-target transfer divided by the smaller
absolute adjacent separation of the session-pooled upper/center/lower validation
presentation medians, calculated separately for each representation. Report
calibration-separation ratios as secondary context. Zero/undefined separation
cannot produce a passing transfer result. MAD is unscaled median absolute
deviation; IQR uses the existing interpolated p75−p25 convention.

## Untouched holdout promising gate — all five criteria required

An alternative may be called **PROMISING** only if geometry-2 satisfies:

1. Primary validation **y MAE improves by at least 20%** versus R0
   (candidate/R0 ≤ 0.80).
2. Median absolute calibration-to-validation vertical transfer relative to
   adjacent-row separation **improves by at least 25%** (ratio ≤ 0.75 of R0).
3. Vertical ordering is **not worse than R0**: do not lose any R0-correct pooled,
   per-block, or per-column ordering check. Direction is inferred from each
   representation's calibration, not chosen from validation.
4. Primary **x MAE does not worsen by more than 15%** (candidate/R0 ≤ 1.15).
5. No target-label leakage, validation-fitted correction, future-frame dependence,
   or post-holdout tuning explains the improvement.

Also report block drift, within-target variability, availability changes, mapping
amplification, and both eyes. Unavailable alternative predictions cannot silently
remove difficult R0 frames: show common-frame and coverage statistics; a required
metric unavailable or unsupported by adequate signal cannot pass. Do not invent a
post-hoc missing-frame threshold. If R0 comparison denominators are zero, report
the ratio undefined and do not declare an improvement from it.

Do not change these gates after outcomes are visible. A pass justifies considering
later live interaction validation; it does **not** select a production replacement.
A failure must remain a failure; no R3 or softened gate follows in this task.
