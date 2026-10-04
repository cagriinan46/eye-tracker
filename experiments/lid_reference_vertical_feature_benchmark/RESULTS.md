# Final offline lid-reference vertical-feature candidate round

## Motivation, fixed formulas, and split

This was the final bounded hand-crafted feature round after corner-referenced alternatives failed to give a consistent improvement. No camera capture or production modification occurred. The [README](README.md) fixed **exactly two** lid-referenced formulas and six held-out criteria before candidate results were computed. Production remains the baseline: for iris center `I`, corner midpoint `M`, lid-oriented corner normal `n`, and current corner span `s`, each eye reports `(I−M)·n/s`; the binocular value averages both eyes. The exact production iris center is the mean of four iris-ring points. All geometry is pixel-scaled before projection.

The two alternatives use each eye's calibration-only median corner span `s_cal` and calibration-only fixed vertical axis `n_cal`:

- **`lid_midpoint_fixed_scale`:** `(I−(upper+lower)/2)·n_cal/s_cal`.
- **`lid_fraction`:** `(I−(upper+lower)/2)·n_cal/((lower−upper)·n_cal)`, equal to the centered `(i−u)/(l−u)−0.5` fraction. A projected aperture ≤1e-6 px is unavailable; none occurred in the six evaluated captures.

The **primary development set** is `.venv/face-reference-cagri-live-1.json` and `-2.json`; the **predeclared decision holdout for these formulas** is `.venv/face-reference-cagri-live-3.json`, all `face_reference_corner_stability` protocol v1, participant Çağrı. Development was computed and inspected before the new candidate results on live-3; definitions and thresholds were unchanged. After the holdout decision, the three `.venv/eye-geometry-cagri-live-{1,2,3}.json` protocol-v1 sessions were evaluated separately as a **secondary historical check**. Existing strict capture analyzers validated all six reports and their saved numerical geometry. No protocol-invalid pilot or earlier eye-opening report entered the statistics.

Each candidate/eye/binocular output received a fresh ordinary least-squares y mapping from **only nine ordinary calibration presentation medians**. All later metrics use diagnostic presentations; no clipping, label-specific fit, or diagnostic reference was used. The production calibration fits reproduced the saved coefficients. Natural diagnostics have nine presentations per session; each condition has nine target/block comparisons to natural; repetition uses 27 same-target/condition block pairs per session. Values are descriptive, correlated observations from one participant.

## Held-out live-3 decision: **NO WINNER**

| Holdout metric | Production | Lid midpoint + fixed scale | Lid fraction |
| --- | ---: | ---: | ---: |
| Natural U/C/L predicted medians | .288/.532/.930 | **.464/.459/.420** | **.459/.445/.461** |
| Natural row order; U→C / C→L margin | Yes; +.244/+.398 | **No; −.005/−.039** | **No; −.014/+.016** |
| Natural y MAE / median abs / p95 abs | .1365/.1533/.2645 | .2214/.2137/.4325 | .2172/.2089/.4137 |
| Natural signed bias | +.0774 | −.0287 | −.0120 |
| Narrow mapped shift, median / p95 abs | .6993/.8109 | .2599/.4103 | **2.1813/3.8293** |
| Wide mapped shift, median / p95 abs | .3091/.7216 | **.8143/.9176** | **.6864/.8051** |
| Block-repeat mapped shift, median / p95 / max abs | .2105/.5026/.8165 | .1233/.4810/.5861 | .2335/1.4611/1.7790 |
| Calibration mapped sample-noise metric | .02667 | .00888 | .00873 |

The midpoint candidate's narrow-state and median repeated-block gains do **not** compensate for lost gaze ordering, 62% higher natural MAE, and a 2.63× wide-state shift. The lid fraction loses gaze ordering, raises natural MAE 59%, and worsens both opening shifts. A stable near-center prediction is not gaze discrimination. No post-hoc feature definition or threshold was introduced to rescue either candidate.

The fixed eligibility rule was: strict natural U<C<L; natural MAE ratio ≤1.15; at least one median mapped narrow/wide shift ratio ≤.85; the other ≤1.15; median mapped repeat ratio ≤1.15; calibration mapped sample-noise ratio ≤1.15. Ratios are candidate ÷ production on **live-3 binocular** data:

| Criterion | Midpoint ratio / result | Fraction ratio / result |
| --- | ---: | ---: |
| Natural row ordering | reversed; **FAIL** | nonordered; **FAIL** |
| Natural y MAE ≤1.15× | 1.623; **FAIL** | 1.591; **FAIL** |
| At least one opening shift ≤.85× | narrow .372; **PASS** | best wide 2.220; **FAIL** |
| Other opening shift ≤1.15× | wide 2.634; **FAIL** | narrow 3.119; **FAIL** |
| Median repeated-target mapped shift ≤1.15× | .586; **PASS** | 1.109; **PASS** |
| Calibration mapped sample-noise ≤1.15× | .333; **PASS** | .327; **PASS** |
| **Overall** | **FAIL** | **FAIL** |

