# Issue #52 — Vertical position and repeat variability

## Question and boundary

At a fixed screen Y, does the existing binocular local-axis vertical feature vary with horizontal target position? Does it change when the **identical target** is presented again later? This is a Phase 1 diagnostic, not a change to feature extraction, calibration, or mapping. The [Issue #50 results](../vertical_mapping_evaluation/RESULTS.md) improved calibration fit with row anchors but worsened held-out vertical error, so they do not justify a production mapping change.

## Offline-first analysis

Analyze the existing local, Git-ignored derived-numerical datasets before any camera run:

```bash
PYTHONPATH=src .venv/bin/python -m experiments.vertical_position_variability.report \
  .venv/vertical-collapse-cagri-A.json .venv/vertical-collapse-cagri-B.json \
  .venv/vertical-drift-cagri-A.json .venv/vertical-drift-cagri-B.json
```

The analyzer groups **usable frames by presentation** before comparing target locations. It reports each presentation's median and IQR, then compares vertical feature medians for different X positions at the same Y *within one phase and session*. For the controlled run it also reports pass 1 and pass 2 separately, preserving the actual X presentation order. It reports later-minus-earlier median differences for each repeated identical target separately, including the five CENTER checkpoints where present. Rows from another participant/session are rejected rather than pooled. Left/right eye, horizontal, eye-opening, and coarse face-center-Y numerical summaries remain diagnostics only. Each session's already-fitted independent-linear vertical slope converts feature differences into illustrative normalized-Y output differences; no correction is applied.

The old calibration grid was always collected top-to-bottom and left-to-right within each row. Its X and time order are therefore confounded. The old held-out sequence was shuffled but identically ordered across sessions; each of eight positions was shown twice, with five extra CENTER checkpoints in the drift sessions. The analyzer flags a same-Y X comparison as order-confounded when each X group's presentation times lie entirely before the next group's times (or entirely after, in reverse). This flag identifies an order limitation, not proof of a time trend. The Experiment 006 numerical CSV has comparable grid/repeat fields but an **experimental blink gate** absent from current production. It is context, not pooled with the four production-derived JSON runs.

## Conditional balanced human protocol

The offline results in [RESULTS.md](RESULTS.md) show repeated-target changes but do not separate a horizontal-position effect from order/elapsed-time effects. The smallest additional collection therefore reuses the existing production Vision and Gaze math and the validation-only target window:

1. Fresh nine-target calibration on the established 3×3 grid, using the existing per-target median aggregator and session fitter.
2. One diagnostic pass over those nine coordinates: top, middle, bottom rows; left, center, right within each row.
3. A second pass over the **same** nine coordinates in the exact reverse order. Thus every coordinate is revisited later and X order reverses in each Y row.

All 27 presentations use the existing validation timing: 0.8 seconds settling, then 1.2 seconds sampling, with at least five usable frames per presentation. The run should take about 54 seconds plus startup/processing overhead. The reversed order reduces—but does not eliminate—time/order confounding. It is deterministic and short; it does not introduce randomized parameter search or new gaze math. No held-out gaze-accuracy claim follows from these repeated diagnostic targets.

For Çağrı's development Mac, with the existing model and camera index 1:

```bash
PYTHONPATH=src .venv/bin/python -m experiments.vertical_position_variability.run \
  --participant cagri --session controlled-1 --camera-index 1 \
  --output .venv/vertical-position-cagri-controlled-1.json
```

Then analyze that local file with the `report` command above, substituting its path. The output path must be new and inside Git-ignored `.venv/`; the script refuses to overwrite it. Camera index remains an explicit runtime choice because device ordering can change. Use normal comfortable posture, natural eye opening and blinking, approximately stable head, and normal glasses use. Look at each dot; do **not** deliberately change eye opening, head/camera angle, or posture to improve a result. Press `q` or Esc to cancel; incomplete runs save no dataset.

## Measurements and interpretation

Compare same-Y left/center/right vertical medians and within-presentation IQRs, then the two presentations of each identical target. Examine whether the positional pattern repeats despite reversed collection order, and whether repeated-target changes are comparable to between-position differences. Record left/right eye values, horizontal feature behavior, eye opening, and coarse face-center-Y changes where available. The head proxy cannot distinguish pitch from translation; associations do not establish causes. No hard pass/fail threshold or statistical-significance claim is defined from these exploratory single-user runs.

The run stores only derived numerical features, target metadata, availability, timing, and the session mapping coefficients. It does **not** save camera frames, facial images, screenshots, or video. Treat numerical features as potentially sensitive and do not commit human data. The separate MediaPipe outbound-telemetry question remains unresolved; local harness behavior alone cannot rule it out. Unlike Experiment 006, the production path has no validated blink filter, so its experimental blink gate is not used here.

See [RESULTS.md](RESULTS.md) for measured offline evidence, any controlled-run outcome, limitations, and the final bounded classification.
