# Vertical-feature covariates in three repeated-target live sessions

## Measured observations and data boundary

The inputs are all three completed Çağrı sessions, `.venv/vertical-sensitivity-cagri-live-{1,2,3}.json`. They remain local and Git-ignored. Each has nine calibration presentations followed by the same nine coordinates in pass A and reverse-order pass B. The analysis retained **27 presentations and all 27 exact-coordinate comparisons per session** (nine calibration→A, nine calibration→B, nine A→B). All 963/967/962 sampling rows in live-1/2/3 were usable. The required binocular, both monocular, both individual and binocular opening, and head-center-y values were present in every usable row. The previous study verified zero failed camera reads and zero no-face observations in each session; no run or outlier was excluded here.

For each presentation, the median of its actual usable raw rows was computed **separately for each field**. Every recomputed binocular vertical median matched the saved presentation median. The per-frame binocular feature equaled `(left_vertical + right_vertical) / 2` exactly in all 963/967/962 checked frames (maximum numerical residual 0 in each session). The maximum difference between a presentation's median binocular feature and the mean of its *separate* left/right medians was 0.000443/0.000243/0.000744 in live-1/2/3. Therefore the common-mode quantity below is descriptive and is not substituted for the recorded binocular median change. See [README.md](README.md) for the complete aggregation, pair, rank, and missing-value rules. All values below are rounded; the analyzer emits full-precision pair records.

## Monocular and common-mode findings

The signed delta is **later minus earlier** at an identical coordinate. `Common = (Δleft + Δright)/2`; `differential = Δleft − Δright`. These are feature units, not mapped screen coordinates. The same-direction denominator excludes zero or missing monocular changes; none occurred in these real comparisons. The p95 uses linear interpolation.

| Session | Same-direction left/right | Median abs Δbinocular | Median abs Δleft / Δright | Median abs common / differential | p95 / max abs differential |
| --- | ---: | ---: | ---: | ---: | ---: |
| live-1 | 20/27 (74.1%) | 0.003273 | 0.003282 / 0.003403 | 0.003203 / 0.001434 | 0.005316 / 0.009865 |
| live-2 | 23/27 (85.2%) | 0.002703 | 0.002752 / 0.002513 | 0.002662 / 0.001214 | 0.003290 / 0.003963 |
| live-3 | 24/27 (88.9%) | 0.003794 | 0.003677 / 0.003902 | 0.003717 / 0.001323 | 0.003400 / 0.003720 |

Across the three sessions, 67/81 pair records had both monocular changes in the same direction; the remaining 14 had opposite signs. This is a description of reused, dependent pair records, **not 81 independent observations**. Every one of the five largest absolute binocular changes in each session had both eyes moving in the same direction. Common-mode change was usually larger than differential change at the session-median level, but monocular disagreement was not absent. The largest differential was 0.009865 in live-1 at (0.2, 0.2), calibration→B: left changed +0.005867 and right −0.003998 while binocular changed only +0.001443. Opposite-direction eye changes can partly cancel in the binocular feature; this does not identify an anatomical or detector problem.

## Head-center association

The table reports **per-session descriptive Spearman rank correlation**, with 27 available pairs per entry. The signed and magnitude questions are distinct: a consistent direction of movement need not mean larger head-center movement accompanies larger feature movement. The median absolute head-center-y pair changes were 0.013251, 0.013519, and 0.014546 in live-1/2/3.

| Session | ρ(Δbinocular vertical, Δhead-center y) | ρ(abs Δbinocular vertical, abs Δhead-center y) |
| --- | ---: | ---: |
| live-1 | +0.444 | −0.181 |
| live-2 | +0.212 | +0.385 |
| live-3 | −0.356 | +0.053 |

The signed direction reverses in live-3, and absolute-change association is inconsistent. Some large binocular changes had small head-center changes: live-1's maximum −0.018975 feature shift had head-center Δ−0.003541; its second-largest −0.012799 shift had head-center Δ−0.000637. The largest live-2 and some live-3 changes did coincide with larger head-center changes, as shown below. This proxy is useful to retain, but it does not give a consistent cross-session signature for the largest feature changes.

