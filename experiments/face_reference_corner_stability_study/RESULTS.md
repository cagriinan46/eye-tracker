# Face-referenced eye-corner stability: three controlled sessions

## Purpose and valid captures

This diagnostic asks whether the **detected production eye corners** change relative to a broader set of non-eye MediaPipe face landmarks when comfortable eye-opening state changes at a fixed displayed target. It follows the [eye-geometry decomposition study](../eye_geometry_decomposition_study/RESULTS.md), whose corner-frame contribution was mathematical rather than anatomical attribution. Only these new files were analyzed: `.venv/face-reference-cagri-live-1.json`, `-2.json`, and `-3.json`. Earlier eye-opening and eye-geometry captures are excluded from the statistics below. The participant reported no protocol failure.

Each file was read and passed the [protocol-v1 analyzer](analysis.py): participant `cagri`, its expected `live-N` session, `face_reference_corner_stability`, seed `20261005`, **1.5 s** centered cue, READY before timing, camera index **1** at **1920×1080**, **0.8 s** settling and **1.2 s** sampling. All use face anchors `[6,197,195,5,4,1,127,234,454,356]` and `calibration_median_pixel_anchors_to_2d_similarity_v1`. Each has **9 calibration + 27 diagnostic = 36 presentations**, exactly one of every target × condition × block cell, without missing or duplicated cells. Every saved sampling row was usable and includes ten face anchors, an alignment transform and RMS residual, original eye primitives, and face-normalized eye geometry; every presentation exceeds the five-usable-row minimum. No data or outlier was removed.

| Session | Elapsed s | Usable rows | Usable per presentation | Failed camera reads / no-face | Calibration y slope |
| --- | ---: | ---: | ---: | ---: | ---: |
| live-1 | 113.641 | 1,218/1,218 | 33–34 | 0 / 0 | 29.142631 |
| live-2 | 113.634 | 1,217/1,217 | 33–34 | 0 / 0 | 31.999926 |
| live-3 | 113.591 | 1,216/1,216 | 33–34 | 0 / 0 | 37.392960 |

All summaries use **independent presentation-level medians** of the actual saved numerical samples. Comparisons subtract the natural presentation at the **same session, target, and block**. Positive/negative counts never exclude a technically valid observation. Counts from the two eyes or repeated matched contrasts are descriptive, correlated measurements—not independent people.

## Manipulation check first

Measured binocular opening followed **comfortably narrow < natural < comfortably wide** in **9/9** target/block sets in each session, **27/27** overall. The table gives the median of nine presentation-level opening medians for each condition, not a presumed numerical value for a prompt.

| Session | Comfortably narrow | Natural | Comfortably wide | Ordered sets |
| --- | ---: | ---: | ---: | ---: |
| live-1 | 0.102593 | 0.274354 | 0.339705 | 9/9 |
| live-2 | 0.096141 | 0.278743 | 0.371495 | 9/9 |
| live-3 | 0.101941 | 0.307315 | 0.380986 | 9/9 |

Across 27 matched sets, median measured opening changes were **−0.189561** for narrow − natural and **+0.075075** for wide − natural. This manipulation separated strongly, but its narrow and wide distances from natural were unequal. Condition labels must not be treated as equal-sized aperture changes.

## Fixed-target vertical-feature response

| Condition − natural | Median Δbinocular vertical | Mean Δbinocular vertical | Positive / negative | Median Δmeasured opening |
| --- | ---: | ---: | ---: | ---: |
| Comfortably narrow | +0.018016 | +0.016571 | 27 / 0 | −0.189561 |
| Comfortably wide | +0.007585 | +0.008859 | 25 / 2 | +0.075075 |

The narrower state had the larger feature change here, alongside its larger measured aperture change. Both states usually increased the feature relative to natural, consistent with a nonlinear/asymmetric response rather than a single opening-to-feature coefficient.

