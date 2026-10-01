# Offline vertical mapping sensitivity results

## Measured input and reconstruction boundary

Seven real local numerical sessions were usable: fixed-CENTER live-1/live-2, Issue #44 collapse A/B, Issue #46 drift A/B, and Issue #52 controlled-1. All are from **Çağrı**. The first six have fresh 3×3 calibration and 16 held-out presentations; controlled-1 has fresh calibration and two reversed-order diagnostic passes over the nine grid targets, but no held-out validation block. Issue #46 additionally has five repeated CENTER checkpoints. No new camera data were collected. No Fatih numerical diagnostic file was available for this analysis; the earlier near-flat Fatih result remains unresolved.

Issue #44's original per-target calibration features were read directly. Issue #46 and #52 calibration features were reaggregated from original usable frames with the production median rule; their fitted coefficients matched the saved mappings. The fixed-CENTER live reports lack the nine stored feature medians, so those values below are **algebraically reconstructed** from the recorded calibration predictions using `(predicted_y - y_intercept) / y_slope`. Their recorded exact calibration CENTER features agreed with this reconstruction. This gives the nine fitter inputs but cannot recover within-presentation raw feature distributions. No held-out result was used to derive a calibration feature.

## Calibration geometry and fit

The following are per-target vertical features used by each session's linear fit. Columns are the nine 3×3 calibration target IDs, ordered top/center/bottom and left/center/right. Live values are reconstructed as described above; the other values are from recorded original features.

| Session | C-1-1 | C-1-2 | C-1-3 | C-2-1 | C-2-2 | C-2-3 | C-3-1 | C-3-2 | C-3-3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | −0.03961906 | −0.03875867 | −0.04101874 | −0.03867111 | −0.03967325 | −0.03722570 | −0.03369032 | −0.03226985 | −0.03923994 |
| live-2 | −0.06341773 | −0.07176080 | −0.07005666 | −0.04581251 | −0.05695507 | −0.05285542 | −0.03808259 | −0.04964068 | −0.04981056 |
| collapse A | −0.05327407 | −0.05674419 | −0.05557193 | −0.04984547 | −0.04987312 | −0.05110124 | −0.04228109 | −0.04277709 | −0.04114196 |
| collapse B | −0.05209556 | −0.05379506 | −0.05283515 | −0.04450259 | −0.04816740 | −0.04577055 | −0.03972714 | −0.03880427 | −0.04066972 |
| drift A | −0.04557900 | −0.05285711 | −0.05073620 | −0.03647001 | −0.04562300 | −0.04491467 | −0.03256232 | −0.03187723 | −0.04197620 |
| drift B | −0.04964410 | −0.05039861 | −0.05120026 | −0.03962743 | −0.04816719 | −0.04901663 | −0.03166935 | −0.03880407 | −0.03809404 |
| controlled-1 | −0.04897076 | −0.06591600 | −0.05425785 | −0.04867341 | −0.04966356 | −0.04214736 | −0.04202379 | −0.03752299 | −0.03372255 |

Each row summary below is the median of its three per-target features, followed by the feature spread across those X positions. Separations are signed differences between adjacent **row medians**. Full span is the maximum minus minimum of all nine target features; minimum separation is the smaller adjacent-row value.

| Session | Top median / spread | Center median / spread | Bottom median / spread | Full span | Top→center | Center→bottom | Minimum separation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | −0.039619 / 0.002260 | −0.038671 / 0.002448 | −0.033690 / 0.006970 | 0.008749 | 0.000948 | 0.004981 | 0.000948 |
| live-2 | −0.070057 / 0.008343 | −0.052855 / 0.011143 | −0.049641 / 0.011728 | 0.033678 | 0.017201 | 0.003215 | 0.003215 |
| collapse A | −0.055572 / 0.003470 | −0.049873 / 0.001256 | −0.042281 / 0.001635 | 0.015602 | 0.005699 | 0.007592 | 0.005699 |
| collapse B | −0.052835 / 0.001699 | −0.045771 / 0.003665 | −0.039727 / 0.001865 | 0.014991 | 0.007065 | 0.006043 | 0.006043 |
| drift A | −0.050736 / 0.007278 | −0.044915 / 0.009153 | −0.032562 / 0.010099 | 0.020980 | 0.005822 | 0.012352 | 0.005822 |
| drift B | −0.050399 / 0.001556 | −0.048167 / 0.009389 | −0.038094 / 0.007135 | 0.019531 | 0.002231 | 0.010073 | 0.002231 |
| controlled-1 | −0.054258 / 0.016945 | −0.048673 / 0.007516 | −0.037523 / 0.008301 | 0.032193 | 0.005584 | 0.011150 | 0.005584 |

