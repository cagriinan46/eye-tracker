# Controlled live vertical sensitivity results

## Data, validity, and method

Çağrı completed all three predeclared, technically valid sessions on the development Mac. The inputs are the original Git-ignored derived-numerical files `.venv/vertical-sensitivity-cagri-live-{1,2,3}.json`; they are not committed. Each contains nine standard 3×3 calibration presentations, pass A over the same nine coordinates, and pass B in exact reverse order. Each used camera index 1, 1920×1080 camera input, a 1200×700 target-window image area, 0.8 s settling plus 1.2 s sampling per presentation, and at least five usable sampling observations per presentation. No raw camera imagery was saved.

| Session | Elapsed (s) | Camera reads, including settling | Sampling attempts / usable / unavailable | Failed camera reads | No-face observations |
| --- | ---: | ---: | ---: | ---: | ---: |
| live-1 | 54.367 | 1,611 | 963 / 963 / 0 | 0 | 0 |
| live-2 | 54.422 | 1,614 | 967 / 967 / 0 | 0 | 0 |
| live-3 | 54.494 | 1,610 | 962 / 962 / 0 | 0 | 0 |

The saved 27 presentation medians in each file exactly matched medians rebuilt from its original numerical sampling rows. The analyzer verified presentation order, exact coordinates, minimum sample counts, and that each saved prediction equals the **unclipped, uncorrected** independent-linear mapping applied to the saved horizontal/vertical features. Each session contributes all nine coordinates and all three planned comparisons per coordinate (27 comparisons); no session or target was selected by result.

Reproduce the calculations from the repository root:

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
import json
from pathlib import Path
from experiments.vertical_sensitivity_live_study.analysis import analyze_session, prepare_report

for number in (1, 2, 3):
    path = Path(f'.venv/vertical-sensitivity-cagri-live-{number}.json')
    report = json.loads(path.read_text())
    assert prepare_report({k: v for k, v in report.items() if k != 'presentations'})['presentations'] == report['presentations']
    print(json.dumps(analyze_session(report), indent=2))
