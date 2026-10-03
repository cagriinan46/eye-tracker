# Eye-geometry decomposition under five opening prompts

## Purpose, captures, and computation

The question was which **recorded primitive geometry** accounts mathematically for changes in the current vertical feature when the displayed gaze target stays fixed and comfortable eye-opening state changes. This is a feature-level, same-participant diagnostic. It does not independently measure fixation or anatomical motion.

Only the three new local files `.venv/eye-geometry-cagri-live-{1,2,3}.json` were analyzed. The earlier eye-opening controlled-study files and its withdrawn protocol-invalid pilots were **not** used. The [Stage 1 protocol](README.md) fixed the order and analysis before capture. Each new report identifies `cagri`, its expected `live-N` session, `protocol_name=eye_geometry_decomposition`, version **1**, seed **20261004**, a **1.5 s** cue, READY screen, camera **1** at **1920×1080**, **0.8 s** settling and **1.2 s** sampling. The participant reported no additional protocol correction.

| Session | Elapsed s | Calibration / diagnostic / total | Usable raw rows | Usable per presentation | Failed reads / no-face | y slope |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | 177.141 | 9 / 45 / 54 | 1,828 / 1,828 | 33–34 | 0 / 0 | 24.360969 |
| live-2 | 177.163 | 9 / 45 / 54 | 1,829 / 1,829 | 33–34 | 0 / 0 | 23.382147 |
| live-3 | 177.199 | 9 / 45 / 54 | 1,830 / 1,830 | 33–34 | 0 / 0 | 16.343710 |

Every session has all **45 unique** target × condition × block cells, with no duplicates or omissions. Every usable row has both eyes' required geometry. The analyzer reconstructed and checked every per-eye horizontal, vertical, and opening value, binocular averages, and coarse corner-derived diagnostics from the saved primitive coordinates. It also checked presentation counts and saved vertical medians. No run, block, sample, or outlier was excluded. Each presentation summary takes an **independent median per scalar field** over usable sampling rows. All matched differences are condition **minus natural** within the same session, target, and block, unless explicitly labeled otherwise. Displayed numbers are rounded; [analysis.py](analysis.py) emits full-precision presentation and pair records.

## Manipulation check — measured opening first

The intended measured order **comfortably narrow < slightly narrow < natural < slightly wide < comfortably wide** held in **9/9** target/block sets for each session, **27/27** overall. The five-level manipulation therefore separated strongly in the measured aperture feature. These are medians of nine presentation-level medians per condition in each session; labels were not treated as equally spaced numerical doses.

| Session | Comfortably narrow | Slightly narrow | Natural | Slightly wide | Comfortably wide | Strict order |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | 0.108836 | 0.174199 | 0.305254 | 0.354318 | 0.396457 | 9/9 |
| live-2 | 0.135996 | 0.224504 | 0.315970 | 0.356293 | 0.395520 | 9/9 |
| live-3 | 0.184271 | 0.224988 | 0.323435 | 0.381492 | 0.411903 | 9/9 |

The full matched-set opening medians, without an exclusion threshold, are retained below:

