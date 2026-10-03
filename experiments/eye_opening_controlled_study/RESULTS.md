# Corrected eye-opening controlled study: three protocol-v2 sessions

## Corrected protocol and capture validity

The participant (`cagri`) completed three **new** sessions with the corrected flow: a centered 1.5-second condition cue appeared alone, disappeared, and was followed by target-only settling and sampling. A READY screen preceded calibration. The participant confirmed deliberately maintaining the instructed comfortable `narrow`, `natural`, or `wide` opening while looking only at the target, with posture as constant as practical. The earlier three captures were withdrawn as **protocol-invalid pilot attempts** after the participant clarified that no deliberate opening manipulation occurred in them. They remain locally preserved under `-protocol-invalid.json` names and contribute **no data** below. PR #59 was closed unmerged.

Only `.venv/eye-opening-cagri-live-{1,2,3}.json` were analyzed. All have `protocol_version=2`, `cue_seconds=1.5`, `ready_screen_used=true`, the expected participant/session ID, nine calibration and 27 diagnostic presentations in the fixed schedule (36 total), all 27 target × condition × block combinations, zero failed camera reads, and zero no-face observations. Every raw sampling row was usable: 1,217 / 1,220 / 1,218 rows in live-1/2/3; every presentation had 32–35 usable samples, above the required five. Elapsed capture time was 113.54 / 113.57 / 113.53 seconds. The required binocular vertical, left/right vertical, binocular opening, and head-center-y fields were present in every diagnostic usable row. No session or comparison was removed.

For each presentation, the analysis takes the median of the actual usable raw samples **separately for each field**. Every saved binocular vertical median matched the recomputation, and the per-sample binocular vertical equaled the mean of the two per-eye features. The median of per-eye presentation medians need not exactly equal the median of per-sample binocular means, so common mode is kept as a descriptive decomposition. Matched differences below always mean **second condition minus first** at the same target and block. Full-precision presentation and 27 matched-pair records per session are reproducible with the [analyzer](analysis.py) and the command in [README.md](README.md); displayed values are rounded.

## Manipulation check: measured opening

The expected **narrow < natural < wide** opening order held in **9/9 target/block triples in each session, 27/27 total**. No threshold was selected after seeing data. The separations were also substantial in the measured feature, unlike the withdrawn pilot. The table gives medians of the nine presentation-level opening medians per condition; the pairwise columns are medians of nine **matched differences**, which need not equal differences of the condition medians.

| Session | Narrow | Natural | Wide | Narrow − natural | Wide − natural | Wide − narrow | Ordered triples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | 0.186780 | 0.301902 | 0.367373 | −0.121727 | +0.077639 | +0.202681 | 9/9 |
| live-2 | 0.161651 | 0.292431 | 0.359926 | −0.132353 | +0.076848 | +0.207495 | 9/9 |
| live-3 | 0.185128 | 0.291880 | 0.376389 | −0.113318 | +0.083044 | +0.176499 | 9/9 |

The 27 measured triples, computed from raw-sample presentation medians, are retained here so the manipulation can be inspected at its declared matching level:

| Session | Target | Block | Narrow | Natural | Wide | Narrow − natural | Wide − natural | Wide − narrow |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | upper | 1 | 0.166126 | 0.321685 | 0.396276 | -0.155559 | +0.074591 | +0.230150 |
| live-1 | upper | 2 | 0.186780 | 0.307933 | 0.389461 | -0.121154 | +0.081528 | +0.202681 |
| live-1 | upper | 3 | 0.164628 | 0.292078 | 0.347164 | -0.127450 | +0.055087 | +0.182537 |
| live-1 | center | 1 | 0.210006 | 0.331733 | 0.415829 | -0.121727 | +0.084096 | +0.205823 |
| live-1 | center | 2 | 0.207524 | 0.308120 | 0.404478 | -0.100595 | +0.096359 | +0.196954 |
| live-1 | center | 3 | 0.098874 | 0.289734 | 0.367373 | -0.190860 | +0.077639 | +0.268499 |
| live-1 | lower | 1 | 0.191081 | 0.301902 | 0.361259 | -0.110821 | +0.059357 | +0.170178 |
| live-1 | lower | 2 | 0.122356 | 0.269109 | 0.350988 | -0.146753 | +0.081878 | +0.228632 |
| live-1 | lower | 3 | 0.216978 | 0.292361 | 0.345296 | -0.075383 | +0.052935 | +0.128318 |
| live-2 | upper | 1 | 0.115292 | 0.313171 | 0.401902 | -0.197880 | +0.088731 | +0.286611 |
| live-2 | upper | 2 | 0.193873 | 0.326226 | 0.401368 | -0.132353 | +0.075141 | +0.207495 |
| live-2 | upper | 3 | 0.220178 | 0.289370 | 0.343642 | -0.069192 | +0.054273 | +0.123464 |
| live-2 | center | 1 | 0.112539 | 0.308578 | 0.404123 | -0.196039 | +0.095545 | +0.291584 |
| live-2 | center | 2 | 0.203741 | 0.294257 | 0.394416 | -0.090516 | +0.100159 | +0.190675 |
| live-2 | center | 3 | 0.181342 | 0.292431 | 0.327157 | -0.111089 | +0.034727 | +0.145816 |
| live-2 | lower | 1 | 0.161651 | 0.283078 | 0.359926 | -0.121427 | +0.076848 | +0.198275 |
| live-2 | lower | 2 | 0.104478 | 0.252456 | 0.350642 | -0.147979 | +0.098186 | +0.246164 |
| live-2 | lower | 3 | 0.125493 | 0.279402 | 0.343360 | -0.153909 | +0.063958 | +0.217868 |
| live-3 | upper | 1 | 0.185128 | 0.309092 | 0.391199 | -0.123963 | +0.082107 | +0.206071 |
| live-3 | upper | 2 | 0.182243 | 0.320636 | 0.418965 | -0.138392 | +0.098329 | +0.236722 |
| live-3 | upper | 3 | 0.214089 | 0.291880 | 0.376389 | -0.077791 | +0.084509 | +0.162301 |
| live-3 | center | 1 | 0.208665 | 0.314832 | 0.375527 | -0.106166 | +0.060695 | +0.166861 |
| live-3 | center | 2 | 0.187151 | 0.295195 | 0.379762 | -0.108045 | +0.084567 | +0.192611 |
| live-3 | center | 3 | 0.176091 | 0.289409 | 0.399720 | -0.113318 | +0.110311 | +0.223629 |
| live-3 | lower | 1 | 0.186857 | 0.280312 | 0.363356 | -0.093455 | +0.083044 | +0.176499 |
| live-3 | lower | 2 | 0.157877 | 0.286469 | 0.332327 | -0.128593 | +0.045858 | +0.174451 |
| live-3 | lower | 3 | 0.165300 | 0.280309 | 0.337580 | -0.115009 | +0.057271 | +0.172280 |

