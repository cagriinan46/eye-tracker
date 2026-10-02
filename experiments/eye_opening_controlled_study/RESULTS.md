# Controlled eye-opening study — three completed Çağrı sessions

## Capture validity and analysis method

The three real, Git-ignored inputs are `.venv/eye-opening-cagri-live-{1,2,3}.json`. Each identifies participant `cagri` and its matching `live-1`, `live-2`, or `live-3` session. The analyzer recomputed each field's **presentation median from the original usable numerical sampling rows**, checked all 36 saved presentations and their counts against the fixed protocol, checked the stored binocular medians, and verified the per-frame binocular vertical feature against the left/right arithmetic mean. There are nine natural-opening calibration presentations and 27 diagnostic presentations (three targets × three conditions × three blocks) in **each** session. Diagnostic targets were upper `(0.5, 0.25)`, center `(0.5, 0.50)`, and lower `(0.5, 0.75)`. All conditions, blocks, target coordinates, and presentation orders match the preregistered schedule. No presentation or session was excluded from the primary analysis.

| Session | Calibration / diagnostic | Sampling rows / usable | Minimum usable per presentation | Failed camera reads / no-face observations | Camera / resolution | Elapsed | Fitted x slope / intercept | Fitted y slope / intercept |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| live-1 | 9 / 27 | 1,220 / 1,220 | 33 | 0 / 0 | index 1 / 1920×1080 | 75.05 s | −5.56314 / 3.23417 | 27.16255 / 1.89789 |
| live-2 | 9 / 27 | 1,220 / 1,220 | 33 | 0 / 0 | index 1 / 1920×1080 | 74.59 s | −5.57957 / 3.26843 | 23.40101 / 1.77797 |
| live-3 | 9 / 27 | 1,217 / 1,217 | 33 | 0 / 0 | index 1 / 1920×1080 | 77.64 s | −5.90467 / 3.42339 | 25.23071 / 1.85848 |

The saved reports include x and y mapping coefficients, resolution, reads, timing, per-attempt status, and all derived eye/head fields. The full-precision, scatter-friendly 81 diagnostic presentation records and 81 fixed-target condition pair records can be reproduced with the command in [README.md](README.md). The JSON input and full analyzer output remain local; no imagery was saved or committed.

## Human-reported capture disturbances

The participant reported that the target window appeared roughly 1–2 seconds late at the beginning of **each** complete run. This was reported independently of numerical selection and does not technically invalidate the runs. The first calibration presentation (`C-1-1`) is retained. Its within-presentation vertical `p95−p05` spread was **0.010960 / 0.015312 / 0.014413** in live-1/2/3, versus median spread **0.001534 / 0.002094 / 0.001492** across each session's other eight calibration presentations. The first target's mapped y was 0.33196 / 0.30646 / 0.25387 at actual y 0.20. The timing and extra spread make first-target calibration context less certain; they do not establish that the window delay caused the spread or quantify its effect on the fitted slope. No recalibration or first-target exclusion was performed.

The participant also reported a roughly 1–2 second system notification at the transition into live-3's diagnostic section. The fixed schedule and saved order identify the first diagnostic target set as **upper, block 1, orders 10–12**: narrow, natural, wide. Their sampling windows began around 24.09, 26.11, and 28.12 seconds after collection start. Their vertical medians were **−0.069451, −0.070412, −0.067107**, respectively. Later upper-target block-2/3 medians were roughly −0.0595 to −0.0569. The notification is a known distraction, but the numerical record cannot prove which frames it affected or that it caused the shift. All three presentations stay in the primary results; the secondary exclusion below removes exactly this initial trio.

## Manipulation check — measured opening first

Each entry below is the **median binocular opening of one diagnostic presentation**, computed from its actual usable samples. Deltas are signed second condition minus first: `N−Nat = narrow − natural`, `W−Nat = wide − natural`, `W−N = wide − narrow`. The requested order is strict `narrow < natural < wide`. Values are rounded to six decimals; the analyzer emits full precision. This check uses measured opening, not condition labels.