| Session | Block | Target | comfortably_narrow | slightly_narrow | natural | slightly_wide | comfortably_wide |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | 1 | upper | 0.102500 | 0.174199 | 0.335795 | 0.399305 | 0.462213 |
| live-1 | 1 | center | 0.076283 | 0.141265 | 0.312194 | 0.393764 | 0.432420 |
| live-1 | 1 | lower | 0.090874 | 0.166757 | 0.287627 | 0.324796 | 0.371934 |
| live-1 | 2 | upper | 0.162760 | 0.266261 | 0.307916 | 0.354318 | 0.382691 |
| live-1 | 2 | center | 0.098717 | 0.153026 | 0.302732 | 0.310639 | 0.351419 |
| live-1 | 2 | lower | 0.122882 | 0.197964 | 0.294515 | 0.353646 | 0.401190 |
| live-1 | 3 | upper | 0.132325 | 0.199245 | 0.305254 | 0.384946 | 0.406686 |
| live-1 | 3 | center | 0.164088 | 0.200185 | 0.309479 | 0.363101 | 0.396457 |
| live-1 | 3 | lower | 0.108836 | 0.141966 | 0.290942 | 0.336204 | 0.393340 |
| live-2 | 1 | upper | 0.157594 | 0.239077 | 0.315970 | 0.356293 | 0.372716 |
| live-2 | 1 | center | 0.121883 | 0.247359 | 0.318465 | 0.358582 | 0.398741 |
| live-2 | 1 | lower | 0.192321 | 0.247079 | 0.298886 | 0.333084 | 0.377875 |
| live-2 | 2 | upper | 0.190044 | 0.224504 | 0.321728 | 0.367146 | 0.396583 |
| live-2 | 2 | center | 0.121219 | 0.199076 | 0.318123 | 0.329217 | 0.395520 |
| live-2 | 2 | lower | 0.099385 | 0.222447 | 0.305298 | 0.331783 | 0.381735 |
| live-2 | 3 | upper | 0.135996 | 0.205219 | 0.333499 | 0.376200 | 0.407674 |
| live-2 | 3 | center | 0.182290 | 0.258076 | 0.309410 | 0.361375 | 0.409276 |
| live-2 | 3 | lower | 0.116172 | 0.188171 | 0.300551 | 0.342594 | 0.388850 |
| live-3 | 1 | upper | 0.213340 | 0.270334 | 0.340350 | 0.399354 | 0.436197 |
| live-3 | 1 | center | 0.232626 | 0.241127 | 0.340007 | 0.381492 | 0.436891 |
| live-3 | 1 | lower | 0.175578 | 0.224674 | 0.314415 | 0.396180 | 0.424208 |
| live-3 | 2 | upper | 0.194101 | 0.246772 | 0.338574 | 0.382129 | 0.405451 |
| live-3 | 2 | center | 0.144198 | 0.200907 | 0.323435 | 0.336522 | 0.411903 |
| live-3 | 2 | lower | 0.184271 | 0.200168 | 0.309028 | 0.363914 | 0.383131 |
| live-3 | 3 | upper | 0.202402 | 0.242670 | 0.354641 | 0.386242 | 0.392604 |
| live-3 | 3 | center | 0.172814 | 0.216671 | 0.310052 | 0.374774 | 0.415625 |
| live-3 | 3 | lower | 0.170595 | 0.224988 | 0.310445 | 0.379336 | 0.401111 |

## Fixed-target vertical-feature response

All **108** natural-reference matched contrasts (four conditions × 27 session/target/block sets) are retained. The more extreme prompts have larger median shifts than the slight prompts. Both extreme narrowing and comfortable widening usually move the recorded feature in the **positive** direction relative to natural, so a single linear opening coefficient would misdescribe the response. These are feature units, not mapped y.

| Condition − natural | Median Δopening | Median Δvertical | Mean Δvertical | Positive/negative |
| --- | ---: | ---: | ---: | ---: |
| comfortably_narrow | -0.158376 | +0.013521 | +0.012642 | 24/3 |
| slightly_narrow | -0.098879 | +0.001202 | +0.002643 | 17/10 |
| slightly_wide | +0.045262 | +0.005446 | +0.005912 | 22/5 |
| comfortably_wide | +0.086978 | +0.021922 | +0.021325 | 27/0 |

Session-specific contrasts show a clear difference in shape: comfortable narrowing was positive in 9/9 comparisons in live-1 and live-2, but only 6/9 in live-3; comfortable widening was positive in **9/9 in every session**. Slight-condition directions varied more.

| Session | Condition − natural | Median Δvertical | Mean Δvertical | Positive/negative |
| --- | ---: | ---: | ---: | ---: |
| live-1 | comfortably_narrow | +0.019978 | +0.020086 | 9/0 |
| live-1 | slightly_narrow | +0.007597 | +0.007453 | 8/1 |
| live-1 | slightly_wide | +0.005446 | +0.007525 | 9/0 |
| live-1 | comfortably_wide | +0.021922 | +0.022340 | 9/0 |
| live-2 | comfortably_narrow | +0.013904 | +0.015058 | 9/0 |
| live-2 | slightly_narrow | +0.001540 | +0.002074 | 5/4 |
| live-2 | slightly_wide | -0.001333 | +0.000167 | 4/5 |
| live-2 | comfortably_wide | +0.011999 | +0.013258 | 9/0 |
| live-3 | comfortably_narrow | +0.002738 | +0.002783 | 6/3 |
| live-3 | slightly_narrow | -0.000263 | -0.001597 | 4/5 |
| live-3 | slightly_wide | +0.010464 | +0.010044 | 9/0 |
| live-3 | comfortably_wide | +0.028416 | +0.028378 | 9/0 |

## Five-level shape and target-row dependence