| Condition | Session | Median Δvertical | Mean Δvertical | Positive / negative |
| --- | --- | ---: | ---: | ---: |
| Narrow | live-1 | +0.016700 | +0.015718 | 9 / 0 |
| Narrow | live-2 | +0.016601 | +0.015513 | 9 / 0 |
| Narrow | live-3 | +0.018701 | +0.018481 | 9 / 0 |
| Wide | live-1 | +0.006478 | +0.007331 | 9 / 0 |
| Wide | live-2 | +0.011582 | +0.009875 | 8 / 1 |
| Wide | live-3 | +0.008267 | +0.009373 | 8 / 1 |

## Face-reference method and what it removes

As preregistered in the [README](README.md), the ten selected nose/face-oval anchors exclude the production eye frame, lids, iris, eyebrows, and lips. A **session-local calibration-only template** takes the coordinate-wise median of each anchor over usable natural-calibration frames. Every usable frame fits an orientation-preserving least-squares 2D similarity from its current **pixel** anchors to that template: `q̂ = sR(θ)p + t`. The same transform maps iris, corner, and lid points into template-aligned face coordinates. The saved `s`, `θ`, `t`, and anchor RMS residual are checked by recomputation. The resulting coordinates remove a best-fit *global 2D* translation, uniform scale, and in-plane rotation of these detected anchors. A condition-related residual eye-corner span change cannot be explained by **one such global transform alone**. This does not remove nonrigid face geometry, pose in depth, or detector coupling.

## Face-normalized corner movement: primary result

The most repeatable geometry result was **corner-span change relative to the selected broader face reference**. Each condition has 27 matched target/block cells × two eyes = **54 eye-level contrasts**:

| Condition − natural | Median signed Δspan, px | Mean Δspan, px | Increased / decreased | Median corner-midpoint displacement, px | Median abs Δangle, degrees |
| --- | ---: | ---: | ---: | ---: | ---: |
| Comfortably narrow | −1.623089 | −1.836159 | 6 / 48 | 1.429563 | 3.310409 |
| Comfortably wide | +2.973178 | +2.895462 | **54 / 0** | 0.809259 | 1.402473 |

`Δspan` is signed; midpoint displacement is the Euclidean length of the x/y change **after pixel scaling**; abs angle is the absolute shortest wrapped angle difference. These are different geometric quantities. The wide condition's span increase includes **every left and right eye** in all 27 matched cells. Narrowing decreased span in 48/54, with the six increases confined to the lower target row. Thus the detected production eye-corner geometry changes relative to the chosen non-eye facial reference under eye-opening manipulation. This is a **detected-landmark** result, not anatomical movement.

Both corner endpoints moved. Pooled face-normalized median absolute displacements were **2.122 / 1.491 px** for corner A/B under wide, and **2.478 / 2.744 px** under narrow. The midpoint displacement was smaller than the endpoint movements and wide span change, supporting **shape/span change plus some midpoint movement**, rather than a rigid translation of an unchanged pair. Narrowing also had a larger angular change. Opposite signed left/right angle changes reflect the two eyes' different corner-axis directions, so pooled signed angle alone is misleading.

| Condition | Eye | Median Δspan px | Span increase / decrease | Median signed Δangle ° | Median midpoint displacement px | Median Δmonocular vertical | Vertical positive / negative |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Narrow | Left | −1.280550 | 4 / 23 | +3.271825 | 1.740878 | +0.018603 | 27 / 0 |
| Narrow | Right | −1.893864 | 2 / 25 | −3.435158 | 1.214845 | +0.016617 | 27 / 0 |
| Wide | Left | +3.023304 | 27 / 0 | −1.665330 | 0.883195 | +0.007957 | 25 / 2 |
| Wide | Right | +2.875674 | 27 / 0 | +1.044501 | 0.682616 | +0.007788 | 26 / 1 |

Left and right span changes had the **same sign in 27/27 wide** and **25/27 narrow** matched cells. Their monocular vertical changes had the same sign in **26/27 wide** and **27/27 narrow** cells. Individual eye measurements are retained in the analyzer, rather than replaced by their binocular average.

## Iris, corners, lids, and descriptive associations

