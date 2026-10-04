# Offline benchmark of four vertical feature formulations

## Data, validation, and evaluation rule

The **primary** dataset comprises only `.venv/face-reference-cagri-live-{1,2,3}.json` (`face_reference_corner_stability`, protocol 1). The **secondary** historical check comprises only `.venv/eye-geometry-cagri-live-{1,2,3}.json` (`eye_geometry_decomposition`, protocol 1). All six belong to Çağrı, passed their existing strict protocol/sample-geometry validators, and contain ordinary nine-point calibration plus repeated upper/center/lower diagnostic presentations. The two protocols are reported separately. Protocol-invalid pilots and earlier eye-opening captures were not used. No new camera data were collected.

Four formulas were fixed before inspecting the benchmark outcomes; their exact geometry is in [README.md](README.md). For each formula, **only nine ordinary calibration presentation medians** fit its own ordinary least-squares `y = slope × feature + intercept`. References use only calibration frames. The production candidate reproduced every saved baseline calibration slope/intercept. All values below are recomputed from saved numerical rows, with no clipping or diagnostic-label tuning. Each session has nine natural diagnostic presentations and 27 matched natural-to-manipulated comparisons per condition across the three sessions. Repeated-target metrics use all three unordered block pairs for each target × condition (27 pairs per session). Unless a cell says otherwise, triples are **live-1 / live-2 / live-3**, not confidence intervals. All y values are normalized screen coordinates.

## Primary comparison: no candidate meets all requirements

| Candidate | Natural diagnostic y MAE, sessions 1/2/3 | Ordered gaze rows | Calibration y slope, 1/2/3 | Median abs mapped narrow shift, 1/2/3 | Median abs mapped wide shift, 1/2/3 | Median abs mapped block repeat, 1/2/3 | Deployable inputs | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Production baseline | .0838 / .1516 / .1365 | 3/3 | 29.14 / 32.00 / 37.39 | .4867 / .5312 / .6993 | .1888 / .3706 / .3091 | .0936 / .1715 / .2105 | Yes | Comparator |
| Face-normalized iris y | .3026 / .2945 / .2837 | **1/3** | +.303 / −.115 / −.170 | .3621 / .1687 / .2742 | .1069 / .0495 / .1229 | .1473 / .0765 / .1186 | Yes, with face anchors | Reject: gaze discrimination/accuracy fail |
| Calibration-stable span | .0920 / .1602 / .1342 | 3/3 | 28.68 / 30.50 / 36.54 | .4662 / .5308 / **.7580** | .1484 / .2598 / .2710 | .0927 / .1686 / .2096 | Yes | Partial wide benefit; no clear overall gain |
| Calibration-stable frame | .1090 / .1677 / .1211 | 3/3 | 28.33 / 30.69 / 34.95 | .4896 / **.5841 / .7670** | .1339 / .2441 / .2954 | .0950 / .1738 / .2056 | Yes | Partial wide benefit; narrow/repeat tradeoff |

The face-iris feature's small slope in sessions 2–3 is **not** a robustness victory: its natural upper/center/lower predicted medians are reversed there. Stable span improves the wide median by roughly **21% / 30% / 12%** versus production, and stable frame by **29% / 34% / 4%**. Neither lowers the narrow median in all three sessions; both change repeated-target mapped variation very little. Candidate selection cannot be based on the wide column alone.

## Natural gaze signal and calibration sensitivity

| Candidate | Natural predicted row medians, live-1 (U/C/L) | live-2 | live-3 | Adjacent margins U→C / C→L by session |
| --- | --- | --- | --- | --- |
| Production | .191 / .552 / .765 | .238 / .709 / .904 | .288 / .532 / .930 | .361/.213; .471/.195; .244/.398 |
| Face iris y | .009 / .297 / .386 | .628 / .423 / .332 | .781 / .579 / .474 | .288/.089; **−.205/−.092; −.202/−.104** |
| Stable span | .262 / .588 / .796 | .312 / .725 / .918 | .279 / .548 / .927 | .326/.208; .413/.193; .270/.379 |
| Stable frame | .273 / .608 / .832 | .306 / .744 / .922 | .261 / .522 / .900 | .336/.223; .438/.179; .261/.378 |