The response is **nonlinear, asymmetric, and session/row dependent**. Live-1 and live-2 were broadly natural-centered: both extreme states had higher (less negative) vertical features than natural. Live-3's narrow side was close to natural while wide states rose strongly. A descriptive Spearman opening-versus-feature rank correlation across the 45 diagnostic presentations was **+0.005 / −0.078 / +0.580** for live-1/2/3. These whole-session values mix three target rows and repeated blocks; the row-level values below make the differing shapes visible. No p-values or population claim are attached. Across 108 matched natural-reference contrasts, descriptive ρ between **absolute measured opening change** and **absolute vertical change** was **+0.291**; larger aperture changes do not uniquely determine feature-shift size.

| Session | Target | comfortably_narrow | slightly_narrow | natural | slightly_wide | comfortably_wide | Spearman ρ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | upper | -0.054174 | -0.063222 | -0.067695 | -0.055454 | -0.038037 | +0.346 |
| live-1 | center | -0.038701 | -0.046505 | -0.058687 | -0.053242 | -0.041313 | -0.057 |
| live-1 | lower | -0.028726 | -0.045918 | -0.049244 | -0.047815 | -0.029484 | -0.189 |
| live-2 | upper | -0.053506 | -0.061080 | -0.062620 | -0.060611 | -0.048672 | +0.011 |
| live-2 | center | -0.043333 | -0.050941 | -0.056665 | -0.054727 | -0.036076 | +0.004 |
| live-2 | lower | -0.026757 | -0.046142 | -0.045639 | -0.048880 | -0.037922 | -0.193 |
| live-3 | upper | -0.057244 | -0.057236 | -0.057370 | -0.043958 | -0.028953 | +0.764 |
| live-3 | center | -0.049621 | -0.051157 | -0.051830 | -0.042881 | -0.018115 | +0.536 |
| live-3 | lower | -0.040741 | -0.047123 | -0.045628 | -0.034410 | -0.017929 | +0.636 |

At the matched-contrast level, row medians and direction counts were:

| Condition − natural | Target | Median Δopening | Median Δvertical | Mean Δvertical | Positive/negative |
| --- | ---: | ---: | ---: | ---: | ---: |
| comfortably_narrow | upper | -0.152239 | +0.010432 | +0.009814 | 7/2 |
| comfortably_narrow | center | -0.179237 | +0.013904 | +0.013383 | 8/1 |
| comfortably_narrow | lower | -0.171633 | +0.018881 | +0.014729 | 9/0 |
| slightly_narrow | upper | -0.097224 | +0.001167 | +0.001727 | 6/3 |
| slightly_narrow | center | -0.109294 | +0.004825 | +0.004728 | 7/2 |
| slightly_narrow | lower | -0.096551 | -0.000185 | +0.001474 | 4/5 |
| slightly_wide | upper | +0.045418 | +0.008370 | +0.008583 | 8/1 |
| slightly_wide | center | +0.041486 | +0.004069 | +0.005030 | 7/2 |
| slightly_wide | lower | +0.045262 | +0.003843 | +0.004122 | 7/2 |
| comfortably_wide | upper | +0.074776 | +0.025019 | +0.023167 | 9/0 |
| comfortably_wide | center | +0.088468 | +0.023340 | +0.023193 | 9/0 |
| comfortably_wide | lower | +0.088299 | +0.019813 | +0.017617 | 9/0 |

Comfortably wide was positive in **9/9** matched comparisons at each row, but its median feature effect decreased from **+0.025019 upper** to **+0.019813 lower**. Comfortable narrowing instead had median +0.010432 upper and +0.018881 lower. This row dependence rules out collapsing the observed response to one global coefficient.

## Current feature geometry and orientation check

For each eye, the unchanged production vertical feature is `f(I,R) = dot(I − C, N) / W`: `I` is the four-ring-point iris center, `C` is the two-corner midpoint, `W` is the pixel-scaled corner distance, and `N` is the corner-axis normal oriented by the upper-to-lower lid direction. Binocular vertical is the mean of the two monocular features. The diagnostic aperture is the **Euclidean lid separation / W**, a different quantity. [README.md](README.md) lists the exact MediaPipe indices and reconstruction rules.

The pre-flip lid-gap sign was **negative for all 5,487 left-eye usable rows** and **positive for all 5,487 right-eye usable rows**; it never changed within either eye in these captures. Thus lid coordinates determined a fixed orientation sign but **did not directly change `f` through lid displacement** during this study. They did change measured aperture and lid-relative geometry, and may co-vary with iris/corner measurements. “Lid state affected the feature” is an experimental association; “the lid-point coordinate directly enters the feature numerator” would be false for these data.

## Iris versus corner/reference-frame decomposition

