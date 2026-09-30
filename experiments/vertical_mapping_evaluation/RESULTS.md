# Issue #50 — Alternative vertical calibration mappings

## Inputs and method

The offline analyzer read the existing, Git-ignored derived-numerical files `.venv/vertical-drift-cagri-A.json` and `.venv/vertical-drift-cagri-B.json` separately. These are two completed Çağrı sessions, **not** two users or independent population samples. Each contains nine calibration targets and 16 distinct held-out presentations (eight interstitial positions repeated twice). No new camera run was made. The current production median aggregator and independent-linear fitter reproduced both recorded coefficient sets; replaying the 16 held-out trials reproduced the saved baseline predictions. This confirms that both candidates below were evaluated on the same recorded feature observations.

The baseline is the current independent-linear mapping. The sole alternative has three anchors: for each calibration y row, take the median of its three per-target **median** vertical features and pair it with that row's known target y. Both sessions' anchors ordered strictly top < center < bottom. The alternative linearly interpolates on top→center and center→bottom segments, extending the nearest segment beyond the outer anchors without clipping. The horizontal mapping is unchanged. Neither candidate used held-out targets for fitting or tuning. The [protocol and reproducible command](README.md) explain these choices.

Signed residual and signed bias below mean **predicted minus target**. Lower calibration error is a fit observation, not held-out evidence. Coordinates are normalized to the target window.

| Session | Top anchor (feature → y) | Center anchor | Bottom anchor | Top→center slope | Center→bottom slope |
| --- | --- | --- | --- | ---: | ---: |
| A | −0.050736 → 0.20 | −0.044915 → 0.50 | −0.032562 → 0.80 | 51.53 | 24.29 |
| B | −0.050399 → 0.20 | −0.048167 → 0.50 | −0.038094 → 0.80 | 134.44 | 29.78 |

Both piecewise mappings are monotonic by construction, as are the fitted positive-slope linear y mappings in these sessions. The relatively narrow top→center feature span in B gives that segment a steep slope; this is measured calibration geometry, not a hand-tuned parameter.

## Calibration fit

| Session | Mapping | Nine-target y MAE | Exact CENTER signed residual |
| --- | --- | ---: | ---: |
| A | Independent linear | 0.10176 | −0.08903 |
| A | Piecewise row-anchor | 0.09577 | −0.03650 |
| B | Independent linear | 0.11773 | −0.13111 |
| B | Piecewise row-anchor | 0.08780 | 0.00000 |

The following rows report the **mean predicted y**, mean signed residual, and MAE across the three calibration targets in each y row; the per-target predictions appear immediately afterward.

| Session | Target y row | Linear mean prediction / signed residual / MAE | Piecewise mean prediction / signed residual / MAE |
| --- | ---: | --- | --- |
| A | 0.20 | 0.29365 / +0.09365 / 0.09365 | 0.25216 / +0.05216 / 0.12502 |
| A | 0.50 | 0.50500 / +0.00500 / 0.11020 | 0.55620 / +0.05620 / 0.08053 |
| A | 0.80 | 0.70135 / −0.09865 / 0.10144 | 0.72933 / −0.07067 / 0.08176 |
| B | 0.20 | 0.29700 / +0.09700 / 0.09700 | 0.19789 / −0.00211 / 0.06974 |
| B | 0.50 | 0.45090 / −0.04910 / 0.14383 | 0.54671 / +0.04671 / 0.12284 |
| B | 0.80 | 0.75210 / −0.04790 / 0.11237 | 0.85673 / +0.05673 / 0.07083 |

### Session A: every calibration target

| Target (x,y) | Linear y / signed residual | Piecewise y / signed residual |
| --- | --- | --- |
| (0.20, 0.20) | 0.4122 / +0.2122 | 0.4658 / +0.2658 |
| (0.50, 0.20) | 0.2040 / +0.0040 | 0.0907 / −0.1093 |
| (0.80, 0.20) | 0.2647 / +0.0647 | 0.2000 / 0.0000 |
| (0.20, 0.50) | 0.6728 / +0.1728 | 0.7051 / +0.2051 |
| **(0.50, 0.50)** | **0.4110 / −0.0890** | **0.4635 / −0.0365** |
| (0.80, 0.50) | 0.4312 / −0.0688 | 0.5000 / 0.0000 |
| (0.20, 0.80) | 0.7846 / −0.0154 | 0.8000 / 0.0000 |
| (0.50, 0.80) | 0.8042 / +0.0042 | 0.8166 / +0.0166 |
| (0.80, 0.80) | 0.5153 / −0.2847 | 0.5714 / −0.2286 |

### Session B: every calibration target

| Target (x,y) | Linear y / signed residual | Piecewise y / signed residual |
| --- | --- | --- |
| (0.20, 0.20) | 0.3216 / +0.1216 | 0.3014 / +0.1014 |
| (0.50, 0.20) | 0.2975 / +0.0975 | 0.2000 / 0.0000 |
| (0.80, 0.20) | 0.2719 / +0.0719 | 0.0922 / −0.1078 |
| (0.20, 0.50) | 0.6421 / +0.1421 | 0.7543 / +0.2543 |
| **(0.50, 0.50)** | **0.3689 / −0.1311** | **0.5000 / 0.0000** |
| (0.80, 0.50) | 0.3417 / −0.1583 | 0.3858 / −0.1142 |
| (0.20, 0.80) | 0.8967 / +0.0967 | 0.9913 / +0.1913 |
| (0.50, 0.80) | 0.6684 / −0.1316 | 0.7789 / −0.0211 |
| (0.80, 0.80) | 0.6912 / −0.1088 | 0.8000 / 0.0000 |