## Primary fixed-target condition comparisons

Each row below summarizes 27 matched target × block comparisons across all three sessions. The direction counts refer to binocular vertical feature change. All 81 comparisons remain in the analyzer output; no condition is relabeled based on measured opening. Pooled medians are descriptive summaries of repeated measures from **one participant**, not independent population estimates.

| Contrast | Median Δopening | Median Δvertical | Δvertical positive / negative | Median Δleft / Δright | Median Δhead-center y |
| --- | ---: | ---: | ---: | ---: | ---: |
| Narrow − natural | −0.121427 | +0.005528 | 21 / 6 | +0.010983 / +0.000763 | −0.000413 |
| Wide − natural | +0.081528 | +0.004477 | 19 / 8 | +0.002633 / +0.006624 | −0.001172 |
| Wide − narrow | +0.198275 | +0.000703 | 15 / 12 | −0.003976 / +0.005557 | −0.000926 |

Session medians show that the narrow and wide contrasts do not have identical size or consistency:

| Session | Narrow − natural Δvertical (positive/negative) | Wide − natural Δvertical (positive/negative) | Wide − narrow Δvertical (positive/negative) |
| --- | ---: | ---: | ---: |
| live-1 | +0.011816 (8/1) | +0.002892 (5/4) | −0.003666 (4/5) |
| live-2 | +0.004369 (6/3) | +0.004477 (8/1) | +0.003630 (5/4) |
| live-3 | +0.005250 (7/2) | +0.005179 (6/3) | +0.000703 (6/3) |

## Target-row dependence

The fixed-target condition effect varies by displayed target row. Each cell is the median of nine session × block matched vertical-feature differences, with positive/negative count. Upper and center were usually positive for **both** changed opening states relative to natural. At the lower target, wide − natural was negative in six of nine comparisons, while narrow − natural was still positive in six of nine. This descriptive row interaction argues against one global opening coefficient.

| Target y | Narrow − natural | Wide − natural | Wide − narrow |
| --- | ---: | ---: | ---: |
| Upper (0.25) | +0.009896 (8/1) | +0.013077 (8/1) | +0.003672 (6/3) |
| Center (0.50) | +0.005250 (7/2) | +0.007256 (8/1) | +0.004590 (6/3) |
| Lower (0.75) | +0.004897 (6/3) | −0.001596 (3/6) | −0.007493 (3/6) |

## Measured opening versus vertical change

Measured opening changed in the requested direction in all 27 triples, but vertical change is **not monotonic in opening**: both narrower and wider than natural often produced a positive vertical-feature difference, especially at upper and center gaze. A wide − narrow comparison had positive vertical change only 15/27 times despite consistently greater measured opening. Strict vertical ordering with narrow < natural < wide was therefore not the general pattern.

The table reports descriptive Spearman rank correlations between **matched Δmeasured binocular opening** and **matched Δbinocular vertical**, using all 27 contrast records per session. The contrast-specific columns each use nine records; they help show why one pooled signed association obscures the bent condition response. These overlapping contrasts share presentations. The correlations have no p-values or causal/population interpretation.