For each eye and matched pair, the analyzer forms coordinate-wise presentation medians of iris center and corner/lid points, then evaluates the production formula at four counterfactual combinations: `f(I₀,R₀)`, `f(I₁,R₀)`, `f(I₀,R₁)`, `f(I₁,R₁)`, where `0` is natural and `1` is the changed condition. The **iris contribution** averages the iris substitution under both reference frames; the **reference contribution** averages the frame substitution under both iris positions. This symmetric two-factor attribution splits their nonlinear interaction equally. A **median-aggregation residual** accounts for the difference between the representative-geometry contrast and the actual difference of median per-sample features. For **each individual pair**, iris + reference + residual equals the actual monocular feature difference exactly; medians of these three columns need not sum to the median observed difference. “Reference” includes corner points and lid orientation; because orientation polarity was fixed here, its changing part is the **corner-defined frame**. This is mathematical attribution, not physical or causal attribution.

The pooled table uses 27 matched pairs per condition and eye. It shows median signed contributions and absolute median residual. Comfortable widening yielded a positive reference contribution that typically exceeded an opposing iris-position contribution: the reference term had larger absolute magnitude in **47/54** eye-level comparisons and iris/reference signs opposed in **47/54**. Comfortable narrowing was more mixed across eyes and sessions. Across all four conditions, median absolute residual was **0.000470–0.000759** by contrast; the largest was **0.004615**, so smaller effects require particular care.

| Condition − natural | Eye | Median ΔV | Median I | Median R | Median E | Median abs E | abs R > abs I |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| comfortably_narrow | left | +0.016082 | +0.025501 | -0.009101 | -0.000304 | 0.000808 | 12/27 |
| comfortably_narrow | right | +0.009774 | -0.010279 | +0.018878 | +0.000249 | 0.000426 | 10/27 |
| slightly_narrow | left | +0.005439 | -0.000443 | +0.002359 | +0.000052 | 0.000806 | 13/27 |
| slightly_narrow | right | -0.002064 | -0.027539 | +0.028618 | -0.000068 | 0.000600 | 13/27 |
| slightly_wide | left | +0.005155 | -0.013397 | +0.021522 | -0.000284 | 0.000558 | 19/27 |
| slightly_wide | right | +0.006303 | -0.012425 | +0.021885 | -0.000370 | 0.000614 | 19/27 |
| comfortably_wide | left | +0.022611 | -0.028515 | +0.050028 | -0.000013 | 0.000830 | 24/27 |
| comfortably_wide | right | +0.020758 | -0.024620 | +0.049460 | +0.000092 | 0.000691 | 23/27 |

The following appendix keeps **session × target row × condition × eye** separate. Each value is the median of three block-pair records. `ΔV` is the observed monocular feature contrast; `I`, `R`, and `E` are iris, reference, and median-aggregation-residual contributions. Independently calculated medians are not algebraically additive; the full-precision **individual** records in the analyzer are.