Face-normalized median absolute iris-center displacement was **1.288 px wide** versus **2.141 px narrow**; corresponding corner-midpoint displacements were **0.809** and **1.430 px**. The analyzer retains signed x/y changes for each corner, iris center, upper/lower lid, and lid midpoint, plus corner span/angle, eye opening, and the current monocular feature. In the wide condition, upper and lower lid landmarks moved by median absolute **4.333** and **2.045 px**; in narrow, **8.846** and **5.262 px**. The iris and corner geometry both changed; a small iris displacement magnitude does not imply an irrelevant iris contribution.

Across 54 eye-level matched contrasts per condition, descriptive Spearman correlations were:

| Condition | Signed Δface-normalized span vs Δmonocular vertical | Iris-center displacement magnitude vs Δmonocular vertical |
| --- | ---: | ---: |
| Comfortably narrow | +0.301 | +0.494 |
| Comfortably wide | +0.654 | +0.086 |

For wide, span/feature rank association was **+0.740 / +0.796 / +0.331** by live-1/2/3; iris-magnitude association was **+0.230 / −0.344 / +0.075**. For narrow, those respective session associations were **+0.164 / +0.659 / +0.472** and **+0.360 / +0.604 / +0.577**. The two conditions therefore show different *descriptive* geometry patterns, but the feature mathematically uses iris **relative to** the corner frame, the two eyes within a presentation are coupled, and repeated contrasts share targets/blocks. These correlations are neither independent-sample inference nor causal partitions.

## Broader-face alignment changes and remaining confounds

The face-anchor fit itself changed between conditions. These are medians of 27 matched presentation-median transform differences, condition minus natural:

| Condition | Δscale | Δrotation rad | Δtranslation x px | Δtranslation y px | Δanchor RMS px |
| --- | ---: | ---: | ---: | ---: | ---: |
| Comfortably narrow | −0.009892 | −0.014025 | −0.314042 | +20.571848 | +1.351067 |
| Comfortably wide | −0.006440 | +0.001904 | +8.217320 | +3.941217 | +0.392923 |

Narrowing had positive translation-y delta in **27/27** matched sets and increased residual in **25/27**; wide had positive translation-x/y in **23/27** each. The fit changes show that the broader **detected** face/camera/head configuration also differed by condition. Alignment removes its best-fit 2D similarity component; the remaining corner-span signal is not just one global 2D translation, scale, or roll. The anchors are themselves MediaPipe outputs, however, and their RMS/residual changes allow expression- or pose-related changes beyond a rigid 2D similarity. Do not attribute them uniquely to head movement.

## Target row, session, and block

| Condition | Target | Median Δbinocular vertical | Positive / negative | Median Δspan px | Span increase / decrease | Median midpoint displacement px | Median abs Δangle ° |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Narrow | Upper | +0.018134 | 9 / 0 | −3.093958 | 0 / 18 | 1.083283 | 3.009772 |
| Narrow | Center | +0.018016 | 9 / 0 | −1.400064 | 0 / 18 | 1.429563 | 3.206798 |
| Narrow | Lower | +0.016420 | 9 / 0 | −0.864876 | 6 / 12 | 1.755906 | 3.399967 |
| Wide | Upper | +0.011618 | 8 / 1 | +3.140565 | 18 / 0 | 0.630519 | 1.186228 |
| Wide | Center | +0.008267 | 8 / 1 | +3.085344 | 18 / 0 | 0.852019 | 1.456028 |
| Wide | Lower | +0.006245 | 9 / 0 | +2.318353 | 18 / 0 | 0.915762 | 1.578176 |

Wide span enlargement was present in **18/18 eye-level contrasts at each row**. Its binocular feature median declined from upper to lower, as in earlier controlled studies. Narrow span shrinkage was strongest at upper gaze, whereas midpoint displacement and angle magnitude rose toward lower gaze. These row patterns make one global feature coefficient inappropriate.