| Candidate | Calibration feature span, live-1/2/3 | Calibration y MAE, live-1/2/3 | Natural diagnostic median abs error, live-1/2/3 | Natural p95 abs error, live-1/2/3 | Natural signed bias, live-1/2/3 |
| --- | --- | --- | --- | --- | --- |
| Production | .021916 / .019255 / .017761 | .0334 / .1234 / .0818 | .0598 / .1541 / .1533 | .2002 / .2643 / .2645 | +.0094 / +.1052 / +.0774 |
| Face iris y (px) | 1.846987 / 1.887870 / 1.238362 | .1398 / .2116 / .2110 | .2406 / .3785 / .2757 | .6103 / .4646 / .5394 | −.3026 / −.0406 / +.1223 |
| Stable span | .021397 / .019212 / .018752 | .0292 / .1157 / .0769 | .0881 / .1678 / .1618 | .1968 / .2694 / .2550 | +.0523 / +.1314 / +.0796 |
| Stable frame | .021811 / .020039 / .019109 | .0289 / .1089 / .0848 | .1083 / .1600 / .1502 | .2103 / .2915 / .2371 | +.0729 / +.1383 / +.0590 |

Feature units differ: face iris y is **pixels** in the face template, while the other features are dimensionless. Compare mapped y, not raw feature differences across unlike units. A 0.001 feature change maps to .0291/.0320/.0374 y for production, .0287/.0305/.0365 for stable span, and .0283/.0307/.0349 for stable frame. The face-iris equivalent is .000303/−.000115/−.000170 y **per 0.001 px**; its nominal small slope does not rescue lost gaze discrimination. Span and frame stabilization did not materially flatten the fitted mapping.

## Matched eye-opening shifts and row dependence

In feature space, median **absolute** narrow shifts for production were `.016700/.016601/.018701`; stable span `.016254/.017400/.020746`; stable frame `.017285/.019033/.021947`; face iris y `1.196/1.473/1.614 px`. Wide shifts were production `.006478/.011582/.008267`; stable span `.005175/.008516/.007416`; stable frame `.004726/.007954/.008452`; face iris y `.353/.432/.723 px`. Mapped-y changes are in the primary table. This is an invariance comparison at the same displayed target and block, not an independent measurement of true gaze.

Mapped-y p95 **absolute** narrow shifts were production `.612/.763/.811`, stable span `.576/.704/.798`, stable frame `.595/.746/.817`, and face iris y `.635/.259/.383`. Wide p95 values were respectively production `.412/.593/.722`, stable span `.324/.490/.649`, stable frame `.302/.473/.592`, and face iris y `.169/.117/.177`. Production, stable span, and stable frame had positive mapped narrow deltas in **9/9 comparisons in each session**. Production wide was positive in **9/9, 8/9, 8/9**; stable span the same; stable frame **8/9, 7/9, 8/9**. The lower median/p95 wide movement of the alternatives does not erase their narrow failure.

| Candidate | Wide median abs mapped shift by row, live-1 U/C/L | live-2 U/C/L | live-3 U/C/L | Narrow live-3 U/C/L |
| --- | --- | --- | --- | --- |
| Production | .221/.210/.182 | .568/.371/.155 | .584/.309/.246 | .699/.803/.614 |
| Face iris y | .088/.136/.107 | .105/.013/.050 | .171/.123/.034 | .233/.277/.274 |
| Stable span | .148/.150/.148 | .460/.288/.104 | .487/.231/.204 | **.758/.775/.605** |
| Stable frame | .137/.134/.123 | .450/.254/.089 | .449/.186/.180 | **.767/.776/.615** |

Stable alternatives reduced wide shifts at all nine session/row medians, but narrowing in live-3 worsened at upper and center gaze. Wide production and alternative effects were usually largest at upper gaze in live-2/3. A single pooled number would hide this row dependence.

## Repeated target stability and left/right behavior

| Candidate | Median abs repeated feature difference, live-1/2/3 | Feature p95, 1/2/3 | Feature max, 1/2/3 | Repeated mapped-y p95, 1/2/3 | Repeated mapped-y max, 1/2/3 | Natural-only repeat mapped median, 1/2/3 |
| --- | --- | --- | --- | --- | --- | --- |
| Production | .003211/.005359/.005630 | .008865/.017873/.013442 | .010084/.020352/.021835 | .258/.572/.503 | .294/.651/.816 | .094/.134/.209 |
| Face iris y (px) | .486665/.668108/.698062 | 1.381276/1.785724/1.410898 | 1.954414/1.880696/1.663554 | .418/.205/.240 | .592/.215/.283 | .314/.064/.110 |
| Stable span | .003231/.005526/.005738 | .008878/.016856/.013093 | .009356/.018138/.023197 | .255/.514/.478 | .268/.553/.848 | .085/.108/.210 |
| Stable frame | .003354/.005665/.005882 | .009070/.015814/.012342 | .009971/.018034/.023112 | .257/.485/.431 | .282/.553/.808 | .089/.121/.206 |