| Session | Target | Condition − natural | L ΔV | L I | L R | L E | R ΔV | R I | R R | R E |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | upper | comfortably_narrow | +0.019299 | +0.038338 | -0.021654 | -0.000460 | +0.011040 | -0.009210 | +0.020144 | +0.000105 |
| live-1 | upper | slightly_narrow | +0.010396 | +0.010812 | -0.005399 | +0.000052 | -0.002064 | -0.024268 | +0.020690 | +0.000274 |
| live-1 | upper | slightly_wide | +0.011556 | -0.025331 | +0.033909 | -0.001030 | +0.012109 | -0.023767 | +0.033216 | -0.001108 |
| live-1 | upper | comfortably_wide | +0.024916 | -0.029248 | +0.058915 | -0.000098 | +0.025151 | -0.031775 | +0.068835 | -0.000119 |
| live-1 | center | comfortably_narrow | +0.018915 | +0.065488 | -0.031019 | -0.000913 | +0.019130 | +0.017954 | +0.009297 | -0.000161 |
| live-1 | center | slightly_narrow | +0.016298 | +0.025327 | -0.009835 | -0.001072 | +0.005790 | -0.019899 | +0.025758 | +0.002078 |
| live-1 | center | slightly_wide | +0.005155 | +0.006779 | -0.000473 | +0.000028 | +0.005642 | +0.002596 | +0.001175 | +0.000073 |
| live-1 | center | comfortably_wide | +0.018324 | +0.000003 | +0.009821 | -0.000223 | +0.016679 | +0.002788 | +0.013002 | -0.000134 |
| live-1 | lower | comfortably_narrow | +0.024508 | +0.091138 | -0.064131 | +0.000044 | +0.020285 | +0.047696 | -0.027054 | +0.000426 |
| live-1 | lower | slightly_narrow | +0.010843 | +0.015313 | -0.007291 | +0.000045 | +0.002872 | -0.020179 | +0.016812 | +0.000034 |
| live-1 | lower | slightly_wide | +0.001413 | -0.013386 | +0.012932 | -0.000216 | +0.005872 | -0.010249 | +0.011624 | -0.000353 |
| live-1 | lower | comfortably_wide | +0.019243 | +0.004968 | +0.018473 | +0.000491 | +0.020343 | -0.004244 | +0.027696 | +0.000312 |
| live-2 | upper | comfortably_narrow | +0.016082 | -0.023217 | +0.040358 | -0.001162 | +0.004666 | -0.083036 | +0.081520 | -0.000244 |
| live-2 | upper | slightly_narrow | +0.003821 | -0.032431 | +0.044946 | -0.002265 | -0.000569 | -0.076234 | +0.072031 | -0.001155 |
| live-2 | upper | slightly_wide | +0.003378 | -0.024572 | +0.025895 | -0.001463 | +0.003483 | -0.021881 | +0.030389 | -0.000889 |
| live-2 | upper | comfortably_wide | +0.015279 | -0.041086 | +0.062724 | -0.001147 | +0.015300 | -0.050891 | +0.055169 | -0.000476 |
| live-2 | center | comfortably_narrow | +0.017597 | +0.011463 | +0.005356 | -0.002199 | +0.010651 | -0.041661 | +0.045259 | +0.001150 |
| live-2 | center | slightly_narrow | +0.005738 | -0.011135 | +0.019083 | +0.000965 | +0.003972 | -0.037681 | +0.041426 | +0.000227 |
| live-2 | center | slightly_wide | -0.003023 | -0.027189 | +0.021733 | -0.002216 | -0.002218 | -0.020719 | +0.025326 | +0.000657 |
| live-2 | center | comfortably_wide | +0.012144 | -0.031887 | +0.054662 | -0.003332 | +0.015540 | -0.035066 | +0.060401 | -0.001758 |
| live-2 | lower | comfortably_narrow | +0.019438 | +0.033856 | -0.029235 | +0.001034 | +0.018324 | +0.004036 | -0.001459 | -0.000903 |
| live-2 | lower | slightly_narrow | +0.003481 | +0.021759 | -0.021163 | +0.000605 | -0.001857 | +0.009321 | -0.010531 | -0.000647 |
| live-2 | lower | slightly_wide | -0.002606 | +0.009577 | -0.010260 | +0.000400 | -0.000138 | +0.015548 | -0.014227 | -0.000436 |
| live-2 | lower | comfortably_wide | +0.006718 | -0.043203 | +0.050028 | +0.001825 | +0.009093 | -0.050402 | +0.059184 | +0.000802 |
| live-3 | upper | comfortably_narrow | +0.006301 | +0.001075 | +0.009370 | +0.000389 | -0.008732 | -0.024612 | +0.019078 | +0.000077 |
| live-3 | upper | slightly_narrow | +0.003069 | -0.008393 | +0.002359 | +0.000345 | -0.002245 | -0.045240 | +0.036969 | -0.000287 |
| live-3 | upper | slightly_wide | +0.011622 | -0.013038 | +0.025452 | -0.000558 | +0.010917 | -0.015240 | +0.026555 | -0.000398 |
| live-3 | upper | comfortably_wide | +0.029483 | -0.014045 | +0.055389 | -0.000477 | +0.027248 | -0.013444 | +0.049460 | -0.000168 |
| live-3 | center | comfortably_narrow | +0.006552 | +0.025501 | -0.009101 | -0.000304 | -0.001138 | -0.007528 | +0.012032 | +0.000708 |
| live-3 | center | slightly_narrow | +0.004289 | +0.007791 | -0.003352 | +0.000593 | -0.002770 | -0.013475 | +0.010160 | +0.000546 |
| live-3 | center | slightly_wide | +0.008412 | -0.006938 | +0.017197 | -0.000080 | +0.009900 | -0.009992 | +0.017300 | +0.000447 |
| live-3 | center | comfortably_wide | +0.036072 | -0.004834 | +0.038742 | +0.000581 | +0.031339 | -0.005440 | +0.032207 | +0.000497 |
| live-3 | lower | comfortably_narrow | +0.012827 | -0.003005 | +0.013323 | -0.000018 | -0.004717 | -0.033398 | +0.033010 | +0.000342 |
| live-3 | lower | slightly_narrow | +0.003557 | -0.036064 | +0.033780 | -0.000181 | -0.006276 | -0.059368 | +0.052082 | +0.000039 |
| live-3 | lower | slightly_wide | +0.011691 | -0.013511 | +0.021522 | -0.000284 | +0.010694 | -0.012425 | +0.021885 | +0.000056 |
| live-3 | lower | comfortably_wide | +0.029039 | -0.025560 | +0.045872 | +0.000209 | +0.026380 | -0.024620 | +0.047626 | -0.000032 |