| Condition | Session | Median Δspan px | Span increase / decrease | Median midpoint displacement px | Median abs Δangle ° |
| --- | --- | ---: | ---: | ---: | ---: |
| Narrow | live-1 | −1.236834 | 4 / 14 | 1.255871 | 2.824019 |
| Narrow | live-2 | −1.536328 | 2 / 16 | 1.342541 | 3.303068 |
| Narrow | live-3 | −2.735931 | 0 / 18 | 1.798318 | 3.501814 |
| Wide | live-1 | +2.789492 | 18 / 0 | 0.951028 | 1.326506 |
| Wide | live-2 | +3.318539 | 18 / 0 | 0.651581 | 1.569714 |
| Wide | live-3 | +2.871496 | 18 / 0 | 0.755342 | 1.356874 |

| Condition | Block | Median Δbinocular vertical | Positive / negative | Median Δspan px | Span increase / decrease |
| --- | ---: | ---: | ---: | ---: | ---: |
| Narrow | 1 | +0.016284 | 9 / 0 | −1.788229 | 1 / 17 |
| Narrow | 2 | +0.018016 | 9 / 0 | −1.539440 | 1 / 17 |
| Narrow | 3 | +0.020063 | 9 / 0 | −1.413731 | 4 / 14 |
| Wide | 1 | +0.004145 | 8 / 1 | +2.462332 | 18 / 0 |
| Wide | 2 | +0.008267 | 8 / 1 | +3.045488 | 18 / 0 |
| Wide | 3 | +0.011618 | 9 / 0 | +3.237064 | 18 / 0 |

Both conditions' feature medians increased across the three blocks, and wide span enlargement strengthened descriptively. Thus time/order or carryover may modulate **magnitude**, even though wide span direction repeated across all blocks and sessions. Nothing was excluded for this pattern.

## Matched-natural stabilized-reference diagnostic

This **secondary, post-capture diagnostic** was implemented during Stage 2; it was not a preregistered primary endpoint. An offline oracle holds each target/block's **natural presentation** corner A/B and upper/lower-lid coordinates fixed in the session's face-normalized frame. For each eye, the reference is the coordinate-wise median of its natural-presentation sample points. The analyzer substitutes each natural or changed sample's **measured face-normalized iris center** into that fixed natural corner/lid frame, evaluates the unchanged production vertical formula, averages left/right values **per sample**, then takes presentation medians and subtracts natural from condition. This retains the measured iris series and uses no fitted output correction. The actual comparison remains the saved production binocular presentation-median difference. Natural target/block knowledge and its measured reference make this **nondeployable** as-is; the diagnostic tests only what would remain if that matched corner frame were held fixed. It does not isolate a physical mechanism or independently guarantee fixation.

| Condition | Actual median Δvertical | Fixed-reference median Δvertical | Actual mean | Fixed-reference mean | Absolute effect reduced / worsened |
| --- | ---: | ---: | ---: | ---: | ---: |
| Comfortably narrow | +0.018016 | +0.022948 | +0.016571 | +0.023344 | 2 / 25 |
| Comfortably wide | +0.007585 | −0.002091 | +0.008859 | +0.000923 | 20 / 7 |

For wide, the **mean signed** matched effect fell about **89.6%** (`1−0.000923/0.008859`), but the median fixed-reference effect crossed zero and **7/27** individual absolute effects worsened. For narrow, the mean signed effect instead grew about **40.9%**, and **25/27** absolute effects worsened. There is no universal stable-corner correction here. Subset medians and absolute-effect improvement counts are:

| Condition | Subset | Actual median | Fixed-reference median | Reduced / total |
| --- | --- | ---: | ---: | ---: |
| Narrow | live-1 | +0.016700 | +0.017882 | 1/9 |
| Narrow | live-2 | +0.016601 | +0.022948 | 0/9 |
| Narrow | live-3 | +0.018701 | +0.026729 | 1/9 |
| Narrow | Upper | +0.018134 | +0.021382 | 2/9 |
| Narrow | Center | +0.018016 | +0.026729 | 0/9 |
| Narrow | Lower | +0.016420 | +0.026711 | 0/9 |
| Wide | live-1 | +0.006478 | −0.004308 | 7/9 |
| Wide | live-2 | +0.011582 | −0.000651 | 6/9 |
| Wide | live-3 | +0.008267 | +0.002334 | 7/9 |
| Wide | Upper | +0.011618 | +0.008154 | 8/9 |
| Wide | Center | +0.008267 | −0.000651 | 6/9 |
| Wide | Lower | +0.006245 | −0.004308 | 6/9 |

