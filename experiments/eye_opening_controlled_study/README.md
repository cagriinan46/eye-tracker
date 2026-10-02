# Controlled eye-opening diagnostic — preregistered Stage 1

The three preregistered sessions are complete; measured findings and the separately labeled notification sensitivity are in [RESULTS.md](RESULTS.md). The protocol below is preserved as declared before collection.

## Question and boundary

At a **known, fixed target**, does a comfortable change in measured eye opening repeatedly accompany a change in the vertical eye feature? Does the response differ between upper, center, and lower gaze? The prior [covariate analysis](../vertical_feature_covariates/RESULTS.md) found a positive signed opening association in three same-participant sessions, but that observational result does not establish a cause. This study collects fresh data to isolate the opening instruction while retaining head-center and both monocular features. It makes no production correction or quality rule.

## Fixed human protocol

Participant: `cagri`. Collect exactly three complete fresh sessions, `live-1`, `live-2`, `live-3`. Each session starts with **one fresh standard nine-target 3×3 calibration** under natural comfortable opening. It then has **27 diagnostic presentations**: three targets at `(0.5, 0.25)` upper, `(0.5, 0.50)` center, `(0.5, 0.75)` lower; three conditions; and three blocks. Each block visits every target and each opening condition once. There are **36 presentations per session**, 0.8 s settling plus 1.2 s sampling each, for at least 72 s of presentation time plus camera/model startup and processing. At least five usable sampling frames are required per presentation. The calibration is only for secondary mapped-y context; there is no CENTER offset, trial-derived tuning, new mapping, correction, smoothing, clipping, blink gate, or threshold.

The deterministic order is set in [`protocol.py`](protocol.py). After the row-major nine-point calibration, block `b` (1–3) visits the three diagnostic rows in cyclic order starting at row index `b−1`. At each row it displays the three conditions consecutively in cyclic order starting at index `(b−1 + row_index) mod 3` of `(narrow, natural, wide)`. Thus every row receives all three conditions in each block, condition position rotates across blocks, and the block/condition schedule is fixed before measurements. Trial order is not changed after observing data.

The full-screen window shows the dot, current condition (`NATURAL`, `GENTLY NARROW`, or `COMFORTABLY WIDE`), settle/sampling state, and instructions. Keep looking at the dot. For **natural**, use normal comfortable opening; for **narrow**, gently narrow the eyelids without a hard squint; for **wide**, open somewhat wider than natural without stretching maximally. Comfort takes priority: do not strain, and do not intentionally move the head. Natural blinking is allowed. Press `q` or Esc to abort at any time. Predictions and numerical results are not shown. Use the same practical camera arrangement across sessions, and record any protocol deviation.

Run from the repository root; camera index 1 matches previous Çağrı sessions, but use the actual working index if it differs:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.eye_opening_controlled_study.run --participant cagri --session live-1 --camera-index 1 --output .venv/eye-opening-cagri-live-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.eye_opening_controlled_study.run --participant cagri --session live-2 --camera-index 1 --output .venv/eye-opening-cagri-live-2.json
PYTHONPATH=src:. .venv/bin/python -m experiments.eye_opening_controlled_study.run --participant cagri --session live-3 --camera-index 1 --output .venv/eye-opening-cagri-live-3.json
```

Only derived numerical observations are saved under Git-ignored `.venv`; no raw image or video is saved. Each sampling row records participant/session, phase, target identity and coordinates, opening condition, block, order, timestamp and monotonic time, usable/unavailable status, binocular and per-eye vertical features, horizontal feature, per-eye and binocular opening, head-center y, and mapped prediction when available. The report also saves presentation counts and vertical medians, calibration coefficients, camera index/resolution, camera reads/failures, no-face counts, timing, and elapsed time. Existing reports are never overwritten.

**Invalid-run policy:** all complete technically valid sessions are retained, including inconvenient results. Retry only after abort, too few usable samples, camera failure, corrupt output, or explicit protocol failure, and record the reason. An invalid attempt writes a separate `.invalid.json` marker and any justified retry needs a distinct output filename; do not replace the marker. The inherited presentation collector cannot retain partial measurements after an exception, so the marker states that limitation.

## Analysis declared before capture

Run the analyzer on all three completed reports; its full precision JSON output contains every presentation median and every fixed-target block contrast:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.eye_opening_controlled_study.analysis .venv/eye-opening-cagri-live-1.json .venv/eye-opening-cagri-live-2.json .venv/eye-opening-cagri-live-3.json
```

The analyzer checks the fixed 36-presentation schedule, coordinates, condition labels, raw usable/unavailable counts, saved binocular medians, and the per-frame binocular = mean-of-two-eyes identity wherever both monocular values exist. For **each** presentation it takes the median of actual usable numerical samples **separately per field**; missing optional fields remain missing. It also reports within-presentation `p95 − p05` spread using linear interpolation. The median of per-frame binocular means need not equal the mean of two separately computed medians; this residual is reported, and no monocular reconstruction replaces the recorded binocular median.

**Manipulation check comes first:** for each session and target row, report three block-presentation medians of measured binocular opening by condition, their across-block medians and ranges, median within-presentation spread, the `narrow < natural < wide` median order, and count of blocks with that order. Report signed pairwise opening separations, whether the ranges of the three block medians overlap (touching counts as overlap), and the within-presentation spread. There is deliberately **no post hoc success threshold**; weak separation or overlap must be described plainly.

**Primary feature comparisons:** within each block at the **same target**, calculate `narrow − natural`, `wide − natural`, and `wide − narrow`. Each comparison records signed and absolute binocular vertical change, signed left/right vertical changes, binocular opening change, head-center-y change, per-eye opening changes, common mode `(Δleft + Δright)/2`, differential `Δleft − Δright`, same/opposite monocular direction, and secondary `y_slope × Δbinocular_vertical` without clipping. The full pair records preserve block-level scatter-friendly numbers; per-session/row summaries report medians and maximum absolute head-center change. No comparison crosses target rows or sessions.

**Directional consistency:** for each session and row, count the blocks where wide has greater *measured* opening than natural and, among those, counts of positive, negative, and zero `wide − natural` vertical change. This does not choose a favorable direction afterward. When a block's measured opening is ordered `narrow < natural < wide`, report whether its feature is strictly increasing or decreasing in that same order. Count same-direction and opposite-direction monocular changes for each condition contrast. Report head-center differences alongside feature differences as a possible confound, not a causal explanation.

The analysis is descriptive. Three sessions from one participant cannot establish an eyelid or detector mechanism, independent fixation, causality, a validated correction, cross-user reliability, production quality, or cursor readiness. Eye opening and the vertical feature use related landmarks; head-center y is a coarse image-coordinate proxy. Presentation order and elapsed time remain possible influences despite the balanced rotation. No final `RESULTS.md` will be written until real sessions exist.