Full repeated mapped medians are in the primary table. In live-3, stable span's **maximum worsened** from .816 to .848 even as its p95 improved. There is no consistent large improvement in the original same-target block-instability problem.

Each eye was fitted and evaluated independently before binocular averaging. All **left, right, and binocular** candidates except face iris y in live-2/3 retained natural U<C<L row ordering. Monocular natural MAEs (left/right, live-1/2/3) were: production `.082/.083; .091/.141; .093/.154`; stable span `.074/.107; .104/.166; .097/.146`; stable frame `.081/.136; .117/.156; .105/.128`; face iris y `.430/.172; .345/.186; .305/.260`. Monocular wide mapped medians were production left `.151/.271/.357` and right `.221/.340/.201`; stable span left `.117/.187/.270` and right `.178/.263/.220`; stable frame left `.107/.173/.261` and right `.146/.254/.188`. Monocular narrow medians remained substantial: stable span left `.450/.378/.698`, right `.437/.548/.590`; stable frame left `.481/.427/.740`, right `.398/.546/.556`. Left/right contributions are not interchangeable; binocular averaging did **not** consistently beat the best eye on natural MAE or repeatability, partly because each mapping is fitted independently. This does not validate choosing an eye after seeing diagnostics.

## Secondary historical validation: different protocol, same ranking concern

The older five-opening-level geometry captures contain all primitives for production, stable span, and stable frame, but **no broader-face anchors**. Face iris y is therefore **unsupported** and was not fabricated. The table uses only their natural, comfortably narrow, and comfortably wide presentations; the two slight conditions are retained in the files but are outside this matched three-condition cross-check. All candidates below preserved natural U<C<L ordering in all three secondary sessions.

| Candidate | Natural MAE live-1/2/3 | Narrow mapped median live-1/2/3 | Wide mapped median live-1/2/3 | Repeated mapped median live-1/2/3 | Calibration slope live-1/2/3 |
| --- | --- | --- | --- | --- | --- |
| Production | .0635/.0761/.1168 | .4867/.3251/.0662 | .5340/.2806/.4644 | .1233/.1382/.0473 | 24.36/23.38/16.34 |
| Stable span | .0506/.0771/.1038 | .4657/.3461/.0872 | .4421/.2186/**.5004** | .1089/.1295/**.0534** | 23.33/22.24/18.20 |
| Stable frame | .0525/.0792/.0965 | **.5001/.3906/.1136** | .4191/.2215/**.5062** | .0981/.1279/**.0553** | 22.74/21.94/18.28 |

The secondary batch confirms that fixed span/frame can help wide shifts in some sessions, but **worsen wide and narrow shifts in another** (live-3). Natural MAE sometimes improves there, unlike the primary batch; that variability is another reason not to promote a candidate from this benchmark. Secondary data are not a prospective independent-user validation.

## Supported conclusions, limits, and decision

**Supported:** the face-normalized absolute iris-y candidate is less affected by measured wide-state contrasts in mapped-y space, but it fails the essential gaze-separation test in two primary sessions and has much worse natural-target accuracy. Calibration-stable span/frame preserve gaze-row ordering and modestly improve the wide-condition median and p95 across the primary sessions. Their narrow and repeated-block behavior does not consistently improve; secondary historical sessions show additional reversals. None offers a convincing Pareto improvement over production. The production baseline itself remains sensitive to opening changes and block repetition.

**Unsupported:** the benchmark does not establish a root physical cause, that eye corners anatomically move, that face normalization removes 3D pose, that a stable-span/frame variant is production-ready, or that this participant's result generalizes to other users. Diagnostic target rows are displayed instructions, not independently verified fixation. Three sessions per protocol, one participant, shared landmarks and calibration, repeated target/eye measurements, and limited natural diagnostic points constrain inference. Calibration fit and evaluation use the same session, though the diagnostic samples are held out from fitting. No significance or causal claim is made.

**Decision:** **no candidate is ready for a final live production-vs-candidate validation.** The next bounded step should remain **offline**: design one or two equally interpretable gaze-reference alternatives that preserve local gaze-row separation while reducing the dynamic-corner dependency in both narrow and wide states, using only calibration and current-frame geometry. Predeclare the formulas before re-evaluating held-out sessions or a future new dataset; do not search coefficients against these diagnostic results. Do not resume root-cause eye-opening camera studies or modify production mapping based on this benchmark.