| Session | Target | Block | Narrow | Natural | Wide | N−Nat | W−Nat | W−N | Ordered? |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| live-1 | upper | 1 | 0.350900 | 0.361940 | 0.367849 | −0.011040 | +0.005909 | +0.016949 | yes |
| live-1 | upper | 2 | 0.361469 | 0.352438 | 0.361030 | +0.009031 | +0.008592 | −0.000439 | no |
| live-1 | upper | 3 | 0.362385 | 0.365878 | 0.360595 | −0.003493 | −0.005282 | −0.001790 | no |
| live-1 | center | 1 | 0.353424 | 0.352312 | 0.352871 | +0.001111 | +0.000558 | −0.000553 | no |
| live-1 | center | 2 | 0.341938 | 0.345173 | 0.335457 | −0.003235 | −0.009715 | −0.006481 | no |
| live-1 | center | 3 | 0.352429 | 0.350559 | 0.352709 | +0.001870 | +0.002151 | +0.000280 | no |
| live-1 | lower | 1 | 0.337815 | 0.334208 | 0.339513 | +0.003607 | +0.005305 | +0.001698 | no |
| live-1 | lower | 2 | 0.332887 | 0.334810 | 0.331743 | −0.001923 | −0.003066 | −0.001144 | no |
| live-1 | lower | 3 | 0.332699 | 0.331769 | 0.334358 | +0.000930 | +0.002589 | +0.001660 | no |
| live-2 | upper | 1 | 0.334241 | 0.341122 | 0.346725 | −0.006881 | +0.005603 | +0.012484 | yes |
| live-2 | upper | 2 | 0.348698 | 0.341040 | 0.348299 | +0.007658 | +0.007259 | −0.000399 | no |
| live-2 | upper | 3 | 0.348098 | 0.351528 | 0.343710 | −0.003431 | −0.007818 | −0.004388 | no |
| live-2 | center | 1 | 0.335679 | 0.332412 | 0.342196 | +0.003266 | +0.009784 | +0.006518 | no |
| live-2 | center | 2 | 0.332787 | 0.333085 | 0.338867 | −0.000298 | +0.005783 | +0.006080 | yes |
| live-2 | center | 3 | 0.338238 | 0.338910 | 0.334966 | −0.000672 | −0.003944 | −0.003272 | no |
| live-2 | lower | 1 | 0.312754 | 0.316405 | 0.311809 | −0.003651 | −0.004596 | −0.000945 | no |
| live-2 | lower | 2 | 0.314842 | 0.313470 | 0.315225 | +0.001372 | +0.001755 | +0.000384 | no |
| live-2 | lower | 3 | 0.304447 | 0.287053 | 0.304341 | +0.017394 | +0.017288 | −0.000106 | no |
| live-3 | upper | 1 | 0.336791 | 0.345445 | 0.347604 | −0.008654 | +0.002159 | +0.010813 | yes |
| live-3 | upper | 2 | 0.356949 | 0.341067 | 0.343080 | +0.015882 | +0.002013 | −0.013869 | no |
| live-3 | upper | 3 | 0.350125 | 0.350464 | 0.345472 | −0.000340 | −0.004993 | −0.004653 | no |
| live-3 | center | 1 | 0.325093 | 0.331418 | 0.337639 | −0.006325 | +0.006221 | +0.012546 | yes |
| live-3 | center | 2 | 0.320809 | 0.321226 | 0.316683 | −0.000418 | −0.004543 | −0.004126 | no |
| live-3 | center | 3 | 0.332422 | 0.308403 | 0.327478 | +0.024019 | +0.019075 | −0.004944 | no |
| live-3 | lower | 1 | 0.310176 | 0.308201 | 0.308913 | +0.001975 | +0.000712 | −0.001263 | no |
| live-3 | lower | 2 | 0.307033 | 0.310790 | 0.313695 | −0.003757 | +0.002905 | +0.006662 | yes |
| live-3 | lower | 3 | 0.313707 | 0.307984 | 0.314830 | +0.005722 | +0.006845 | +0.001123 | no |

| Session | Full N < Nat < W | Narrow < natural | Wide > natural | Wide > narrow |
| --- | ---: | ---: | ---: | ---: |
| live-1 | 1/9 | 4/9 | 6/9 | 4/9 |
| live-2 | 2/9 | 5/9 | 6/9 | 4/9 |
| live-3 | 3/9 | 4/9 | 7/9 | 5/9 |
| **Total** | **6/27** | **13/27** | **19/27** | **13/27** |