For comfortable widening, both raw iris centers and corner midpoints usually moved upward in image y, with the corners moving farther: pooled median Δiris y was **−0.001599 / −0.001646** (left/right), versus Δcorner-mid y **−0.002974 / −0.003118**. Iris and corner y moved in opposite directions in only **4/27 left** and **3/27 right** wide contrasts. Thus the preliminary possibility of opposing raw-image motion occurred sometimes but was **not the usual wide-condition pattern**. The local feature rose because the measured iris became more positive relative to the moving corner frame, with orientation/width changes also included in the exact decomposition. The wide median corner-axis width increased by **3.581 / 3.626 px** (left/right); median axis-angle changes were **−0.0422 / +0.0423 rad**. These are landmark-derived geometry changes, not verified head or eyeball motion.

## Eyelid geometry and iris relative to eyelid midpoint

Both lid landmarks moved in the expected *local-frame directions* under every comfortable extreme: comfortable narrowing had upper-lid local Δpositive and lower-lid local Δnegative in **27/27 pairs for each eye**; comfortable widening reversed both signs in **27/27 pairs for each eye**. The shifts were **not symmetric around a fixed midpoint**. The upper-lid local displacement generally had larger median magnitude than the lower-lid displacement, and the lid midpoint shifted: positive with narrowing and negative with widening, particularly at lower target rows. The table gives pooled medians per eye across 27 matched pairs; local coordinates are normalized by each eye's corner width.

| Condition − natural | Eye | Δaperture | Δupper local | Δlower local | Δlid midpoint local | Δiris vs lid midpoint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| comfortably_narrow | left | -0.172342 | +0.117684 | -0.064492 | +0.024770 | -0.008550 |
| comfortably_narrow | right | -0.147315 | +0.090378 | -0.065709 | +0.014055 | -0.007825 |
| slightly_narrow | left | -0.110849 | +0.064555 | -0.050021 | +0.009546 | -0.005196 |
| slightly_narrow | right | -0.091979 | +0.051942 | -0.043222 | +0.002860 | -0.005136 |
| slightly_wide | left | +0.044975 | -0.025985 | +0.018437 | -0.004284 | +0.008986 |
| slightly_wide | right | +0.046149 | -0.025768 | +0.019339 | -0.004625 | +0.010605 |
| comfortably_wide | left | +0.084679 | -0.044197 | +0.036938 | -0.003418 | +0.025431 |
| comfortably_wide | right | +0.085858 | -0.049207 | +0.038118 | -0.004206 | +0.025816 |

The eye feature references the **corner midpoint**, while `iris_vs_lid_mid_vertical` references the **lid midpoint**. Comfortable widening raised iris-versus-lid-midpoint by **+0.025431 / +0.025816** (left/right) versus observed monocular feature medians **+0.022611 / +0.020758**. Comfortable narrowing showed the opposite lid-relative median shift (**−0.008550 / −0.007825**) despite positive feature medians (**+0.016083 / +0.009774**). Thus aperture magnitude, lid midpoint configuration, and corner-relative iris position do not move as one interchangeable quantity. At the lower target, comfortable-narrow lid-midpoint local shifts were larger than at the upper target; comfortable-wide iris-versus-lid shifts were smaller at the lower target. These are descriptive coordinates, not eyelid or iris anatomy.

## Left/right common-mode and disagreement

Same-direction counts below refer to 27 matched pairs per condition. `I` and `R` are the counterfactual contributions above; `lid midpoint` uses the corner-local vertical coordinate. The iris local vertical coordinate **is** the current monocular feature, so its same-direction count equals `Same ΔV` exactly; it is not an independent check. Comfortable widening gave **27/27 same-direction observed monocular vertical shifts** and **27/27 same-direction reference contributions**, with small median absolute left-minus-right feature difference **0.002150**. Slight widening was also mostly common-direction. Narrowing was less consistent: in live-3, comfortable-narrow monocular feature signs agreed in only **1/9** pairs. Binocular averaging therefore hides meaningful monocular disagreement on the narrow side.