Even the fitted piecewise model does not force each of the three targets in a row to land at that row's y; only the row-median **feature anchor** lands exactly there. It can therefore reduce one target's residual while worsening another's.

## Held-out validation

| Session | Mapping | y MAE | Median absolute y error | p95 absolute y error | Signed y bias | y ordering | Predicted-y range |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| A | Independent linear | 0.18687 | 0.19240 | 0.27464 | −0.18687 | 21/21 | 0.12082 to 0.52000 |
| A | Piecewise row-anchor | 0.21954 | 0.20215 | 0.38463 | −0.21954 | 21/21 | −0.05919 to 0.57537 |
| B | Independent linear | 0.17961 | 0.20328 | 0.33191 | −0.16781 | 20/21 | 0.12170 to 0.74438 |
| B | Piecewise row-anchor | 0.36412 | 0.26392 | 0.87195 | −0.32229 | 20/21 | −0.53876 to 0.84954 |

The table uses per-trial **median** predictions from the same held-out frames and the existing validation metric definitions. x was identical for the two candidates: Session A x MAE 0.06572, signed x bias −0.06572, x ordering 21/21; Session B x MAE 0.04414, signed x bias −0.04414, x ordering 21/21. The changed y results therefore do not come from a changed horizontal model.

### Each held-out trial (actual y → linear prediction / piecewise prediction)

| Target / trial | Actual y | A linear / piecewise y | B linear / piecewise y |
| --- | ---: | --- | --- |
| V-1 / 1 | 0.35 | 0.1390 / −0.0264 | 0.2909 / 0.1722 |
| V-1 / 2 | 0.35 | 0.1684 / 0.0265 | 0.2339 / −0.0671 |
| V-2 / 1 | 0.35 | 0.1208 / −0.0592 | 0.1217 / −0.5388 |
| V-2 / 2 | 0.35 | 0.1455 / −0.0148 | 0.1309 / −0.5001 |
| V-3 / 1 | 0.65 | 0.5200 / 0.5754 | 0.5146 / 0.6356 |
| V-3 / 2 | 0.65 | 0.4331 / 0.5016 | 0.7444 / 0.8495 |
| V-4 / 1 | 0.65 | 0.4356 / 0.5037 | 0.2930 / 0.1810 |
| V-4 / 2 | 0.65 | 0.3499 / 0.3535 | 0.3265 / 0.3217 |
| V-5 / 1 | 0.35 | 0.2655 / 0.2014 | 0.1455 / −0.4389 |
| V-5 / 2 | 0.35 | 0.2347 / 0.1459 | 0.1270 / −0.5164 |
| V-6 / 1 | 0.50 | 0.3151 / 0.2908 | 0.3748 / 0.5055 |
| V-6 / 2 | 0.50 | 0.3340 / 0.3249 | 0.2415 / −0.0355 |
| V-7 / 1 | 0.65 | 0.4501 / 0.5160 | 0.4478 / 0.5735 |
| V-7 / 2 | 0.65 | 0.3838 / 0.4146 | 0.4456 / 0.5714 |
| V-8 / 1 | 0.50 | 0.3944 / 0.4337 | 0.3821 / 0.5123 |
| V-8 / 2 | 0.50 | 0.3201 / 0.2998 | 0.4949 / 0.6173 |

The piecewise model had **225 of 572** usable held-out frames outside its outer calibration feature anchors in A (affecting 12/16 trials), and **285 of 573** in B (affecting 13/16 trials). The nearest segment was extrapolated on those frames. Three A and six B piecewise trial medians predicted y below zero; none of the baseline trial medians did. Predictions were intentionally left unclipped, so these failures remain visible. Extrapolation and the steep B top→center segment coincide with large B tail errors; these observations do not isolate the cause of the underlying feature movement.

## Interpretation and limitations

**Outcome C — calibration residual improved, but held-out behavior did not.** The piecewise candidate lowered nine-target y MAE and the exact calibration-CENTER residual in both sessions, but increased held-out y MAE, median error, p95 error, and negative signed bias in both. It preserved the same descriptive y ordering (21/21 A, 20/21 B), which does not compensate for its larger coordinate errors. On these two sessions, the independent-linear baseline remains the safer experimental comparator; this result does **not** establish it as a permanent production winner.

These are two short runs by one person in which later feature movement was already observed. The study compares candidate outputs on the same recorded frames but cannot remove or explain that drift, establish performance for Fatih or other users, or claim statistical significance. An alternative that fits the calibration anchors better may amplify feature changes or extrapolate more sharply after calibration. No production mapping, filter, offset, or compensation has been adopted. The piecewise candidate does **not** earn a production-validation step from these data. Further work on the source and positional dependence of the vertical feature should be separately approved rather than tuning this model against these held-out answers.