PY
```

Feature values are presentation-level medians of usable observations. A signed difference means later minus earlier. Its mapped-y difference is exactly `y_slope × signed_feature_difference`; it is a model-output change at the **same target**, not an independently measured gaze error. Absolute summaries use all 27 comparisons within each session and the repository's linearly interpolated p95. Tables round for readability; the ignored JSONs retain full precision.

## Measured calibration geometry

| Session | Fitted y slope | Fitted y intercept | Full feature span | Top row median | Center row median | Bottom row median | Top→center | Center→bottom | Minimum adjacent row | Calibration y MAE | y ordering |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | 32.94890 | 2.27082 | 0.017268 | −0.061704 | −0.050657 | −0.047344 | 0.011048 | 0.003312 | 0.003312 | 0.091697 | 27/27 |
| live-2 | 44.13644 | 2.68374 | 0.015471 | −0.054485 | −0.049065 | −0.045613 | 0.005420 | 0.003452 | 0.003452 | 0.108169 | 25/27 |
| live-3 | 30.32154 | 1.98564 | 0.023278 | −0.056784 | −0.046343 | −0.040744 | 0.010441 | 0.005599 | 0.005599 | 0.081819 | 27/27 |

Within-row feature spread across the three X positions is `maximum − minimum` of the three calibration-target medians:

| Session | Top spread | Center spread | Bottom spread |
| --- | ---: | ---: | ---: |
| live-1 | 0.003217 | 0.010810 | 0.001357 |
| live-2 | 0.006352 | 0.004246 | 0.005746 |
| live-3 | 0.008800 | 0.005223 | 0.002168 |

All nine **recorded** calibration vertical-feature medians, by coordinate:

| Target (x,y) | live-1 | live-2 | live-3 |
| --- | ---: | ---: | ---: |
| (0.2, 0.2) | −0.063270 | −0.054485 | −0.054427 |
| (0.5, 0.2) | −0.061704 | −0.058309 | −0.056784 |
| (0.8, 0.2) | −0.060053 | −0.051956 | −0.063227 |
| (0.2, 0.5) | −0.050657 | −0.045099 | −0.046075 |
| (0.5, 0.5) | −0.059060 | −0.049345 | −0.046343 |
| (0.8, 0.5) | −0.048250 | −0.049065 | −0.051298 |
| (0.2, 0.8) | −0.046002 | −0.042838 | −0.039949 |
| (0.5, 0.8) | −0.047359 | −0.048583 | −0.042117 |
| (0.8, 0.8) | −0.047344 | −0.045613 | −0.040744 |

## Measured repeated-target differences

Each comparison cell below is **signed Δfeature / absolute Δfeature / signed mapped Δy**. Thus the absolute mapped-y difference is the magnitude of the last number. Calibration→A compares the calibration presentation with pass A, calibration→B compares it with pass B, and A→B compares the two diagnostic passes at the identical coordinate.

### live-1

| Target (x,y) | Calibration→A | Calibration→B | A→B |
| --- | ---: | ---: | ---: |
| (0.2, 0.2) | +0.001583 / 0.001583 / +0.05217 | +0.001443 / 0.001443 / +0.04756 | −0.000140 / 0.000140 / −0.00461 |
| (0.5, 0.2) | −0.000543 / 0.000543 / −0.01789 | −0.002629 / 0.002629 / −0.08663 | −0.002086 / 0.002086 / −0.06873 |
| (0.8, 0.2) | −0.007476 / 0.007476 / −0.24633 | −0.012799 / 0.012799 / −0.42170 | −0.005323 / 0.005323 / −0.17538 |
| (0.2, 0.5) | +0.000902 / 0.000902 / +0.02973 | −0.000149 / 0.000149 / −0.00492 | −0.001051 / 0.001051 / −0.03464 |
| (0.5, 0.5) | +0.001131 / 0.001131 / +0.03727 | −0.003416 / 0.003416 / −0.11257 | −0.004548 / 0.004548 / −0.14984 |
| (0.8, 0.5) | −0.011533 / 0.011533 / −0.38000 | −0.018975 / 0.018975 / −0.62520 | −0.007442 / 0.007442 / −0.24521 |
| (0.2, 0.8) | +0.003273 / 0.003273 / +0.10783 | −0.003522 / 0.003522 / −0.11606 | −0.006795 / 0.006795 / −0.22390 |
| (0.5, 0.8) | −0.003007 / 0.003007 / −0.09908 | −0.006118 / 0.006118 / −0.20158 | −0.003111 / 0.003111 / −0.10249 |
| (0.8, 0.8) | −0.007974 / 0.007974 / −0.26274 | −0.009185 / 0.009185 / −0.30264 | −0.001211 / 0.001211 / −0.03990 |

### live-2

| Target (x,y) | Calibration→A | Calibration→B | A→B |
| --- | ---: | ---: | ---: |
| (0.2, 0.2) | −0.002483 / 0.002483 / −0.10958 | +0.007157 / 0.007157 / +0.31587 | +0.009639 / 0.009639 / +0.42545 |
| (0.5, 0.2) | +0.006889 / 0.006889 / +0.30406 | +0.008144 / 0.008144 / +0.35947 | +0.001255 / 0.001255 / +0.05541 |
| (0.8, 0.2) | −0.002863 / 0.002863 / −0.12637 | −0.006365 / 0.006365 / −0.28095 | −0.003502 / 0.003502 / −0.15457 |
| (0.2, 0.5) | −0.000642 / 0.000642 / −0.02833 | +0.001683 / 0.001683 / +0.07428 | +0.002325 / 0.002325 / +0.10261 |
| (0.5, 0.5) | +0.002703 / 0.002703 / +0.11931 | +0.003859 / 0.003859 / +0.17031 | +0.001155 / 0.001155 / +0.05100 |
| (0.8, 0.5) | +0.000242 / 0.000242 / +0.01066 | −0.002756 / 0.002756 / −0.12164 | −0.002997 / 0.002997 / −0.13230 |
| (0.2, 0.8) | +0.000822 / 0.000822 / +0.03630 | +0.003123 / 0.003123 / +0.13786 | +0.002301 / 0.002301 / +0.10156 |
| (0.5, 0.8) | +0.004553 / 0.004553 / +0.20094 | +0.004619 / 0.004619 / +0.20389 | +0.000067 / 0.000067 / +0.00295 |
| (0.8, 0.8) | −0.001305 / 0.001305 / −0.05758 | +0.001035 / 0.001035 / +0.04569 | +0.002340 / 0.002340 / +0.10327 |

### live-3

| Target (x,y) | Calibration→A | Calibration→B | A→B |
| --- | ---: | ---: | ---: |
| (0.2, 0.2) | −0.003794 / 0.003794 / −0.11504 | +0.001934 / 0.001934 / +0.05863 | +0.005728 / 0.005728 / +0.17367 |
| (0.5, 0.2) | −0.003816 / 0.003816 / −0.11571 | −0.003696 / 0.003696 / −0.11205 | +0.000121 / 0.000121 / +0.00366 |
| (0.8, 0.2) | +0.009461 / 0.009461 / +0.28688 | +0.003715 / 0.003715 / +0.11266 | −0.005746 / 0.005746 / −0.17422 |
| (0.2, 0.5) | +0.000351 / 0.000351 / +0.01065 | +0.000617 / 0.000617 / +0.01871 | +0.000266 / 0.000266 / +0.00806 |
| (0.5, 0.5) | −0.008364 / 0.008364 / −0.25359 | −0.006031 / 0.006031 / −0.18288 | +0.002332 / 0.002332 / +0.07072 |
| (0.8, 0.5) | −0.001716 / 0.001716 / −0.05202 | −0.006939 / 0.006939 / −0.21041 | −0.005224 / 0.005224 / −0.15839 |
| (0.2, 0.8) | +0.005803 / 0.005803 / +0.17595 | +0.001738 / 0.001738 / +0.05269 | −0.004065 / 0.004065 / −0.12327 |
| (0.5, 0.8) | −0.003207 / 0.003207 / −0.09724 | +0.002124 / 0.002124 / +0.06441 | +0.005331 / 0.005331 / +0.16165 |
| (0.8, 0.8) | −0.005441 / 0.005441 / −0.16498 | −0.001474 / 0.001474 / −0.04469 | +0.003967 / 0.003967 / +0.12029 |

Per-comparison-type absolute summaries (nine coordinates in each row):

| Session | Comparison | Median / p95 / max absolute Δfeature | Median / p95 / max absolute mapped Δy |
| --- | --- | ---: | ---: |
| live-1 | Calibration→A | 0.003007 / 0.010109 / 0.011533 | 0.09908 / 0.33310 / 0.38000 |
| live-1 | Calibration→B | 0.003522 / 0.016504 / 0.018975 | 0.11606 / 0.54380 / 0.62520 |
| live-1 | A→B | 0.003111 / 0.007183 / 0.007442 | 0.10249 / 0.23668 / 0.24521 |
| live-2 | Calibration→A | 0.002483 / 0.005954 / 0.006889 | 0.10958 / 0.26281 / 0.30406 |
| live-2 | Calibration→B | 0.003859 / 0.007749 / 0.008144 | 0.17031 / 0.34203 / 0.35947 |
| live-2 | A→B | 0.002325 / 0.007185 / 0.009639 | 0.10261 / 0.31710 / 0.42545 |
| live-3 | Calibration→A | 0.003816 / 0.009022 / 0.009461 | 0.11571 / 0.27357 / 0.28688 |
| live-3 | Calibration→B | 0.002124 / 0.006576 / 0.006939 | 0.06441 / 0.19940 / 0.21041 |
| live-3 | A→B | 0.004065 / 0.005739 / 0.005746 | 0.12327 / 0.17400 / 0.17422 |

## Cross-session comparison and fixed sensitivity examples

| Session | Calibration span | Minimum adjacent row | y slope | Calibration y MAE | Median / p95 / max absolute Δfeature | Median / p95 / max absolute mapped Δy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | 0.017268 | 0.003312 | 32.94890 | 0.091697 | 0.003273 / 0.012419 / 0.018975 | 0.10783 / 0.40919 / 0.62520 |
| live-2 | 0.015471 | 0.003452 | 44.13644 | 0.108169 | 0.002703 / 0.007848 / 0.009639 | 0.11931 / 0.34639 / 0.42545 |
| live-3 | 0.023278 | 0.005599 | 30.32154 | 0.081819 | 0.003794 / 0.007936 / 0.009461 | 0.11504 / 0.24064 / 0.28688 |

For the same **hypothetical** feature movement, the fitted slope gives these absolute normalized-y changes; these are sensitivity examples, not observed movement:

| Session | Δfeature 0.001 | Δfeature 0.003 | Δfeature 0.005 |
| --- | ---: | ---: | ---: |
| live-1 | 0.03295 | 0.09885 | 0.16474 |
| live-2 | 0.04414 | 0.13241 | 0.22068 |
| live-3 | 0.03032 | 0.09096 | 0.15161 |

## Descriptive interpretation and limits

**Supported observations:** live-2 had the smallest full calibration feature span and the steepest fitted y slope; live-3 had the widest span, strongest minimum adjacent-row separation, and shallowest slope. Thus compressed calibration geometry and steeper mapping recurred descriptively in these controlled sessions. For an equal feature change, live-2's slope maps to the largest y change, exactly as the linear identity specifies. Calibration ordering and fit quality also varied; good calibration ordering alone did not prevent later same-target movement.

**Distinct measured mechanism:** repeated-target feature changes themselves differed across sessions. live-1, despite a lower slope than live-2, had the largest single feature change (−0.018975, calibration→B at x=0.8, y=0.5) and therefore the largest absolute mapped-y difference (0.62520). The session medians of amplified difference were fairly close (0.10783–0.11931) because the median feature differences varied in the opposite direction to slope. The p95 and maximum mapped differences varied more strongly. Tail behavior warrants attention in any later usability assessment, but no cursor-quality threshold follows from this study.

**Bounded conclusion:** these three same-participant live sessions support mapping sensitivity as a useful accounting diagnostic for vertical output instability: a steeper fitted slope amplifies any given feature movement. They also directly show independent repeated-target **feature instability**. The output differences reflect the combination of feature movement and slope; mapping sensitivity alone does not explain which features move or why. The observed span/slope pattern is descriptive across only three sessions, not a statistical or causal relationship.

The fixed-order calibration and the forward/reverse passes do not independently control fixation accuracy, elapsed time, prior targets, eye/face geometry, or other conditions. The study does **not** establish that compressed calibration causes feature movement, that slope causes biological or landmark instability, or that head pose, eyelids, glasses, time, gaze history, camera position, or physiology is the physical cause. These are same-coordinate mapped-output differences, not a 16-trial held-out accuracy or cursor-targeting test. There is no cross-user evidence, production quality gate, production correction, or cursor-readiness decision here. Fatih's earlier near-flat vertical result remains unexplained.

The supplied independent rounded cross-check values agreed with the direct JSON recomputation at their stated precision; no discrepancy was found. No production code or behavior was changed.