## Eye-opening association

Per-session descriptive Spearman correlations again use 27 available pairs each. Eye-opening measures are recorded normalized lid-point features. The left/right columns compare each eye's own vertical and opening changes.

| Session | ρ(Δvertical, Δbinocular opening) | ρ(abs Δvertical, abs Δbinocular opening) | ρ(Δleft vertical, Δleft opening) | ρ(Δright vertical, Δright opening) |
| --- | ---: | ---: | ---: | ---: |
| live-1 | +0.519 | +0.200 | +0.515 | +0.403 |
| live-2 | +0.399 | +0.214 | +0.451 | +0.411 |
| live-3 | +0.295 | +0.156 | +0.314 | +0.205 |

The signed association was positive in each session for binocular and both eye-specific comparisons. The median absolute binocular-opening pair changes were 0.010081, 0.009367, and 0.024474. Feature and binocular-opening deltas had the same sign in 20/27, 20/27, and 17/27 comparisons; among the top five feature changes per session, the counts were 5/5, 5/5, and 4/5. Yet magnitude associations were weak (ρ +0.156 to +0.214), and one of live-3's five largest changes had opposite feature/opening signs. Opening does not explain the size of these changes by itself. Its landmarks and the vertical feature's geometry are related, so even a repeatable association would not identify a physical cause.

## Extreme repeated-target cases

These are the **five largest absolute binocular feature differences in each session**, with no exclusions. Pair types are calibration→A (`C→A`), calibration→B (`C→B`), and A→B. All deltas are signed later minus earlier. `Δmapped y = session y slope × Δbinocular feature` is an unclipped **model-output difference**, not an independently measured gaze error. The same target can appear more than once because its three pair types share presentations.

| Session | Target (x,y) | Pair | Δbinocular | Δleft | Δright | Δhead-center y | Δbinocular opening | y slope | Δmapped y |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | (0.8, 0.5) | C→B | −0.018975 | −0.020129 | −0.017601 | −0.003541 | −0.033467 | 32.94890 | −0.62520 |
| live-1 | (0.8, 0.2) | C→B | −0.012799 | −0.014493 | −0.011257 | −0.000637 | −0.013491 | 32.94890 | −0.42170 |
| live-1 | (0.8, 0.5) | C→A | −0.011533 | −0.011415 | −0.011526 | −0.001297 | −0.016519 | 32.94890 | −0.38000 |
| live-1 | (0.8, 0.8) | C→B | −0.009185 | −0.010017 | −0.008583 | −0.004708 | −0.007039 | 32.94890 | −0.30264 |
| live-1 | (0.8, 0.8) | C→A | −0.007974 | −0.008485 | −0.007337 | −0.013894 | −0.008849 | 32.94890 | −0.26274 |
| live-2 | (0.2, 0.2) | A→B | +0.009639 | +0.009018 | +0.010209 | +0.010700 | +0.028954 | 44.13644 | +0.42545 |
| live-2 | (0.5, 0.2) | C→B | +0.008144 | +0.007517 | +0.008996 | +0.026873 | +0.009842 | 44.13644 | +0.35947 |
| live-2 | (0.2, 0.2) | C→B | +0.007157 | +0.008588 | +0.005816 | +0.037096 | +0.019200 | 44.13644 | +0.31587 |
| live-2 | (0.5, 0.2) | C→A | +0.006889 | +0.006651 | +0.006878 | +0.012669 | +0.007716 | 44.13644 | +0.30406 |
| live-2 | (0.8, 0.2) | C→B | −0.006365 | −0.007355 | −0.005065 | +0.026083 | −0.008503 | 44.13644 | −0.28095 |
| live-3 | (0.8, 0.2) | C→A | +0.009461 | +0.011021 | +0.008603 | +0.025071 | +0.013946 | 30.32154 | +0.28688 |
| live-3 | (0.5, 0.5) | C→A | −0.008364 | −0.008137 | −0.007819 | +0.022134 | −0.054353 | 30.32154 | −0.25359 |
| live-3 | (0.8, 0.5) | C→B | −0.006939 | −0.007131 | −0.006624 | +0.031151 | −0.041415 | 30.32154 | −0.21041 |
| live-3 | (0.5, 0.5) | C→B | −0.006031 | −0.004319 | −0.006963 | +0.009667 | −0.043398 | 30.32154 | −0.18288 |
| live-3 | (0.2, 0.8) | C→A | +0.005803 | +0.004150 | +0.007452 | +0.003501 | −0.039107 | 30.32154 | +0.17595 |