| Session | Fitted y slope / intercept | Calibration y MAE | Calibration y ordering | Held-out y MAE | Held-out median abs | Held-out p95 abs | Held-out y ordering |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | 61.96450 / 2.84203 | 0.13457 | 22/27 | 0.31916 | 0.27481 | 0.63963 | 17/21 |
| live-2 | 20.07176 / 1.61151 | 0.09637 | 25/27 | 0.09453 | 0.10515 | 0.17350 | 20/21 |
| collapse A | 43.34105 / 2.63147 | 0.04306 | 27/27 | 0.13543 | 0.08175 | 0.32788 | 21/21 |
| collapse B | 43.82747 / 2.52759 | 0.04044 | 27/27 | 0.21606 | 0.19362 | 0.40336 | 21/21 |
| drift A | 28.60586 / 1.71605 | 0.10176 | 25/27 | 0.18687 | 0.19240 | 0.27464 | 21/21 |
| drift B | 31.99278 / 1.90989 | 0.11773 | 27/27 | 0.17961 | 0.20328 | 0.33191 | 20/21 |
| controlled-1 | 22.69249 / 1.56629 | 0.11133 | 26/27 | — | — | — | — |

The calibration and held-out target sets differ, so their MAEs are descriptive scores of different presentations. A low calibration MAE alone does not establish held-out stability.

## Sensitivity and repeated-target behavior

The fixed changes below are **illustrative inputs**, not measured motion or thresholds. Every value is the session's saved `y_slope × Δvertical_feature`, in normalized screen y; all seven slopes are positive.

| Session | Δfeature 0.001 | Δfeature 0.003 | Δfeature 0.005 |
| --- | ---: | ---: | ---: |
| live-1 | 0.06196 | 0.18589 | 0.30982 |
| live-2 | 0.02007 | 0.06022 | 0.10036 |
| collapse A | 0.04334 | 0.13002 | 0.21671 |
| collapse B | 0.04383 | 0.13148 | 0.21914 |
| drift A | 0.02861 | 0.08582 | 0.14303 |
| drift B | 0.03199 | 0.09598 | 0.15996 |
| controlled-1 | 0.02269 | 0.06808 | 0.11346 |

Each repeated-target entry below compares the **later** presentation median with the earlier one at the identical target. Across eight held-out target pairs, the table reports the median and maximum **absolute** difference; live sessions have prediction differences only, because their JSONs do not retain held-out features. Other sessions' output differences are the exact linear mapping of recorded presentation-level feature medians. The report command also emits every target's signed difference separately.

| Session | Repeat phase / target pairs | Median abs feature Δ | Max abs feature Δ | Median abs predicted-y Δ | Max abs predicted-y Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
| live-1 | held-out / 8 | unavailable | unavailable | 0.13574 | 0.42435 |
| live-2 | held-out / 8 | unavailable | unavailable | 0.03940 | 0.09149 |
| collapse A | held-out / 8 | 0.002296 | 0.009953 | 0.09950 | 0.43137 |
| collapse B | held-out / 8 | 0.001495 | 0.003591 | 0.06552 | 0.15739 |
| drift A | held-out / 8 | 0.001697 | 0.003039 | 0.04854 | 0.08693 |
| drift B | held-out / 8 | 0.001413 | 0.007184 | 0.04521 | 0.22983 |
| controlled-1 | diagnostic grid / 9 | 0.003273 | 0.009750 | 0.07428 | 0.22126 |

For the Issue #46 five-CENTER series, checkpoint 4 minus checkpoint 0 was **−0.004771 feature / −0.13649 mapped y** in drift A and **−0.002102 / −0.06726** in drift B. These are first-to-last changes, not held-out errors or evidence of monotonic drift. The controlled-1 run has no held-out metric; its repeated grid observations are diagnostic presentations.

## Bounded interpretation

**In the two fresh live sessions, the high-slope run did have a compressed calibration feature range.** live-1's slope was about 3.09 times live-2's (61.96 versus 20.07), while its full nine-target feature span was about 3.85 times narrower (0.00875 versus 0.03368). Its top-to-center row-median separation was particularly weak (0.00095 versus 0.01720), and its calibration y MAE/ordering were worse (0.13457 and 22/27 versus 0.09637 and 25/27). Yet live-2's **center-to-bottom** separation was smaller than live-1's (0.00321 versus 0.00498). Thus the data support a narrower *overall* span and weaker *top-to-center* separation in live-1, not a claim that every row separation was worse. The other five same-participant sessions provide context with slopes ~22.69–43.83 and differing feature spans/fit behavior; they do not turn this into a statistical relationship.

The distinction is essential: **feature instability** is the feature itself changing at an identical target; **mapping sensitivity** is the fitted slope converting that change into a larger or smaller output change. The identity `Δpredicted_y = y_slope × Δvertical_feature` accounts exactly for recorded same-target changes under the independent-linear model. For example, controlled-1's median absolute repeat feature change of 0.003273 maps to 0.07428 y at its slope of 22.69. At live-1's slope, a *hypothetical* 0.003 change would map to 0.18589 y, versus 0.06022 at live-2's slope. This does not mean the same feature change actually occurred in both live sessions; their held-out feature medians were not saved.

This diagnostic supports mapping sensitivity and calibration geometry as **useful measurements for a later controlled live study**, with per-frame features retained and repeated identical targets after calibration. It does **not** prove that feature-range compression caused the large slope, that the slope caused feature movement, or that one physical mechanism explains the sessions. Calibration is row-major, so X position and presentation order remain entangled; the existing sessions differ in repeat/checkpoint protocol. There is one participant, no independent cross-user evidence, and no cursor-targeting usability test. Head pose, eyelids, glasses, elapsed time, gaze history, camera geometry, and physiology were not isolated as causes. No production correction or mapping change follows from these results.