| Condition − natural | Same ΔV | Same I | Same R | Same lid midpoint | Median common ΔV | Median abs(L−R) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| comfortably_narrow | 18/27 | 18/27 | 22/27 | 25/27 | +0.013510 | 0.008668 |
| slightly_narrow | 15/27 | 19/27 | 20/27 | 23/27 | +0.001335 | 0.006799 |
| slightly_wide | 25/27 | 26/27 | 26/27 | 27/27 | +0.005398 | 0.001319 |
| comfortably_wide | 27/27 | 26/27 | 27/27 | 27/27 | +0.021895 | 0.002150 |

## Coarse head/face diagnostics and largest shifts

All four diagnostics are derived from **the same eye-corner landmarks**: head-center x/y are corner means, inter-eye scale is the distance between corner midpoints, and eye-line angle is their line angle. They are useful geometry records but **not independent head-motion measurements**. Across the 36 natural-reference contrasts per session, median absolute changes were:

| Session | Median abs Δhead x | Median abs Δhead y | Median abs Δscale px | Median abs Δroll rad |
| --- | ---: | ---: | ---: | ---: |
| live-1 | 0.000538 | 0.001564 | 0.963627 | 0.008172 |
| live-2 | 0.000662 | 0.002628 | 1.048448 | 0.006523 |
| live-3 | 0.000345 | 0.001641 | 0.753263 | 0.004000 |

Comfortably wide had median Δhead-center y **−0.003028** (negative in 24/27 pairs), but median Δhead-center x was only **+0.000055**, and scale/roll changes were comparatively mixed. Narrow prompts changed the eye-line angle in the positive direction in **27/27 pairs** for each narrow condition, yet their vertical effects were not equally consistent. The strongest vertical contrasts below include cases with small x/scale/roll changes and others with larger changes. No single coarse diagnostic isolates head movement from the eye-corner geometry already used in `f`.

| Session | Target | Block | Condition | Δvertical | Δhead x | Δhead y | Δscale px | Δroll rad |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | upper | 1 | comfortably_wide | +0.036758 | +0.000055 | -0.003990 | +0.207 | +0.001325 |
| live-1 | center | 1 | comfortably_wide | +0.033968 | -0.000530 | -0.004653 | +1.188 | -0.003354 |
| live-1 | center | 2 | comfortably_narrow | +0.029765 | +0.000291 | +0.000395 | +2.166 | +0.016339 |
| live-1 | lower | 3 | comfortably_narrow | +0.025341 | +0.001363 | +0.002744 | +2.010 | +0.014709 |
| live-1 | upper | 3 | comfortably_wide | +0.025019 | -0.000201 | -0.002857 | -0.192 | -0.001477 |
| live-2 | lower | 2 | comfortably_narrow | +0.028409 | +0.000968 | -0.004001 | +3.544 | +0.017520 |
| live-2 | center | 2 | comfortably_narrow | +0.025303 | -0.000181 | -0.002430 | +3.243 | +0.019091 |
| live-2 | upper | 3 | comfortably_wide | +0.025193 | -0.001081 | -0.002907 | +1.370 | -0.005387 |
| live-2 | center | 3 | comfortably_wide | +0.023340 | +0.000458 | -0.003434 | +0.071 | -0.000880 |
| live-2 | upper | 3 | comfortably_narrow | +0.023286 | -0.000185 | +0.001975 | +0.382 | +0.015892 |
| live-3 | upper | 1 | comfortably_wide | +0.038524 | -0.000064 | -0.003362 | +0.018 | -0.000968 |
| live-3 | center | 1 | comfortably_wide | +0.036921 | +0.000249 | -0.003112 | +0.753 | +0.002695 |
| live-3 | center | 2 | comfortably_wide | +0.033715 | -0.000548 | -0.000916 | +0.777 | -0.001749 |
| live-3 | center | 3 | comfortably_wide | +0.029139 | +0.000108 | -0.002294 | +0.765 | -0.002109 |
| live-3 | upper | 2 | comfortably_wide | +0.028416 | -0.001287 | -0.003947 | -0.001 | -0.003618 |

These diagnostics do **not** exclude pitch, yaw, three-dimensional translation, camera-geometry change, facial deformation, or imperfect fixation. No causal direction is assigned.

## Block and presentation-order behavior