The top cases show a common recorded binocular pattern—both monocular features moved in the same direction—but **no single head-center or opening magnitude** accompanied every extreme case. In live-1 the four largest feature changes had comparatively small head-center shifts. Live-2's top five generally had larger head-center shifts. In live-3, head-center shifts were mostly positive while binocular changes had both signs. Opening sign matched feature sign in 14/15 listed comparisons, but its magnitude did not scale consistently with feature magnitude.

## Secondary within-presentation spread

The measure here is `p95 − p05` across usable samples within each 1.2-second presentation. It is distinct from the repeated-visit median difference above.

| Session | Median / max vertical spread | Median / max head-center-y spread | Median / max binocular-opening spread |
| --- | ---: | ---: | ---: |
| live-1 | 0.007326 / 0.017021 | 0.009786 / 0.065732 | 0.011266 / 0.025255 |
| live-2 | 0.006622 / 0.060242 | 0.009927 / 0.053104 | 0.010412 / 0.236978 |
| live-3 | 0.009038 / 0.049210 | 0.013153 / 0.024043 | 0.014309 / 0.216080 |

For live-1's largest pair, the calibration and pass-B within-presentation vertical spreads were 0.004434 and 0.003768, both below the 0.018975 difference between their medians. Some other presentations were much less internally stable: live-3's exact CENTER pass A had vertical spread 0.049210 and participates in its second-largest repeated-target change. Thus visit-level shifts and within-visit spread both appear; this secondary measure cannot assign a cause or define a quality gate.

## Supported conclusions, unsupported conclusions, and limits

**Supported:** same-target binocular changes were usually accompanied by left and right vertical changes in the same direction, including all 15 listed extreme pair records. Common-mode differences generally exceeded differential differences at the session-median level, while a few opposing monocular changes were large enough to cancel materially in the binocular average. Head-center associations were inconsistent across sessions. Signed eye-opening association was positive in all three sessions and is the most consistent **recorded covariate** for planning a targeted follow-up, but its association with change *magnitude* was weak and it did not explain every extreme case.

**Unsupported:** these measurements do not show that opening, head motion, eyelids, camera perspective, MediaPipe, or a biological process *caused* feature instability. They do not establish a validated correction, threshold, production or cursor readiness, cross-user reliability, or a statistical population relationship. The same participant completed all three short sessions. Each coordinate contributes three overlapping comparisons, and presentation order, elapsed time, prior gaze targets, fixation accuracy, and eye/face geometry were not independently controlled. Head-center y is a coarse image proxy that cannot separate translation from pitch; opening and vertical features share landmark geometry. The reversed pass reduces some order confounding but does not remove these limits. Fatih's earlier near-flat vertical behavior remains unexplained.

## Recommended next experiment

If the team approves another human study, **independently vary or control eye opening while holding an identical target and measured head geometry as steady as practicable**, with condition order balanced and raw numerical measurements retained. Eye opening is the most useful recorded candidate to isolate because its signed association recurred in all three sessions and most largest feature changes; it is **not a demonstrated cause or production correction**. The design should also retain per-eye features and a stronger independent head-pose measure, since common-mode movement could reflect a shared condition not captured by eye opening. No new session or production change is started by this report.