| Session | All three contrasts ρ | Narrow − natural ρ | Wide − natural ρ | Wide − narrow ρ |
| --- | ---: | ---: | ---: | ---: |
| live-1 | −0.585 | −0.933 | +0.417 | −0.300 |
| live-2 | −0.206 | −0.917 | +0.667 | −0.050 |
| live-3 | −0.123 | −0.833 | +0.683 | +0.167 |

The per-session all-contrast association changes in strength, and the within-contrast signs differ. The 81-record pooled descriptive ρ is −0.303, but it combines repeated presentations and distinct condition contrasts. Neither this number nor a straight-line fit is an appropriate production correction.

## Monocular and common-mode behavior

For each matched pair, `common = (Δleft + Δright)/2` and `differential = Δleft − Δright`. The two eyes changed in the same direction for **19/27 narrow − natural**, **24/27 wide − natural**, and **17/27 wide − narrow** comparisons. The session counts for these contrasts were live-1 **6/9, 9/9, 5/9**; live-2 **6/9, 7/9, 8/9**; live-3 **7/9, 8/9, 4/9**, respectively. Thus the strong common-direction pattern for wide versus natural strengthens the earlier observational finding, while monocular disagreement remains material, especially for wide versus narrow.

| Contrast | Median signed common | Median abs common | Median signed differential | Median abs differential | Same / opposite direction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Narrow − natural | +0.005657 | 0.005657 | +0.008829 | 0.008829 | 19 / 8 |
| Wide − natural | +0.004356 | 0.005237 | −0.002974 | 0.002974 | 24 / 3 |
| Wide − narrow | +0.000736 | 0.006444 | −0.010990 | 0.010990 | 17 / 10 |

Narrow − natural had a larger median left-eye than right-eye shift, so it should not be described as uniformly common-mode despite 19 same-direction pairs. These are landmark-derived measurements, not evidence of which anatomical part moved or whether a detector erred. No binocular value was replaced with common mode.

## Head-center diagnostic

Across all 81 matched comparisons, median absolute Δhead-center y was **0.000936** (maximum **0.005327**). By contrast it was 0.000742 for narrow − natural, 0.001390 for wide − natural, and 0.000990 for wide − narrow. Per-session median absolute changes across 27 contrasts were 0.000592 / 0.001120 / 0.001401. Descriptive Spearman correlations between signed Δhead-center y and Δvertical were −0.252 / −0.258 / −0.305 in live-1/2/3. These image-coordinate changes are small relative to the vertical-feature contrasts, but their unit and geometry differ; size alone cannot establish that they are irrelevant. Head-center y is one coarse proxy and cannot rule out pitch, rotation, camera geometry, or unmeasured pose changes. No causal direction is assigned.

## Secondary mapped-y context

The fresh standard calibration slopes were **26.2731 / 28.6757 / 27.3817** for live-1/2/3. These are used only in `Δmapped y = y_slope × Δvertical`, without clipping or a new mapping. A representative feature difference of **0.005** maps to absolute normalized-y differences of **0.1314 / 0.1434 / 0.1369** at those slopes. For the observed narrow − natural session median feature differences, the corresponding model-output differences are **+0.3104 / +0.1253 / +0.1438**; for wide − natural, **+0.0760 / +0.1284 / +0.1418**. These are mapped-output changes at fixed targets, not independent measurements of fixation error or cursor usability.

## Supported conclusions

Under the corrected, participant-confirmed protocol, the measured opening manipulation separated cleanly in **27/27** matched triples. Deliberately changing comfortable eye-opening state at a fixed displayed target was accompanied by repeatable vertical-feature shifts. In particular, narrow and wide were often both shifted positively relative to natural at upper and center gaze; lower-row wide behavior differed. Substantial shifts were frequently in the same direction for both eyes, especially wide versus natural. This is stronger controlled evidence than the earlier observational opening association, while the shape and row dependence mean **opening magnitude alone is not a simple global predictor**.

## Unsupported conclusions and limitations

The study does **not** establish that eyelids are the sole physical cause of earlier instability, that MediaPipe is defective, that eye opening alone explains session drift, or that a linear or any other production correction is justified. It does not establish cross-user generalization, cursor readiness, or production quality. There are only three short sessions from **one participant**; repeated contrast records share presentations. The protocol fixes the displayed target, but has no independent gaze fixation measurement. Participants may alter lid shape, eye musculature, or subtle pose along with aperture; opening and vertical measures share landmarks. Head-center y is coarse. Balanced condition order limits simple sequence bias but does not remove time or carryover effects. Camera images/video were not saved, so any later landmark-level investigation needs a separately approved numerical capture design. The withdrawn protocol-invalid pilots are not evidence for or against the corrected manipulation.

## Recommended next controlled experiment

If approved separately, isolate **aperture magnitude** from **eyelid/eye-shape and landmark-geometry configuration** at fixed upper, center, and lower targets. A bounded design could use several comfortable intermediate opening levels and retain the numerical landmarks that define lid opening and the local eye axis, along with an independent head-pose diagnostic. It should test whether presentations with similar measured aperture but different instructed configuration yield the same vertical feature, while preserving per-eye data and order balance. This would target the observed nonmonotonic, row-dependent response without selecting a production correction or starting another run here.