The human-side approximate **1/9, 2/9, 3/9** full-order check agrees exactly with the recomputation. Although wide exceeded natural in 19/27 triples, narrow was below natural in only 13/27, and wide exceeded narrow in only 13/27. Across the three blocks, all three target rows in every session had overlapping presentation-median opening ranges for each condition pair. Median within-presentation opening `p95−p05` was 0.002395 / 0.004833 / 0.005465 in live-1/2/3. The intended three-level manipulation was **weak and inconsistent**. There is no post hoc threshold declaring success or failure from effect size; the ordering and overlap are reported directly.

## Primary fixed-target condition comparisons

All 81 comparisons use same-session, same-target, same-block presentations. The full analyzer output contains each comparison's measured opening, binocular and left/right vertical, per-eye opening, and head-center deltas. This table summarizes signed **median of the nine block/target pair deltas per session**, plus positive/negative binocular-vertical counts; the pooled rows use 27 dependent pairs and are descriptive. A median of paired deltas need not equal a difference of across-block condition medians.

| Session | Contrast | Median Δopening | Median Δbinocular vertical | Vertical + / − | Median abs Δhead-center y |
| --- | --- | ---: | ---: | ---: | ---: |
| live-1 | narrow−natural | +0.000930 | −0.002128 | 2 / 7 | 0.000559 |
| live-1 | wide−natural | +0.002151 | −0.002120 | 1 / 8 | 0.001191 |
| live-1 | wide−narrow | −0.000439 | −0.000190 | 4 / 5 | 0.001286 |
| live-2 | narrow−natural | −0.000298 | +0.000583 | 5 / 4 | 0.000870 |
| live-2 | wide−natural | +0.005603 | +0.000003 | 5 / 4 | 0.002009 |
| live-2 | wide−narrow | −0.000106 | −0.000818 | 4 / 5 | 0.001872 |
| live-3 | narrow−natural | −0.000340 | +0.000221 | 5 / 4 | 0.001593 |
| live-3 | wide−natural | +0.002159 | +0.001616 | 6 / 3 | 0.001462 |
| live-3 | wide−narrow | −0.001263 | +0.000190 | 5 / 4 | 0.001194 |
| **Pooled** | **narrow−natural** | **−0.000298** | **−0.000641** | **12 / 15** | — |
| **Pooled** | **wide−natural** | **+0.002159** | **−0.000217** | **12 / 15** | — |
| **Pooled** | **wide−narrow** | **−0.000399** | **−0.000004** | **13 / 14** | — |

These pooled vertical medians agree with the human-side approximate −0.00064, −0.00022, and ~0.00000 cross-checks. Condition-labeled feature direction **does not repeat across sessions**: live-1's wide−natural median was negative and 8/9 pair deltas were negative, while live-2 was near zero and live-3 was positive. For wide−natural comparisons with **measured wide opening greater than natural**, positive/negative vertical counts were 1/5 (live-1), 4/2 (live-2), and 4/3 (live-3); no common direction follows. Among the six fully ordered opening triples, vertical medians were strictly increasing in one and strictly decreasing in one, with neither order in four. There is no stable ordered descriptive vertical response.

## Actual measured opening versus vertical change

The preregistered 27 condition-pair records per session were also compared by their **actual signed measured opening delta** and signed binocular vertical delta. Spearman is an additional Stage 2 descriptive summary of those fixed pair records, rather than a preregistered test. The rank coefficients are **+0.623, −0.024, and −0.439** for live-1/2/3; the clearly labeled pooled descriptive coefficient is **+0.037** across 81 overlapping pair records. These pairs reuse presentations and one participant, so they are not 81 independent trials or population evidence. The relationship is not directionally repeatable across sessions. In particular, a positive association in live-1 does not validate the earlier observational positive association when live-2 is near zero and live-3 reverses sign. No p-values or causal interpretation are used.

## Monocular and common-mode behavior

For each matched contrast, `common = (Δleft + Δright)/2` and `differential = Δleft − Δright`, using separate presentation medians. Both eye deltas had the same sign in **22/27, 21/27, and 20/27** condition comparisons in live-1/2/3 (63/81 overall); opposite signs occurred in 5, 6, and 7. Median absolute common-mode deltas were **0.001946 / 0.001726 / 0.001511**; median absolute differential deltas were **0.000585 / 0.001278 / 0.000986**. Thus many shifts were shared across eyes, including each session's largest absolute binocular contrast, but monocular disagreement is material and the earlier observational common-mode pattern does not imply a consistent opening effect here. The per-frame binocular mean identity held; independently taken presentation medians were not substituted for the actual binocular median.