Across blocks 1/2/3, absolute effects improved in **4/9, 8/9, 8/9** wide comparisons and **2/9, 0/9, 0/9** narrow comparisons. The seven wide failures include both original negative-feature cases and small original positive cases; all are retained: live-1 center/block-1, lower/block-1; live-2 center/block-1, lower/block-1, lower/block-3; live-3 center/block-1, upper/block-2. The 2D alignment and natural-reference substitution do not settle why detected corner and iris points moved. Subset medians are computed independently and need not average to the pooled median.

## Secondary mapped-y context

Only the existing fitted calibration slope is used: `Δmapped y = y_slope × Δvertical feature`, with no clipping or model change. Fixed hypothetical feature changes give:

| Session | y slope | Δfeature 0.005 | 0.010 | 0.018 |
| --- | ---: | ---: | ---: | ---: |
| live-1 | 29.142631 | 0.145713 | 0.291426 | 0.524567 |
| live-2 | 31.999926 | 0.160000 | 0.319999 | 0.575999 |
| live-3 | 37.392960 | 0.186965 | 0.373930 | 0.673073 |

Session median **observed** matched mapped-y changes for narrow were **+0.486679 / +0.531242 / +0.699287**; for wide, **+0.188799 / +0.370627 / +0.309136** (live-1/2/3). These are model-output changes at displayed fixed targets, not independently measured true gaze errors or cursor usability.

## Supported conclusions, unsupported conclusions, and project decision

**Supported:** in three technically valid same-participant sessions, measured opening states separated in every matched triple. Both deliberate narrow and wide states usually raised the vertical feature relative to natural. More importantly, the **detected corner-defined eye reference changed relative to the selected non-eye face anchor template**: wide increased face-normalized corner span in **54/54** eye-level contrasts across every row, session, and block; narrow decreased it in **48/54**. The wide signal is more consistently a corner-span/shape change than a rigid movement of the pair's midpoint. The feature and geometry effects are large enough for fitted slopes to amplify them into material normalized-y output differences. The matched-natural oracle often reduces the wide effect but usually worsens narrow, supporting a condition-dependent mixture rather than a deployable fix.

**Unsupported:** none of these data proves that eye corners anatomically moved, that eyelids alone caused the feature change, that MediaPipe is defective, that the observed iris-center displacement is eyeball rotation, or that the participant's true gaze changed. The chosen anchors are **themselves MediaPipe estimates**, not anatomical ground truth or an independent sensor. A calibration-template 2D similarity does **not** resolve pitch, yaw, depth, perspective, facial deformation, expression-induced anchor movement, or true fixation. This one participant's three sessions do not establish cross-user reliability, population significance, a production correction, a quality threshold, or cursor readiness. Angle, span, midpoint, and iris metrics are coupled through the same detected landmarks; repeated pairs and two eyes are not independent statistical units.

**Project decision:** the sequence of controlled eye-opening, primitive decomposition, and this face-reference study is sufficient to **pause additional root-cause live-camera experiments** for now. The evidence has isolated a systematic *detected-geometry* problem relevant to output y while leaving physical causality unresolved. Another live causal study need not precede a bounded **offline alternative-feature engineering comparison**. This is an evidence-bounded workflow recommendation, not a claim that root cause is solved.

**Recommended next bounded step, not implemented here:** using already captured numerical landmark/anchor records, predeclare and compare a small set of alternative vertical features offline—such as a face-normalized iris coordinate, a reference less sensitive to dynamic corner span, and a session-calibrated stable-reference formulation—against the unchanged production feature. Require preservation of true upper/center/lower ordering and held-out/repeated-target behavior, with no tuning on test presentations. Any promising feature would need separate validation before production use. No new experiment or correction is started in this PR.