The amplification measure is `abs(fitted slope) × median of the nine within-calibration-presentation feature MADs`. It uses calibration observations only and compares different feature units in mapped-y space. Passing that check alone does not preserve gaze information or prevent deliberate-condition shifts.

## Development sessions: live-1 and live-2

| Session/candidate | Natural MAE | U/C/L natural predicted medians | Narrow mapped median | Wide mapped median | Repeat mapped median | Calibration slope / span / MAE / residual p95 abs | Calibration mapped noise |
| --- | ---: | --- | ---: | ---: | ---: | --- | ---: |
| live-1 production | .0838 | .191/.552/.765 | .4867 | .1888 | .0936 | +29.14 / .021916 / .0334 / .0903 | .01096 |
| live-1 midpoint | .1928 | .318/.358/.338 **nonordered** | .2557 | .4707 | .1390 | +39.25 / .010265 / .1573 / .3765 | .01882 |
| live-1 fraction | .2678 | .259/.242/.229 **nonordered** | 1.1321 | .5226 | .2570 | +10.49 / .032748 / .1769 / .3850 | .01743 |
| live-2 production | .1516 | .238/.709/.904 | .5312 | .3706 | .1715 | +32.00 / .019255 / .1234 / .2476 | .01633 |
| live-2 midpoint | .2312 | .538/.555/.498 **nonordered** | .1528 | .9117 | .0955 | −35.63 / .010578 / .1782 / .3317 | .02790 |
| live-2 fraction | .2688 | .636/.685/.594 **nonordered** | 2.0954 | 1.0273 | .3006 | −12.07 / .036680 / .1578 / .3219 | .02774 |

Both alternatives already lost natural row ordering in both development sessions. The midpoint feature improved narrow shifts but made wide shifts larger, consistent with the holdout failure. Fraction was especially sensitive to narrowing. These observations were not used to redefine either formula. Its development calibration mapped-noise measure was also worse than production in both sessions.

## Feature-space, repeatability, and calibration detail

Feature units differ; mapped y is the fairer operational comparison. Nonetheless the actual feature changes are retained below. Entries are **median / p95 absolute** in feature units, in live-1 / live-2 / **holdout live-3** order:

| Candidate | Narrow feature change, 1/2/3 | Wide feature change, 1/2/3 | Repeated feature change, median / p95 / max in holdout |
| --- | --- | --- | --- |
| Production | .01670/.02099; .01660/.02383; .01870/.02169 | .00648/.01413; .01158/.01853; .00827/.01930 | .00563 / .01344 / .02183 |
| Lid midpoint | .00652/.00927; .00429/.00800; .00753/.01189 | .01199/.02287; .02559/.02965; .02359/.02659 | .00357 / .01394 / .01698 |
| Lid fraction | .10792/.66780; .17367/.56888; .21351/.37483 | .04982/.08189; .08514/.09788; .06719/.07881 | .02285 / .14302 / .17414 |

Mapped repeated-target median/p95/max for development live-1/2 were production `.0936/.2584/.2939` and `.1715/.5719/.6513`; midpoint `.1390/.4203/.5636` and `.0955/.5603/.6373`; fraction `.2570/3.3182/4.4652` and `.3006/4.7975/5.1451`. The holdout values are in the decision table. Fraction had very large tails despite no invalid apertures. No diagnostic presentation or outlier was removed.

Development repeated-target **feature** median/p95/max were production live-1 `.00321/.00887/.01008`, live-2 `.00536/.01787/.02035`; midpoint `.00354/.01071/.01436`, `.00268/.01573/.01789`; fraction `.02450/.31634/.42568`, `.02491/.39761/.42641`. These feature units differ across formulas, so the mapped counterparts above carry the operational comparison.

Holdout calibration feature spans were production `.017761`, midpoint `.010854`, fraction `.037672`; slopes were `+37.393`, `−34.512`, `−10.216`; calibration MAEs `.0818/.1894/.1889` and absolute residual p95s `.1527/.3494/.3479`. Unlike the mapped sample-noise metric, a raw slope alone cannot rank amplification across features with different units. The alternative calibration residuals and natural diagnostic errors both increased materially.

Holdout signed mapped-direction counts (positive/negative of condition−natural) were production narrow `9/0`, wide `8/1`; midpoint narrow `7/2`, wide `0/9`; fraction narrow `9/0`, wide `0/9`. The reversal in fitted slope and response direction is descriptive, not a corrected eye-opening relation.

## Monocular results

Separate left/right calibration fits preceded binocular averaging. Holdout values below are **left / right / binocular**:

| Candidate | Natural row ordering | Natural MAE | Narrow mapped median | Wide mapped median | Repeat mapped median |
| --- | --- | --- | --- | --- | --- |
| Production | yes / yes / yes | .0933/.1535/.1365 | .7292/.5576/.6993 | .3573/.2012/.3091 | .1786/.1970/.2105 |
| Lid midpoint | **no / no / no** | .2145/.2114/.2214 | .1850/.2768/.2599 | .6279/.7291/.8143 | .0937/.1246/.1233 |
| Lid fraction | **no / yes / no** | .2144/.2079/.2172 | 1.7126/2.1673/2.1813 | .5887/.6373/.6864 | .1792/.2451/.2335 |

The fraction's right eye alone retained ordered row medians in the holdout, but its natural MAE remained .2079 versus production right .1535, and its opening shifts were larger. Binocular averaging did not restore ordering and sometimes had higher error or shift than both single eyes after each was independently mapped. Development monocular midpoint/fraction outputs were also nonordered for **both eyes in both sessions**. The result is not hidden by binocular pooling, and it does not justify post-hoc eye selection.

For development, left/right natural MAE pairs (live-1; live-2) were production `.0818/.0834; .0905/.1412`, midpoint `.1789/.1929; .2050/.2712`, and fraction `.2835/.2345; .2331/.3222`. Their left/right median mapped narrow, wide, and repeat changes were:

| Candidate/session | Narrow L/R | Wide L/R | Repeated L/R |
| --- | --- | --- | --- |
| Production live-1 | .496/.437 | .151/.221 | .067/.072 |
| Midpoint live-1 | .262/.163 | .517/.308 | .189/.081 |
| Fraction live-1 | 1.603/.663 | .584/.331 | .272/.155 |
| Production live-2 | .363/.527 | .271/.340 | .133/.145 |
| Midpoint live-2 | .091/.233 | .574/1.306 | .077/.197 |
| Fraction live-2 | 1.206/3.136 | .700/1.318 | .168/.404 |

## Secondary historical check, after the holdout decision

The older `eye_geometry_decomposition` sessions have all needed iris/corner/lid primitives. They were not part of formula design or the live-3 eligibility rule. Their three-level subset compares comfortably narrow/wide with natural; the two slight levels remain in the files but are outside this matched cross-check.

| Historical candidate | Natural row order live-1/2/3 | Natural MAE live-1/2/3 | Narrow mapped median live-1/2/3 | Wide mapped median live-1/2/3 | Repeat mapped median live-1/2/3 |
| --- | --- | --- | --- | --- | --- |
| Production | yes/yes/yes | .0635/.0761/.1168 | .4867/.3251/.0662 | .5340/.2806/.4644 | .1233/.1382/.0473 |
| Lid midpoint | yes/**no/no** | .1550/.1537/.1671 | .1149/.2171/.0085 | .5074/**.5504**/.0262 | .0665/.1204/.0032 |
| Lid fraction | yes/**no/no** | .1715/.1651/.1644 | **.5811/.7955/.6272** | .2688/**.4068**/.4676 | .0928/.1457/.0711 |

Historical live-1 preserved row order for both candidates, unlike all primary development/holdout sessions; this is a **mixed** ordering detail. But its natural MAE was much worse than production, and historical live-2/3 lost ordering. Historical midpoint live-3's near-zero mapped shifts came with near-flat predicted rows `.499/.501/.499`, not improved gaze tracking. The secondary batch therefore supports the primary **no-winner** decision overall; it cannot reverse the failed held-out criteria.

## Supported conclusions, limitations, and project step

**Supported:** neither predeclared lid-referenced candidate passed the held-out six-part rule. Midpoint replacement trades better narrow/repeat metrics for worse wide-state behavior and lost gaze discrimination. Aperture normalization makes narrow-state sensitivity and tails especially large in the primary data. The current production feature has measured opening-state and repeated-target limitations, but remains the only one of these three that consistently retained natural gaze-row ordering in the primary sessions.

**Unsupported:** these feature comparisons do not identify anatomical eyelid or iris motion, prove true fixation, diagnose MediaPipe, establish cross-user behavior, or show that production is cursor-ready. Calibration and diagnostic presentations came from the same session. Live-3 was held out from **this round's** formula and rule selection, but its capture had already been analyzed for different candidates in the preceding benchmark; it is not an untouched new acquisition. The coarse face and lid landmarks remain detector estimates. The six sessions are from one participant, and repeated pairs share presentations. No causal or statistical-significance claim is made.

**Stop-rule decision:** **NO WINNER; end this bounded hand-crafted vertical-feature search.** Retain the production vertical feature for now with its documented errors. Return to the approved Phase 1 interaction/cursor-targeting roadmap using appropriately coarse targets and tolerances, and evaluate usability under those limitations. A future stronger pose model, learning approach, or multi-user model may be considered by the human team later; none is started or recommended as the immediate next experiment. No final baseline-versus-candidate live validation is justified by this holdout.
