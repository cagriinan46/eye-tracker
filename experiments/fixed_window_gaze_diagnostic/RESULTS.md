# Fixed-window gaze diagnostic — results

Analysis finalized 2026-10-06. **Outcome C: feature representation and mapping are both implicated.** The raw features retain ordered gaze signal over these short windows, but same-target transfer/block changes are substantial relative to vertical separation. The current independent-linear mapping also leaves substantial residuals on the calibration medians themselves. Prioritize representation/normalization measurement and redesign before adding more complex static mappings. This is a single-participant engineering diagnosis, not a physical-cause identification.

## 1. Question, protocol, and valid captures

Does failure arise from unstable/non-transferable production features, inadequate calibration mapping, or both? Only the two completed `fixed_window_gaze_diagnostic`, version 1 captures below are used. Neither earlier targeting captures nor eye-opening/geometry studies enter these statistics.

Both pass `validate_capture`: participant `cagri`, READY used, seed `20261006`, camera index 1, 1920×1080, 1200×700 displayed coordinate area; 9 standard calibration presentations (0.8 s settle + 1.2 s sample), all 9 targets once in each of three validation blocks, 27 fixed target windows. Cue = 0.75 s, nominal target = 3.0 s, neutral transition = 0.5 s. Saved mapping coefficients reproduce calibration-only fitting and all raw mapped samples. No acquisition grading, gaze cursor, early success stops, smoothing, or clipping.

| Session | Elapsed s | Calibration usable | Validation usable/attempts | Camera reads | Failed reads | No-face | Actual target display s (min–max) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | 134.912874 | 298 | 2261/2261 | 3816 | 0 | 1 | 3.015341–3.026500 |
| diagnostic-2 | 134.920455 | 297 | 2265/2265 | 3816 | 0 | 1 | 3.015850–3.026989 |

Each calibration target has at least 33 usable samples (above the established five-sample requirement). Validation presentations contain 83–84 samples; all 4,526 are usable (100%, zero unavailable target samples). Each session has **one no-face observation** in the whole-run counter, not zero; no unavailable observations occur in the logged calibration/validation sampling windows. Counters also cover settling/cues/transitions, so the exact off-window occurrence is not identified. Display scheduling overruns of roughly 15–27 ms were logged as designed; analysis uses observations completed inside the nominal [0,3) s window and retains every eligible sample. No capture is excluded for its error.

Input provenance (local ignored files; numerical data remain untracked):

- `.venv/fixed-window-gaze-cagri-diagnostic-1.json` — SHA-256 `f645485fb723d8f406d6a044d217fa4c320499107aa0fe5393124b34a6a731a8`
- `.venv/fixed-window-gaze-cagri-diagnostic-2.json` — SHA-256 `c5bf81a34012b0824d4526cfdd4f282c1fb78bdcdd013f4be600f3e1152d243f`

## 2. Reproducible analysis and weighting

All values are recomputed from raw samples, not saved summaries or preliminary chat observations. Tables round derived values to six decimal places; coefficients use nine. h/v refer to the unchanged production binocular horizontal/vertical features.