## Head-center confound

Median absolute head-center-y contrast changes were roughly 0.0006–0.0020 across the nine session/contrast groups above. Maxima were **0.003687 / 0.005206 / 0.021681** in live-1/2/3. The largest live-3 head-center change (upper, block 2, narrow−natural: −0.021681) had a comparatively small binocular feature delta of −0.000289; live-3 center block-1 narrow−natural instead combined +0.009588 head-center and +0.006048 vertical change. Signed head-center/vertical Spearman association over the 27 pair records was **−0.692 / −0.228 / +0.404** across sessions. These differences are a confound and show no consistent attribution. Head-center y is a coarse image-coordinate proxy and cannot isolate pitch or translation.

## Secondary live-3 notification sensitivity

**Primary results above retain every valid presentation.** The only excluded set in this secondary check is live-3's first upper-target block-1 condition trio, orders 10–12. This removes exactly three diagnostic presentations and their three within-trio comparisons, leaving **24 diagnostic presentations and 24 pair records** in live-3. It does not alter calibration, other target rows, other live-3 blocks, or either other session. The full triples are retained in the saved input and primary output.

| Measure | Primary live-3 | Secondary without orders 10–12 |
| --- | ---: | ---: |
| Full opening order | 3/9 | 2/8 |
| Signed opening/vertical Spearman | −0.439 | −0.568 |
| Median narrow−natural vertical / sign +:− | +0.000221 / 5:4 | −0.000034 / 4:4 |
| Median wide−natural vertical / sign +:− | +0.001616 / 6:3 | +0.001072 / 5:3 |
| Median wide−narrow vertical / sign +:− | +0.000190 / 5:4 | +0.000093 / 4:4 |

Across all three sessions, full measured opening order changes from **6/27 to 5/26** triples; pooled signed opening/vertical Spearman changes from **+0.037 to +0.024**. Pooled vertical contrast medians remain near zero: narrow−natural **−0.000789**, wide−natural **−0.000231**, wide−narrow **−0.000051**. The weak manipulation, inconsistent cross-session association, and absence of a stable condition-direction response **do not change**. This exclusion is a sensitivity calculation, not a technical invalidation or evidence that the notification caused the observed live-3 values.

## Supported conclusions, unsupported conclusions, and limitations

**Supported:** all three sessions were technically valid and were retained. The requested narrow/natural/wide manipulation yielded the full measured opening order in only 6/27 same-target block triples, so the intended three-level separation was weak and inconsistent. Condition-labeled vertical shifts and actual measured opening/vertical associations did not repeat in a common direction across sessions. Both eyes often moved together, but this did not establish an eye-opening mechanism. The first calibration target and live-3 transition have human-reported disturbances that may affect interpretation; the bounded live-3 sensitivity does not change the main description. The prior observational opening association received **no clear confirmation** from this controlled protocol.

**Unsupported:** this weak manipulation does **not prove absence of an eye-opening effect**. It does not show that eyelids, head motion, MediaPipe, or camera geometry caused or did not cause vertical-feature instability. It does not establish a correction, mapping change, quality gate, production or cursor readiness, or cross-user reliability. No production eye-opening correction was selected.

**Limitations:** one participant, three short sessions, dependent comparisons sharing presentations, no independent fixation or head-pose measure, and related landmark geometry in the opening and vertical features. Requested opening conditions were not reliably realized in the measured feature. The first-target window delay and live-3 notification are participant reports; exact affected frames are not identified by the numerical record. Calibration and diagnostic order, gaze history, time, and face/camera geometry remain possible influences. The secondary exclusion is broader than the reported 1–2 second notification and is deliberately conservative. These bounds prevent a causal or population inference.

## Recommended next technical step

Before another human session is requested, review this study's condition instructions and on-screen transition timing against the measured opening distributions, then preregister a **more reliably separable yet comfortable manipulation and an independent fixation/head-position control or measurement**. The design should verify the measured manipulation during collection without coaching toward numerical outcomes, retain the three known gaze rows and per-eye numerical observations, and define its analysis before capture. This is a proposal for a separately approved diagnostic, not an instruction to start it or a production correction.