Each row/condition was measured in all three fixed-order blocks. The table shows each block's median feature contrast over its three target rows, plus positive-count out of three. Comfortable widening remained positive in **all three rows of every block in every session**. Live-1 and live-3 wide medians decreased across blocks; live-2 increased, so there is no single monotonic session-time drift that explains the result. Slight-condition directions were less repeatable. All early and late blocks remain included.

| Session | Condition − natural | Block 1 | Block 2 | Block 3 |
| --- | ---: | ---: | ---: | ---: |
| live-1 | comfortably_narrow | +0.018983 (3/3 +) | +0.022274 (3/3 +) | +0.021408 (3/3 +) |
| live-1 | slightly_narrow | +0.004343 (3/3 +) | +0.009935 (3/3 +) | +0.007597 (2/3 +) |
| live-1 | slightly_wide | +0.012241 (3/3 +) | +0.005208 (3/3 +) | +0.005446 (3/3 +) |
| live-1 | comfortably_wide | +0.033968 (3/3 +) | +0.021922 (3/3 +) | +0.019813 (3/3 +) |
| live-2 | comfortably_narrow | +0.004741 (3/3 +) | +0.025303 (3/3 +) | +0.018881 (3/3 +) |
| live-2 | slightly_narrow | -0.002866 (0/3 +) | +0.007894 (3/3 +) | +0.001540 (2/3 +) |
| live-2 | slightly_wide | -0.003517 (0/3 +) | +0.000045 (2/3 +) | +0.004069 (2/3 +) |
| live-2 | comfortably_wide | +0.008928 (3/3 +) | +0.013774 (3/3 +) | +0.023340 (3/3 +) |
| live-3 | comfortably_narrow | +0.004366 (3/3 +) | +0.002735 (2/3 +) | -0.000650 (1/3 +) |
| live-3 | slightly_narrow | +0.001167 (2/3 +) | +0.000689 (2/3 +) | -0.004757 (0/3 +) |
| live-3 | slightly_wide | +0.012234 (3/3 +) | +0.008843 (3/3 +) | +0.010464 (3/3 +) |
| live-3 | comfortably_wide | +0.036921 (3/3 +) | +0.028416 (3/3 +) | +0.027858 (3/3 +) |

## Secondary mapped-y impact

The unmodified session calibration y slopes were **24.360969 / 23.382147 / 16.343710**. `Δmapped y = y_slope × Δbinocular vertical` is reported without clipping and is **model-output context**, not an independently measured gaze error. A feature shift of **0.010** would map to **0.2436 / 0.2338 / 0.1634** normalized y in live-1/2/3. For comfortable widening, session median matched output changes were **+0.5340 / +0.2806 / +0.4644**, and the largest absolute matched changes were **0.8955 / 0.5891 / 0.6296**. Those magnitudes explain why the observed feature movement could matter operationally, without identifying its cause or establishing cursor usability.

## Supported conclusions, limits, and next bounded step

**Supported:** the corrected five-level manipulation separated in all 27 matched sets. At fixed displayed targets, both extreme opening prompts often shifted the vertical feature positively relative to natural; slight prompts were smaller and less consistent. The response differed across sessions and target rows. The saved primitives support an exact, symmetric two-factor **mathematical** decomposition. In comfortable-wide contrasts, changing the corner-defined reference frame contributed more than raw iris-position substitution in most eye-level pairs, commonly opposing it; lid landmarks shifted aperture and midpoint but did not flip the current feature's normal. Wide-condition feature changes were strongly common-direction across eyes. Narrow-condition attribution and monocular direction were mixed.

**Unsupported:** these data do not establish that eyelids are the sole root cause, that the participant's true gaze or iris anatomically moved, that MediaPipe is defective, or that corner changes represent head motion. They do not justify a linear, quadratic, or other production correction, a new quality threshold, cross-user generalization, production readiness, or cursor readiness. All three sessions are from one participant; the same presentations enter overlapping pair records; displayed targets do not independently verify fixation; image-coordinate iris/corner/lid features and coarse head diagnostics are not independent physical measurements. Coordinate-wise median geometry is a descriptive construct and leaves a documented residual. Vertical instability remains unresolved at the physical/source level.

**Recommended next bounded step:** if separately approved, collect a short fixed-target numerical study that adds a **small set of extraocular facial reference landmarks** and a stronger independent head-pose/fixation diagnostic while repeating natural and comfortable-wide states. This would test whether the eye-corner frame shifts relative to the face or with whole-head geometry, the ambiguity most exposed by the wide-condition decomposition. Preserve the current feature and mapping as comparators; do not implement a production correction from these data. No further experiment is started here.