Screen MAE/bias/Euclidean statistics use every usable sample in the full window and are sample-weighted, including pooled session/row/column/target/block summaries. Euclidean error = sqrt(dx²+dy²). Feature-level medians give each presentation equal weight; same-target validation reference = median of its three block medians. Calibration residuals below use exactly nine presentation medians, equally weighted, not calibration-frame error. MAD = median absolute deviation; IQR = interpolated p75−p25. No diagnostic label enters calibration or fits any correction.

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.fixed_window_gaze_diagnostic.analysis --finalize .venv/fixed-window-gaze-cagri-diagnostic-1.json .venv/fixed-window-gaze-cagri-diagnostic-2.json --output .venv/fixed-window-final-analysis-20261006.json
```

The output path must not already exist. The deterministic output contains all trial summaries, distributions, conditional ordering, transfers, ranges, half-window medians, calibration-median residuals, and pooled position groups. Raw feature scales remain session-local.

## 3. Production validation screen-space error

| Session | N | x MAE | y MAE | x bias | y bias | Mean Euclidean | p95 Euclidean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | 2261 | 0.050517 | 0.128078 | -0.014232 | -0.029526 | 0.148261 | 0.413258 |
| diagnostic-2 | 2265 | 0.072408 | 0.144663 | -0.051007 | 0.052690 | 0.175635 | 0.514263 |
| pooled | 4526 | 0.061472 | 0.136378 | -0.032636 | 0.011619 | 0.161960 | 0.482686 |

| Session | Median Euclidean | Median \|x error\| | Median \|y error\| |
| --- | --- | --- | --- |
| diagnostic-1 | 0.109363 | 0.023013 | 0.104430 |
| diagnostic-2 | 0.123685 | 0.057270 | 0.100492 |
| pooled | 0.116889 | 0.035359 | 0.102496 |

Vertical MAE exceeds horizontal MAE in both sessions. Opposite session y biases partly cancel when pooled; the small pooled signed bias must not be mistaken for accurate y prediction. These are measurement residuals, not success rates for any dwell/target geometry.

## 4. Row, column, target, and block residuals

### Screen row y

| Session / level | N | x MAE | y MAE | x bias | y bias | Mean Euclidean | p95 Euclidean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 / 0.2 | 753 | 0.056352 | 0.147878 | -0.011905 | 0.087244 | 0.168092 | 0.481060 |
| diagnostic-1 / 0.5 | 755 | 0.054455 | 0.085800 | -0.023678 | -0.025165 | 0.113620 | 0.204641 |
| diagnostic-1 / 0.8 | 753 | 0.040734 | 0.150668 | -0.007089 | -0.150668 | 0.163164 | 0.422538 |
| diagnostic-2 / 0.2 | 754 | 0.067156 | 0.189113 | -0.043631 | 0.124315 | 0.209623 | 0.526706 |
| diagnostic-2 / 0.5 | 755 | 0.069292 | 0.123234 | -0.043935 | 0.039371 | 0.156212 | 0.333188 |
| diagnostic-2 / 0.8 | 756 | 0.080758 | 0.121731 | -0.065425 | -0.005443 | 0.161135 | 0.679401 |
| pooled / 0.2 | 1507 | 0.061758 | 0.168509 | -0.027778 | 0.105792 | 0.188871 | 0.526515 |
| pooled / 0.5 | 1510 | 0.061873 | 0.104517 | -0.033806 | 0.007103 | 0.134916 | 0.330234 |
| pooled / 0.8 | 1509 | 0.060786 | 0.136171 | -0.036315 | -0.077911 | 0.162147 | 0.638424 |

### Screen column x

| Session / level | N | x MAE | y MAE | x bias | y bias | Mean Euclidean | p95 Euclidean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 / 0.2 | 753 | 0.062969 | 0.143738 | 0.006273 | 0.059224 | 0.167834 | 0.560614 |
| diagnostic-1 / 0.5 | 753 | 0.024029 | 0.106934 | -0.019284 | -0.083377 | 0.114622 | 0.372607 |
| diagnostic-1 / 0.8 | 755 | 0.064516 | 0.133547 | -0.029645 | -0.064332 | 0.162290 | 0.629137 |
| diagnostic-2 / 0.2 | 754 | 0.076143 | 0.214204 | -0.027250 | 0.185595 | 0.236633 | 0.521325 |
| diagnostic-2 / 0.5 | 755 | 0.067286 | 0.090862 | -0.058978 | 0.002180 | 0.124855 | 0.322939 |
| diagnostic-2 / 0.8 | 756 | 0.073799 | 0.129035 | -0.066739 | -0.029419 | 0.165511 | 0.681361 |
| pooled / 0.2 | 1507 | 0.069560 | 0.178994 | -0.010500 | 0.122452 | 0.202256 | 0.522927 |
| pooled / 0.5 | 1508 | 0.045686 | 0.098887 | -0.039157 | -0.040542 | 0.119746 | 0.369087 |
| pooled / 0.8 | 1511 | 0.069161 | 0.131290 | -0.048204 | -0.046864 | 0.163902 | 0.658384 |

### Validation block

| Session / level | N | x MAE | y MAE | x bias | y bias | Mean Euclidean | p95 Euclidean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 / 1 | 755 | 0.052386 | 0.124701 | -0.028413 | -0.023162 | 0.146640 | 0.614824 |
| diagnostic-1 / 2 | 754 | 0.045392 | 0.128936 | -0.011357 | -0.016612 | 0.145006 | 0.404420 |
| diagnostic-1 / 3 | 752 | 0.053779 | 0.130608 | -0.002878 | -0.048864 | 0.153153 | 0.369643 |
| diagnostic-2 / 1 | 755 | 0.056792 | 0.148497 | -0.033948 | 0.082318 | 0.169101 | 0.523470 |
| diagnostic-2 / 2 | 755 | 0.100594 | 0.145304 | -0.082017 | 0.072992 | 0.192538 | 0.476597 |
| diagnostic-2 / 3 | 755 | 0.059838 | 0.140188 | -0.037055 | 0.002761 | 0.165266 | 0.565548 |
| pooled / 1 | 1510 | 0.054589 | 0.136599 | -0.031180 | 0.029578 | 0.157871 | 0.524064 |
| pooled / 2 | 1509 | 0.073012 | 0.137125 | -0.046710 | 0.028220 | 0.168788 | 0.458985 |
| pooled / 3 | 1507 | 0.056815 | 0.135407 | -0.020001 | -0.023000 | 0.159222 | 0.472291 |

### Individual targets

| Session / target | N | x MAE | y MAE | x bias | y bias | Mean Euclidean | p95 Euclidean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 / T-1-1 | 251 | 0.088920 | 0.218414 | -0.001439 | 0.218414 | 0.248042 | 0.665424 |
| diagnostic-1 / T-1-2 | 250 | 0.008784 | 0.098242 | -0.007595 | -0.027288 | 0.099607 | 0.455114 |
| diagnostic-1 / T-1-3 | 252 | 0.071105 | 0.126863 | -0.026605 | 0.070218 | 0.156399 | 0.813141 |
| diagnostic-1 / T-2-1 | 251 | 0.045208 | 0.087286 | -0.011775 | 0.084771 | 0.109805 | 0.147878 |
| diagnostic-1 / T-2-2 | 252 | 0.046287 | 0.081352 | -0.034304 | -0.081352 | 0.100639 | 0.369643 |
| diagnostic-1 / T-2-3 | 252 | 0.071832 | 0.088768 | -0.024907 | -0.078479 | 0.130401 | 0.603524 |
| diagnostic-1 / T-3-1 | 251 | 0.054779 | 0.125513 | 0.032033 | -0.125513 | 0.145655 | 0.775597 |
| diagnostic-1 / T-3-2 | 251 | 0.016868 | 0.141275 | -0.015845 | -0.141275 | 0.143616 | 0.242430 |
| diagnostic-1 / T-3-3 | 251 | 0.050555 | 0.185216 | -0.037455 | -0.185216 | 0.200220 | 0.317759 |
| diagnostic-2 / T-1-1 | 250 | 0.102077 | 0.346378 | -0.035928 | 0.346378 | 0.367225 | 0.701034 |
| diagnostic-2 / T-1-2 | 252 | 0.036419 | 0.071559 | -0.036419 | -0.007606 | 0.089301 | 0.272015 |
| diagnostic-2 / T-1-3 | 252 | 0.063251 | 0.150649 | -0.058484 | 0.035936 | 0.173594 | 0.846359 |
| diagnostic-2 / T-2-1 | 252 | 0.063029 | 0.192513 | -0.024187 | 0.189798 | 0.216031 | 0.344779 |
| diagnostic-2 / T-2-2 | 251 | 0.087039 | 0.075413 | -0.062946 | 0.003431 | 0.119904 | 0.231401 |
| diagnostic-2 / T-2-3 | 252 | 0.057879 | 0.101588 | -0.044748 | -0.075259 | 0.132556 | 0.263957 |
| diagnostic-2 / T-3-1 | 252 | 0.063529 | 0.104772 | -0.021705 | 0.021886 | 0.127679 | 0.202366 |
| diagnostic-2 / T-3-2 | 252 | 0.078477 | 0.125553 | -0.077585 | 0.010719 | 0.165341 | 0.405917 |
| diagnostic-2 / T-3-3 | 252 | 0.100269 | 0.134868 | -0.096985 | -0.048933 | 0.190384 | 0.733191 |
| pooled / T-1-1 | 501 | 0.095485 | 0.282268 | -0.018649 | 0.282268 | 0.307515 | 0.666495 |
| pooled / T-1-2 | 502 | 0.022657 | 0.084847 | -0.022065 | -0.017408 | 0.094434 | 0.454327 |
| pooled / T-1-3 | 504 | 0.067178 | 0.138756 | -0.042544 | 0.053077 | 0.164997 | 0.821318 |
| pooled / T-2-1 | 503 | 0.054136 | 0.140004 | -0.017993 | 0.137389 | 0.163024 | 0.330672 |
| pooled / T-2-2 | 503 | 0.066622 | 0.078388 | -0.048597 | -0.039045 | 0.110252 | 0.297258 |
| pooled / T-2-3 | 504 | 0.064855 | 0.095178 | -0.034827 | -0.076869 | 0.131478 | 0.440959 |
| pooled / T-3-1 | 503 | 0.059163 | 0.115122 | 0.005111 | -0.051667 | 0.136649 | 0.411620 |
| pooled / T-3-2 | 503 | 0.047734 | 0.133398 | -0.046776 | -0.065127 | 0.154500 | 0.365798 |
| pooled / T-3-3 | 503 | 0.075462 | 0.159992 | -0.067279 | -0.116939 | 0.195292 | 0.724295 |

T-r-c denotes row r and column c at levels 0.2/0.5/0.8. T-1-1 is the largest y-MAE target in both sessions. The left column has positive y bias in both, while center/right columns differ; this is not one universal y offset. T-3-3 has substantial negative calibration residual in both sessions and validation y bias of −0.185216/−0.048933. T-1-3 and T-3-3 have large tail Euclidean errors; tails include the cue-to-target movement in the full primary window.

## 5. Feature separation and ordering

Calibration infers **h decreasing left→right**, **v increasing upper→lower** in both sessions. Full-window row/column medians and signed adjacent separations:

| Session | Axis | Phase/block | Level .2 median | Level .5 median | Level .8 median | Δ .2→.5 | Δ .5→.8 | Ordered |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | horizontal | calibration | 0.532266 | 0.485783 | 0.438730 | -0.046483 | -0.047053 | yes |
| diagnostic-1 | horizontal | 1 | 0.538998 | 0.487668 | 0.442250 | -0.051330 | -0.045418 | yes |
| diagnostic-1 | horizontal | 2 | 0.536422 | 0.487961 | 0.436527 | -0.048461 | -0.051434 | yes |
| diagnostic-1 | horizontal | 3 | 0.538724 | 0.487637 | 0.433746 | -0.051087 | -0.053891 | yes |
| diagnostic-1 | horizontal | pooled | 0.538270 | 0.487668 | 0.437547 | -0.050602 | -0.050120 | yes |
| diagnostic-1 | vertical | calibration | -0.062052 | -0.043562 | -0.035244 | 0.018491 | 0.008317 | yes |
| diagnostic-1 | vertical | 1 | -0.054299 | -0.048806 | -0.037979 | 0.005493 | 0.010827 | yes |
| diagnostic-1 | vertical | 2 | -0.057930 | -0.050749 | -0.037619 | 0.007182 | 0.013130 | yes |
| diagnostic-1 | vertical | 3 | -0.062925 | -0.049569 | -0.040080 | 0.013356 | 0.009490 | yes |
| diagnostic-1 | vertical | pooled | -0.057930 | -0.049569 | -0.039443 | 0.008361 | 0.010127 | yes |
| diagnostic-2 | horizontal | calibration | 0.532366 | 0.485943 | 0.425987 | -0.046423 | -0.059957 | yes |
| diagnostic-2 | horizontal | 1 | 0.541589 | 0.491003 | 0.433357 | -0.050586 | -0.057645 | yes |
| diagnostic-2 | horizontal | 2 | 0.549705 | 0.498897 | 0.442788 | -0.050808 | -0.056109 | yes |
| diagnostic-2 | horizontal | 3 | 0.539512 | 0.492963 | 0.429500 | -0.046549 | -0.063463 | yes |
| diagnostic-2 | horizontal | pooled | 0.546892 | 0.492915 | 0.433357 | -0.053977 | -0.059558 | yes |
| diagnostic-2 | vertical | calibration | -0.061287 | -0.048329 | -0.039906 | 0.012958 | 0.008423 | yes |
| diagnostic-2 | vertical | 1 | -0.060580 | -0.050960 | -0.036304 | 0.009619 | 0.014657 | yes |
| diagnostic-2 | vertical | 2 | -0.059138 | -0.047266 | -0.037901 | 0.011872 | 0.009365 | yes |
| diagnostic-2 | vertical | 3 | -0.063541 | -0.053888 | -0.042314 | 0.009654 | 0.011573 | yes |
| diagnostic-2 | vertical | pooled | -0.060580 | -0.050960 | -0.038849 | 0.009619 | 0.012111 | yes |

Both axes order correctly in all 6/6 validation blocks and both pooled-session summaries. To avoid hiding cross-position failure in pooled row medians, vertical ordering is also checked separately at each x, and horizontal ordering at each y:

| Session | Axis | Fixed axis | Level | B1 ordered | B2 ordered | B3 ordered | Pooled .2 | .5 | .8 | Smallest block adjacency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | vertical | x | 0.2 | yes | yes | yes | -0.048834 | -0.043500 | -0.036600 | 0.003262 |
| diagnostic-1 | vertical | x | 0.5 | yes | yes | yes | -0.063943 | -0.050313 | -0.037979 | 0.009490 |
| diagnostic-1 | vertical | x | 0.8 | yes | yes | yes | -0.057930 | -0.050749 | -0.040606 | 0.004713 |
| diagnostic-1 | horizontal | y | 0.2 | yes | yes | yes | 0.541363 | 0.487637 | 0.436527 | 0.045176 |
| diagnostic-1 | horizontal | y | 0.5 | yes | yes | yes | 0.538724 | 0.489188 | 0.434728 | 0.044341 |
| diagnostic-1 | horizontal | y | 0.8 | yes | yes | yes | 0.532580 | 0.487668 | 0.442250 | 0.038856 |
| diagnostic-2 | vertical | x | 0.2 | yes | yes | yes | -0.047204 | -0.044833 | -0.036304 | 0.002371 |
| diagnostic-2 | vertical | x | 0.5 | yes | yes | yes | -0.064370 | -0.052820 | -0.037901 | 0.009365 |
| diagnostic-2 | vertical | x | 0.8 | yes | yes | yes | -0.060580 | -0.055448 | -0.042606 | 0.000812 |
| diagnostic-2 | horizontal | y | 0.2 | yes | yes | yes | 0.547271 | 0.489278 | 0.431972 | 0.049430 |
| diagnostic-2 | horizontal | y | 0.5 | yes | yes | yes | 0.541589 | 0.492963 | 0.433357 | 0.045429 |
| diagnostic-2 | horizontal | y | 0.8 | yes | yes | yes | 0.539512 | 0.497371 | 0.440812 | 0.042142 |

Vertical ordering holds in 18/18 block×column checks; horizontal ordering in 18/18 block×row checks. Correct order does not mean strong margins everywhere: diagnostic-2, block 2, right-column upper/center separation is only **0.000812** (features −0.059138/−0.058326). Spatial aggregation can conceal this compressed local margin.

## 6. Within-target variability relative to separation

| Session | Axis | Median trial MAD | Median trial IQR | Min calibration adjacency | Min pooled-validation adjacency | Median IQR/separation | p95 IQR/separation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | horizontal | 0.000968 | 0.001972 | 0.046483 | 0.050120 | 0.039343 | 0.119620 |
| diagnostic-1 | vertical | 0.000666 | 0.001307 | 0.008317 | 0.008361 | 0.156308 | 0.543579 |
| diagnostic-2 | horizontal | 0.001390 | 0.002575 | 0.046423 | 0.053977 | 0.047709 | 0.129828 |
| diagnostic-2 | vertical | 0.001068 | 0.002380 | 0.008423 | 0.009619 | 0.247467 | 0.702858 |

The ratio denominator is the smaller absolute adjacent-level separation of the session-pooled presentation medians, not a clinical threshold or each column’s smallest margin. Typical within-window feature IQR is below that separation, especially horizontally, but vertical IQR reaches larger fractions. Raw per-level distributions/quantiles and each presentation’s spread remain in the analysis output; order alone does not establish distribution non-overlap.

Pooled raw-sample IQR intervals by level (sample-weighted; not presentation-median separation):

| Session | Axis | Level .2 IQR interval | Level .5 IQR interval | Level .8 IQR interval |
| --- | --- | --- | --- | --- |
| diagnostic-1 | horizontal | [0.533195, 0.539825] | [0.486609, 0.489101] | [0.434936, 0.443799] |
| diagnostic-1 | vertical | [-0.063660, -0.052896] | [-0.051476, -0.044141] | [-0.041123, -0.037071] |
| diagnostic-2 | horizontal | [0.538229, 0.549401] | [0.489149, 0.497273] | [0.430069, 0.442672] |
| diagnostic-2 | vertical | [-0.064964, -0.052831] | [-0.054598, -0.045634] | [-0.042564, -0.036287] |

Diagnostic-2 upper/center vertical IQR intervals overlap; all adjacent vertical p05–p95 intervals overlap in both sessions. This includes within-target, cross-column, block, and initial-transition variability. It demonstrates that ordered aggregate medians do not guarantee per-sample separability, without attributing all overlap to a single mechanism.

## 7. Exact-target calibration-to-validation transfer

For each target, calibration median versus median of its three validation block medians. Both signed and absolute shifts are explicit; ratios use the same session-pooled validation separation defined above. Ratios against calibration separation are also retained by the analyzer.

| Session | Target | Cal h | Val h | Δh | \|Δh\| | \|Δh\|/sep | Cal v | Val v | Δv | \|Δv\| | \|Δv\|/sep |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | T-1-1 | 0.532729 | 0.541363 | 0.008633 | 0.008633 | 0.172252 | -0.057932 | -0.048834 | 0.009098 | 0.009098 | 1.088164 |
| diagnostic-1 | T-1-2 | 0.488637 | 0.487637 | -0.001000 | 0.001000 | 0.019954 | -0.062931 | -0.063943 | -0.001012 | 0.001012 | 0.121081 |
| diagnostic-1 | T-1-3 | 0.438730 | 0.436527 | -0.002203 | 0.002203 | 0.043960 | -0.062052 | -0.057930 | 0.004122 | 0.004122 | 0.493004 |
| diagnostic-1 | T-2-1 | 0.532266 | 0.538724 | 0.006458 | 0.006458 | 0.128852 | -0.040356 | -0.043500 | -0.003144 | 0.003144 | 0.376040 |
| diagnostic-1 | T-2-2 | 0.485783 | 0.489188 | 0.003404 | 0.003404 | 0.067926 | -0.043562 | -0.050313 | -0.006752 | 0.006752 | 0.807507 |
| diagnostic-1 | T-2-3 | 0.437179 | 0.434728 | -0.002450 | 0.002450 | 0.048891 | -0.047283 | -0.050749 | -0.003466 | 0.003466 | 0.414541 |
| diagnostic-1 | T-3-1 | 0.531854 | 0.532580 | 0.000726 | 0.000726 | 0.014483 | -0.032836 | -0.036600 | -0.003765 | 0.003765 | 0.450272 |
| diagnostic-1 | T-3-2 | 0.484098 | 0.487668 | 0.003570 | 0.003570 | 0.071230 | -0.035244 | -0.037979 | -0.002734 | 0.002734 | 0.327038 |
| diagnostic-1 | T-3-3 | 0.444584 | 0.442250 | -0.002335 | 0.002335 | 0.046581 | -0.040857 | -0.040606 | 0.000251 | 0.000251 | 0.029974 |
| diagnostic-2 | T-1-1 | 0.536272 | 0.547271 | 0.010998 | 0.010998 | 0.203757 | -0.059212 | -0.047204 | 0.012008 | 0.012008 | 1.248324 |
| diagnostic-2 | T-1-2 | 0.485943 | 0.489278 | 0.003335 | 0.003335 | 0.061779 | -0.061287 | -0.064370 | -0.003084 | 0.003084 | 0.320575 |
| diagnostic-2 | T-1-3 | 0.425987 | 0.431972 | 0.005985 | 0.005985 | 0.110882 | -0.063822 | -0.060580 | 0.003242 | 0.003242 | 0.337033 |
| diagnostic-2 | T-2-1 | 0.532366 | 0.541589 | 0.009223 | 0.009223 | 0.170863 | -0.048329 | -0.044833 | 0.003496 | 0.003496 | 0.363388 |
| diagnostic-2 | T-2-2 | 0.481386 | 0.492963 | 0.011577 | 0.011577 | 0.214482 | -0.048218 | -0.052820 | -0.004602 | 0.004602 | 0.478405 |
| diagnostic-2 | T-2-3 | 0.424238 | 0.433357 | 0.009120 | 0.009120 | 0.168955 | -0.057022 | -0.055448 | 0.001574 | 0.001574 | 0.163632 |
| diagnostic-2 | T-3-1 | 0.530314 | 0.539512 | 0.009198 | 0.009198 | 0.170408 | -0.038126 | -0.036304 | 0.001823 | 0.001823 | 0.189492 |
| diagnostic-2 | T-3-2 | 0.488223 | 0.497371 | 0.009148 | 0.009148 | 0.169477 | -0.039906 | -0.037901 | 0.002005 | 0.002005 | 0.208384 |
| diagnostic-2 | T-3-3 | 0.436911 | 0.440812 | 0.003901 | 0.003901 | 0.072267 | -0.046985 | -0.042606 | 0.004379 | 0.004379 | 0.455231 |

| Session | Axis | Median \|shift\| | Maximum \|shift\| | Median / val sep | Maximum / val sep | Median / cal sep | Maximum / cal sep |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | horizontal | 0.002450 | 0.008633 | 0.048891 | 0.172252 | 0.052717 | 0.185731 |
| diagnostic-1 | vertical | 0.003466 | 0.009098 | 0.414541 | 1.088164 | 0.416726 | 1.093898 |
| diagnostic-2 | horizontal | 0.009148 | 0.011577 | 0.169477 | 0.214482 | 0.197055 | 0.249383 |
| diagnostic-2 | vertical | 0.003242 | 0.012008 | 0.337033 | 1.248324 | 0.384917 | 1.425680 |

Median vertical transfer is **0.003466/0.003242**, or **41.454094%/33.703266%** of the smaller pooled-validation row separation. Maximum shift exceeds that separation in both sessions, at T-1-1. Diagnostic-2 horizontal shifts are positive for all nine targets (not just y instability). These changes occur before any mapping is applied: no static calibration map can make a changed same-target input invariant by itself.

## 8. Block repeatability and drift

Every target retains all three blocks. Range = max(block medians)−min(block medians). A directional flag means both adjacent changes have the same strict sign; it does not establish a cause or trend beyond three observations.

| Session | Target | h B1 | h B2 | h B3 | h range | h B3−B1 | v B1 | v B2 | v B3 | v range | v B3−B1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | T-1-1 | 0.541600 | 0.538270 | 0.541363 | 0.003330 | -0.000237 | -0.054299 | -0.048465 | -0.048834 | 0.005834 | 0.005466 |
| diagnostic-1 | T-1-2 | 0.486167 | 0.487961 | 0.487637 | 0.001793 | 0.001470 | -0.064816 | -0.063943 | -0.062925 | 0.001891 | 0.001891 |
| diagnostic-1 | T-1-3 | 0.440991 | 0.436527 | 0.433746 | 0.007245 | -0.007245 | -0.053518 | -0.057930 | -0.063389 | 0.009871 | -0.009871 |
| diagnostic-1 | T-2-1 | 0.538998 | 0.533528 | 0.538724 | 0.005469 | -0.000273 | -0.043500 | -0.040755 | -0.044641 | 0.003886 | -0.001141 |
| diagnostic-1 | T-2-2 | 0.493596 | 0.489188 | 0.485645 | 0.007950 | -0.007950 | -0.050313 | -0.051798 | -0.049569 | 0.002228 | 0.000744 |
| diagnostic-1 | T-2-3 | 0.444828 | 0.434728 | 0.433135 | 0.011693 | -0.011693 | -0.048806 | -0.050749 | -0.053903 | 0.005097 | -0.005097 |
| diagnostic-1 | T-3-1 | 0.532058 | 0.536422 | 0.532580 | 0.004364 | 0.000522 | -0.034855 | -0.036600 | -0.041379 | 0.006524 | -0.006524 |
| diagnostic-1 | T-3-2 | 0.487668 | 0.487332 | 0.489366 | 0.002034 | 0.001698 | -0.037979 | -0.037619 | -0.040080 | 0.002461 | -0.002101 |
| diagnostic-1 | T-3-3 | 0.442250 | 0.448476 | 0.437547 | 0.010928 | -0.004702 | -0.043153 | -0.040606 | -0.039443 | 0.003710 | 0.003710 |
| diagnostic-2 | T-1-1 | 0.547271 | 0.549705 | 0.546892 | 0.002813 | -0.000378 | -0.045215 | -0.047204 | -0.054244 | 0.009029 | -0.009029 |
| diagnostic-2 | T-1-2 | 0.484198 | 0.492218 | 0.489278 | 0.008020 | 0.005080 | -0.064370 | -0.065036 | -0.063541 | 0.001495 | 0.000829 |
| diagnostic-2 | T-1-3 | 0.431972 | 0.442788 | 0.429500 | 0.013288 | -0.002472 | -0.060580 | -0.059138 | -0.068152 | 0.009014 | -0.007573 |
| diagnostic-2 | T-2-1 | 0.541589 | 0.548271 | 0.538392 | 0.009879 | -0.003197 | -0.041058 | -0.044833 | -0.045642 | 0.004585 | -0.004585 |
| diagnostic-2 | T-2-2 | 0.492915 | 0.498897 | 0.492963 | 0.005982 | 0.000048 | -0.052820 | -0.047266 | -0.053888 | 0.006622 | -0.001068 |
| diagnostic-2 | T-2-3 | 0.433357 | 0.436056 | 0.426613 | 0.009442 | -0.006744 | -0.050960 | -0.058326 | -0.055448 | 0.007366 | -0.004488 |
| diagnostic-2 | T-3-1 | 0.537932 | 0.550853 | 0.539512 | 0.012920 | 0.001580 | -0.036304 | -0.035680 | -0.042314 | 0.006634 | -0.006011 |
| diagnostic-2 | T-3-2 | 0.491003 | 0.500654 | 0.497371 | 0.009651 | 0.006368 | -0.033939 | -0.037901 | -0.041367 | 0.007428 | -0.007428 |
| diagnostic-2 | T-3-3 | 0.440812 | 0.447649 | 0.431155 | 0.016494 | -0.009657 | -0.042606 | -0.038849 | -0.046109 | 0.007260 | -0.003503 |

| Session | Axis | Median target range | Maximum target range | Median mapped range | Maximum mapped range | Strict directional targets /9 |
| --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | horizontal | 0.005469 | 0.011693 | 0.035506 | 0.075913 | 3 |
| diagnostic-1 | vertical | 0.003886 | 0.009871 | 0.083541 | 0.212182 | 5 |
| diagnostic-2 | horizontal | 0.009651 | 0.016494 | 0.055130 | 0.094215 | 0 |
| diagnostic-2 | vertical | 0.007260 | 0.009029 | 0.186654 | 0.232114 | 3 |

The vertical range reaches **0.009871** (diagnostic-1, T-1-3) and **0.009029** (diagnostic-2, T-1-1). Median vertical block range is **0.003886/0.007260**; much larger than median within-window MAD. Motion is mixed across targets: strict directional drift occurs for v at 5/9 and 3/9 targets, h at 3/9 and 0/9. Do not label this one global monotonic time drift. Screen-space block changes follow the unchanged mapping slopes; they are not fitted corrections.

## 9. Temporal stability and persistence after gaze transition

Primary halves are [0,1.5) and [1.5,3) s. Compare their raw medians for every window (Appendix A). Initial cue-to-target gaze movement can contribute to their difference; it is not automatically feature instability. Separately recompute calibration transfer from the second-half median of each presentation, then median across its three blocks.

| Session | Axis | Median \|half shift\| | Max \|half shift\| | Full-window median \|transfer\| | Second-half median \|transfer\| | Second-half max \|transfer\| |
| --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | horizontal | 0.001447 | 0.006092 | 0.002450 | 0.002227 | 0.008989 |
| diagnostic-1 | vertical | 0.000755 | 0.009385 | 0.003466 | 0.003504 | 0.009512 |
| diagnostic-2 | horizontal | 0.001912 | 0.012466 | 0.009148 | 0.008556 | 0.013684 |
| diagnostic-2 | vertical | 0.001565 | 0.008376 | 0.003242 | 0.003687 | 0.012607 |

Vertical transfer does **not disappear**: median absolute second-half transfer is **0.003504/0.003687**, compared with full-window **0.003466/0.003242**. T-1-1 remains shifted by **+0.009512/+0.012607** in the second half. This excludes an explanation based only on the initial transition, without proving what caused the later feature value.

The preregistered secondary [0.8,3) s analysis also reduces transition-contaminated screen errors but leaves appreciable residuals:

| Session | Secondary N | x MAE | y MAE | y bias | Mean Euclidean | p95 Euclidean |
| --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | 1680 | 0.026209 | 0.112723 | -0.027415 | 0.118069 | 0.240293 |
| diagnostic-2 | 1679 | 0.052511 | 0.131555 | 0.064902 | 0.150471 | 0.432736 |

## 10. Calibration mapping fit on the nine medians

Production coefficients (fresh session calibration only):

| Session | x slope | x intercept | y slope | y intercept | Calibration-median x MAE | Calibration-median y MAE |
| --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | -6.492183252 | 3.656543548 | 21.495473016 | 1.510410358 | 0.010576 | 0.063713 |
| diagnostic-2 | -5.712101899 | 3.255543861 | 25.708532588 | 1.822293147 | 0.022508 | 0.078086 |

| Session | Calibration target | h median | v median | Fitted x | Fitted y | Signed x residual | Signed y residual | \|x residual\| | \|y residual\| |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | C-1-1 | 0.532729 | -0.057932 | 0.197966 | 0.265143 | -0.002034 | 0.065143 | 0.002034 | 0.065143 |
| diagnostic-1 | C-1-2 | 0.488637 | -0.062931 | 0.484220 | 0.157688 | -0.015780 | -0.042312 | 0.015780 | 0.042312 |
| diagnostic-1 | C-1-3 | 0.438730 | -0.062052 | 0.808229 | 0.176565 | 0.008229 | -0.023435 | 0.008229 | 0.023435 |
| diagnostic-1 | C-2-1 | 0.532266 | -0.040356 | 0.200974 | 0.642940 | 0.000974 | 0.142940 | 0.000974 | 0.142940 |
| diagnostic-1 | C-2-2 | 0.485783 | -0.043562 | 0.502750 | 0.574034 | 0.002750 | 0.074034 | 0.002750 | 0.074034 |
| diagnostic-1 | C-2-3 | 0.437179 | -0.047283 | 0.818299 | 0.494045 | 0.018299 | -0.005955 | 0.018299 | 0.005955 |
| diagnostic-1 | C-3-1 | 0.531854 | -0.032836 | 0.203649 | 0.804593 | 0.003649 | 0.004593 | 0.003649 | 0.004593 |
| diagnostic-1 | C-3-2 | 0.484098 | -0.035244 | 0.513693 | 0.752815 | 0.013693 | -0.047185 | 0.013693 | 0.047185 |
| diagnostic-1 | C-3-3 | 0.444584 | -0.040857 | 0.770220 | 0.632176 | -0.029780 | -0.167824 | 0.029780 | 0.167824 |
| diagnostic-2 | C-1-1 | 0.536272 | -0.059212 | 0.192302 | 0.300048 | -0.007698 | 0.100048 | 0.007698 | 0.100048 |
| diagnostic-2 | C-1-2 | 0.485943 | -0.061287 | 0.479786 | 0.246706 | -0.020214 | 0.046706 | 0.020214 | 0.046706 |
| diagnostic-2 | C-1-3 | 0.425987 | -0.063822 | 0.822263 | 0.181533 | 0.022263 | -0.018467 | 0.022263 | 0.018467 |
| diagnostic-2 | C-2-1 | 0.532366 | -0.048329 | 0.214613 | 0.579838 | 0.014613 | 0.079838 | 0.014613 | 0.079838 |
| diagnostic-2 | C-2-2 | 0.481386 | -0.048218 | 0.505818 | 0.582674 | 0.005818 | 0.082674 | 0.005818 | 0.082674 |
| diagnostic-2 | C-2-3 | 0.424238 | -0.057022 | 0.832255 | 0.356330 | 0.032255 | -0.143670 | 0.032255 | 0.143670 |
| diagnostic-2 | C-3-1 | 0.530314 | -0.038126 | 0.226335 | 0.842122 | 0.026335 | 0.042122 | 0.026335 | 0.042122 |
| diagnostic-2 | C-3-2 | 0.488223 | -0.039906 | 0.466765 | 0.796371 | -0.033235 | -0.003629 | 0.033235 | 0.003629 |
| diagnostic-2 | C-3-3 | 0.436911 | -0.046985 | 0.759864 | 0.614377 | -0.040136 | -0.185623 | 0.040136 | 0.185623 |

Calibration y MAE is already **0.063713/0.078086**, with C-3-3 residual **−0.167824/−0.185623**. C-2-1 and C-2-3 also differ by column. The independent-linear model is insufficient to represent these recorded nine feature-to-screen pairs adequately, even before later transfer shifts. This does not isolate a pure static-map defect: calibration observations were sequential, and representation/time/cross-position effects may already be present. A better fit alone would not establish validation transfer.

The y slope increases from 21.495473 to 25.708533 (19.600%). A feature change of 0.005 maps to 0.107477/0.128543 normalized y. Mapping sensitivity amplifies feature shifts; it does not cause the raw features to change.

## 11. Extreme targets: T-1-1 and other cautions

T-1-1 is upper-left (0.2,0.2). Its full-window median v moves from calibration **−0.057932 to −0.048834** in diagnostic-1, and **−0.059212 to −0.047204** in diagnostic-2. Through the same fitted map, these imply mapped median y near 0.46/0.61 rather than 0.2. Sample-level y MAE is **0.218414/0.346378**.

Its current-calibration fit error and later transfer add separately: calibration y residual **+0.065143/+0.100048**, plus slope×feature transfer. The second-half feature still shifts strongly; excluding only the initial transition cannot fix this target. T-1-3 has diagnostic-1’s largest vertical block range; T-3-3 has the largest calibration y error in both sessions. Diagnostic-2 right-column upper/center margin nearly collapses in block 2 despite preserving sign. Preserve all these cases; no outlier is discarded.

## 12. Supported classification, unsupported claims, and limitations

**Outcome C — both, with representation/normalization first.**

- **Feature representation implicated:** h/v preserve target order over short windows, but known same-target raw features shift between calibration and validation, across blocks, and into the second half. The representation carries gaze signal but is insufficiently invariant/transferable in these sessions.
- **Mapping fit implicated:** nine calibration medians already leave appreciable vertical residuals and column/position differences under the independent-linear map. The current mapping is structurally insufficient for those recorded pairs.
- **Priority:** stabilize/characterize the earlier representation layer before adding richer static mappings. A static map trained on calibration cannot repair an unknown later feature-input change; the prior offline map/filter benchmark also selected no validated replacement.
- **Availability:** all validation predictions are usable. The two off-window no-face observations must be reported, but tracking availability is not the main explanation for the measured validation errors.

This does not quantify what percentage of total failure is causally due to each layer. No physical cause, head-pose effect, eyelid effect, anatomy, camera-geometry effect, detector defect, true eye rotation, or fixation compliance was measured here. Target labels express intended fixation, not an independent eye-tracker reference. There is no population/cross-user, cursor-readiness, production correction, or new estimator claim.

Limitations: two same-participant sessions; temporally correlated samples; fixed three-block order can confound position with time; sequential calibration cannot isolate static model inadequacy from changing input geometry; aggregated row order can hide small per-column margins; complete primary windows include gaze transit; normal blinking is not independently labeled; no raw eye/face/pose geometry or images were saved, so physical/geometry explanations cannot be reconstructed from these captures. Display timestamps are software observations, not photon-level timing.

## 13. Next task — bounded raw-geometry representation benchmark (proposal only)

**Do not implement or collect anything in this results task.** Next, specify experiment-owned geometry instrumentation and a small predeclared representation benchmark. Preserve the fixed-window physical protocol: READY, fresh 9-point calibration, same seed/targets/3 blocks, 0.75 s instructional cue, complete 3.0 s target, 0.5 s neutral transition, natural eyes, no cursor and no gaze-gated progress. Use a new explicit geometry-schema/protocol identity to reject legacy feature-only captures while retaining these timings.

### Investigated data boundary

The production adapter (`src/eye_tracker/vision/face_tracker.py`) converts each MediaPipe result to `NormalizedPoint(x,y)` and drops depth and optional face transforms. The current captures contain only h/v and mapped coordinates: missing geometry cannot be invented or recovered, and no images exist to rerun detection. The next task must preserve an experiment-owned numerical sidecar **at the same detector call before XY conversion**, without changing production contracts or feature behavior. Do not run a second independent landmark detector and silently treat its outputs as the production frames.

MediaPipe exposes normalized 3D face landmarks; its optional `facial_transformation_matrixes` output describes canonical-to-detected-face geometry and is disabled by default in the current adapter. The installed 0.10.35 `FaceLandmarkerResult` and `NormalizedLandmark` types confirm these fields. Depth/matrix estimates are not independently measured metric 3D pose or anatomical ground truth. See the [official Face Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python).

| Geometry to retain | Exact existing primitives / bounded investigation |
| --- | --- |
| Iris centers and reconstructable ring | Left ring 474,475,476,477; right ring 469,470,471,472. Retain x/y and available z; current center is arithmetic ring mean. Do not substitute a different iris-center landmark without documenting it. |
| Corners | Left corner_a=263, corner_b=362; right corner_a=33, corner_b=133. Verify inner/outer names and mirrored-coordinate convention from topology when instrumenting; preserve index identity. |
| Lid references | Left upper=386, lower=374; right upper=159, lower=145; derived midpoint/aperture plus current monocular h/v. |
| R0 horizontal reconstruction | Retain all current eye-contour points: left 249,263,362,373,374,380,381,382,384,385,386,387,388,390,398,466; right 7,33,133,144,145,153,154,155,157,158,159,160,161,163,173,246. Current h uses iris x within contour x min/max. |
| R0 vertical reconstruction | Pixel-scaled corners define span/tangent and perpendicular; lid direction sets image-down sign. v = projected iris-minus-corner-midpoint / corner span. Retain raw image size; binocular h/v average both valid eyes. |
| Broader face reference | Reuse documented non-eye anchors 6,197,195,5,4,1,127,234,454,356. Keep raw x/y/available z and calibration-only reference, not just normalized results; retain similarity translation/scale/rotation/RMS. These detector estimates need not be expression-invariant. |
| Pose diagnostics for offline estimation | Investigate retaining the existing optional face transform (matrix/convention/availability) plus selected non-eye 3D coordinates. Keep camera dimensions and explicitly known/unknown intrinsics. Additional pose correspondences must be named/verified before collection, not guessed; avoid saving all 478 points without a declared need. |
| Provenance | Same-frame timestamps, detector/model version and options, geometry-index schema, missing-field flags, calibration/target phase, block/order, and R0 outputs. Never fabricate z/pose when absent. |

### Bounded benchmark and gates to preregister

Keep **R0 = exact production representation** and at most **two alternative families**, frozen before inspecting their outcomes: (1) an independent non-eye face/pose-normalized iris–eye geometry representation, and (2) an explicitly pose-conditioned local-eye geometry representation. Exact formulas, normalization assumptions, and calibration/holdout split must be specified before evaluation; these are proposed families, not implementations or accepted production directions. Exclude already-rejected naive absolute face-y/frozen-span/lid scalar recipes and arbitrary blends, polynomials, eye-opening regressions, and feature search. No new ML.

Construct all session references/maps from ordinary calibration only; target/block/condition labels are evaluation-only and unavailable at runtime. Keep left/right separate before binocular combination. Require genuine row/column separation, held-out transfer, repeatability, spatial accuracy, and mapping amplification to be compared together. Reconstruct R0 numerically from saved geometry and prove agreement first. Freeze an evaluation holdout before candidate outcomes; repeated frames/trials are not independent participant replicates. Do not select a winner from one score.

The immediate next deliverable is instrumentation plus synthetic reconstruction/coordinate/availability tests and a predeclared small benchmark plan. If geometry-rich capture is subsequently authorized, collect one shared fixed-window dataset rather than a new run for each candidate. These two feature-only sessions remain diagnostic evidence, not usable raw-geometry benchmark inputs. No further live session, estimator, filter, mapping alternative, correction, or OS cursor work is started here.

## Appendix A. Every window: first-half and second-half feature medians

Δ = second−first. Every trial remains included.

| Session | Order | Block | Target | h first | h second | Δh | v first | v second | Δv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-1 | 1 | 1 | T-3-2 | 0.488338 | 0.486602 | -0.001735 | -0.037113 | -0.038178 | -0.001065 |
| diagnostic-1 | 2 | 1 | T-1-2 | 0.485857 | 0.487225 | 0.001368 | -0.065798 | -0.064379 | 0.001419 |
| diagnostic-1 | 3 | 1 | T-2-3 | 0.444298 | 0.445019 | 0.000721 | -0.048695 | -0.048858 | -0.000163 |
| diagnostic-1 | 4 | 1 | T-1-3 | 0.440798 | 0.442885 | 0.002087 | -0.054779 | -0.053256 | 0.001523 |
| diagnostic-1 | 5 | 1 | T-3-1 | 0.533636 | 0.531781 | -0.001855 | -0.034746 | -0.035009 | -0.000263 |
| diagnostic-1 | 6 | 1 | T-3-3 | 0.441402 | 0.442358 | 0.000956 | -0.043085 | -0.043184 | -0.000099 |
| diagnostic-1 | 7 | 1 | T-2-2 | 0.488791 | 0.493900 | 0.005109 | -0.050338 | -0.050298 | 0.000040 |
| diagnostic-1 | 8 | 1 | T-1-1 | 0.541259 | 0.541718 | 0.000459 | -0.054919 | -0.054164 | 0.000755 |
| diagnostic-1 | 9 | 1 | T-2-1 | 0.538206 | 0.539651 | 0.001445 | -0.043759 | -0.043316 | 0.000442 |
| diagnostic-1 | 10 | 2 | T-1-3 | 0.435320 | 0.437175 | 0.001855 | -0.058917 | -0.057677 | 0.001240 |
| diagnostic-1 | 11 | 2 | T-3-1 | 0.536622 | 0.536410 | -0.000212 | -0.035908 | -0.036653 | -0.000745 |
| diagnostic-1 | 12 | 2 | T-3-3 | 0.444117 | 0.450210 | 0.006092 | -0.040863 | -0.040291 | 0.000571 |
| diagnostic-1 | 13 | 2 | T-2-2 | 0.488629 | 0.489921 | 0.001293 | -0.052067 | -0.051757 | 0.000310 |
| diagnostic-1 | 14 | 2 | T-1-1 | 0.538108 | 0.538272 | 0.000164 | -0.054486 | -0.045101 | 0.009385 |
| diagnostic-1 | 15 | 2 | T-2-1 | 0.532955 | 0.534191 | 0.001236 | -0.040930 | -0.040593 | 0.000337 |
| diagnostic-1 | 16 | 2 | T-3-2 | 0.487502 | 0.486999 | -0.000503 | -0.037822 | -0.037600 | 0.000222 |
| diagnostic-1 | 17 | 2 | T-1-2 | 0.487980 | 0.487946 | -0.000034 | -0.064944 | -0.062507 | 0.002436 |
| diagnostic-1 | 18 | 2 | T-2-3 | 0.435317 | 0.434690 | -0.000627 | -0.050680 | -0.050787 | -0.000106 |
| diagnostic-1 | 19 | 3 | T-2-2 | 0.483426 | 0.486811 | 0.003385 | -0.049426 | -0.049655 | -0.000229 |
| diagnostic-1 | 20 | 3 | T-1-1 | 0.539173 | 0.542016 | 0.002843 | -0.052604 | -0.048420 | 0.004184 |
| diagnostic-1 | 21 | 3 | T-2-1 | 0.539870 | 0.538422 | -0.001447 | -0.044454 | -0.044730 | -0.000276 |
| diagnostic-1 | 22 | 3 | T-3-2 | 0.488856 | 0.494415 | 0.005560 | -0.040684 | -0.039529 | 0.001155 |
| diagnostic-1 | 23 | 3 | T-1-2 | 0.486611 | 0.487868 | 0.001257 | -0.064995 | -0.061909 | 0.003087 |
| diagnostic-1 | 24 | 3 | T-2-3 | 0.431396 | 0.436493 | 0.005097 | -0.054184 | -0.053030 | 0.001154 |
| diagnostic-1 | 25 | 3 | T-1-3 | 0.434958 | 0.432479 | -0.002479 | -0.067322 | -0.062931 | 0.004391 |
| diagnostic-1 | 26 | 3 | T-3-1 | 0.531430 | 0.533119 | 0.001688 | -0.040367 | -0.041637 | -0.001269 |
| diagnostic-1 | 27 | 3 | T-3-3 | 0.436730 | 0.438297 | 0.001567 | -0.038659 | -0.039546 | -0.000887 |
| diagnostic-2 | 1 | 1 | T-3-2 | 0.492972 | 0.490747 | -0.002225 | -0.034148 | -0.033324 | 0.000824 |
| diagnostic-2 | 2 | 1 | T-1-2 | 0.484355 | 0.483590 | -0.000766 | -0.066327 | -0.063674 | 0.002653 |
| diagnostic-2 | 3 | 1 | T-2-3 | 0.433404 | 0.433306 | -0.000099 | -0.051537 | -0.050635 | 0.000902 |
| diagnostic-2 | 4 | 1 | T-1-3 | 0.429740 | 0.433327 | 0.003586 | -0.062817 | -0.060135 | 0.002682 |
| diagnostic-2 | 5 | 1 | T-3-1 | 0.537657 | 0.538052 | 0.000394 | -0.036285 | -0.036308 | -0.000023 |
| diagnostic-2 | 6 | 1 | T-3-3 | 0.440914 | 0.440409 | -0.000504 | -0.042286 | -0.042700 | -0.000414 |
| diagnostic-2 | 7 | 1 | T-2-2 | 0.481917 | 0.494383 | 0.012466 | -0.051400 | -0.053197 | -0.001797 |
| diagnostic-2 | 8 | 1 | T-1-1 | 0.544199 | 0.550574 | 0.006375 | -0.051982 | -0.043606 | 0.008376 |
| diagnostic-2 | 9 | 1 | T-2-1 | 0.538155 | 0.545576 | 0.007421 | -0.041800 | -0.039162 | 0.002638 |
| diagnostic-2 | 10 | 2 | T-1-3 | 0.444374 | 0.442007 | -0.002367 | -0.064438 | -0.058845 | 0.005594 |
| diagnostic-2 | 11 | 2 | T-3-1 | 0.551627 | 0.549887 | -0.001740 | -0.036391 | -0.035456 | 0.000935 |
| diagnostic-2 | 12 | 2 | T-3-3 | 0.447942 | 0.447478 | -0.000464 | -0.039128 | -0.038820 | 0.000308 |
| diagnostic-2 | 13 | 2 | T-2-2 | 0.499060 | 0.498857 | -0.000203 | -0.048333 | -0.047110 | 0.001223 |
| diagnostic-2 | 14 | 2 | T-1-1 | 0.549504 | 0.549957 | 0.000453 | -0.048170 | -0.046605 | 0.001565 |
| diagnostic-2 | 15 | 2 | T-2-1 | 0.548983 | 0.548047 | -0.000936 | -0.045502 | -0.043911 | 0.001591 |
| diagnostic-2 | 16 | 2 | T-3-2 | 0.500124 | 0.501409 | 0.001285 | -0.037784 | -0.038498 | -0.000714 |
| diagnostic-2 | 17 | 2 | T-1-2 | 0.491373 | 0.493569 | 0.002196 | -0.065706 | -0.064285 | 0.001421 |
| diagnostic-2 | 18 | 2 | T-2-3 | 0.439059 | 0.435491 | -0.003568 | -0.059014 | -0.057508 | 0.001506 |
| diagnostic-2 | 19 | 3 | T-2-2 | 0.494568 | 0.492656 | -0.001912 | -0.055141 | -0.053382 | 0.001760 |
| diagnostic-2 | 20 | 3 | T-1-1 | 0.545051 | 0.548573 | 0.003522 | -0.056569 | -0.053810 | 0.002759 |
| diagnostic-2 | 21 | 3 | T-2-1 | 0.537602 | 0.540025 | 0.002423 | -0.047907 | -0.044462 | 0.003446 |
| diagnostic-2 | 22 | 3 | T-3-2 | 0.497668 | 0.496779 | -0.000889 | -0.038975 | -0.041637 | -0.002662 |
| diagnostic-2 | 23 | 3 | T-1-2 | 0.490138 | 0.488930 | -0.001208 | -0.064570 | -0.063039 | 0.001530 |
| diagnostic-2 | 24 | 3 | T-2-3 | 0.424962 | 0.426897 | 0.001934 | -0.055452 | -0.055422 | 0.000030 |
| diagnostic-2 | 25 | 3 | T-1-3 | 0.429121 | 0.429681 | 0.000560 | -0.069135 | -0.067427 | 0.001708 |
| diagnostic-2 | 26 | 3 | T-3-1 | 0.541592 | 0.537997 | -0.003595 | -0.041399 | -0.042510 | -0.001111 |
| diagnostic-2 | 27 | 3 | T-3-3 | 0.433076 | 0.429546 | -0.003530 | -0.047978 | -0.045916 | 0.002063 |
