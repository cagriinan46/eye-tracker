# Coarse zone targeting with COMBO vertical — Issue #81

Preregistered **2026-10-08, Europe/Istanbul**, before any Issue #81 session.
Approved by Fatih in chat ("3 numarayı bir deneyelim ama eski haline de
dönebilelim"). Interaction experiment; no production change.

## Question and reversibility

[Issue #77](../vertical_signal_comparison/RESULTS.md) found no vertical signal
accurate enough for fine pointing; the best (COMBO) had about 0.10 normalized y
error. [Issue #79](../../docs/research/appearance-gaze-options.md) proposed
designing around coarse vertical accuracy. **Can Fatih reliably select
screen-filling zones on 3×3 and 4×4 grids with live COMBO, with few wrong
selections?** The accepted exit criteria include "coarse 3×3 targeting ≥ 80%".

Everything lives in this folder and its tests; `src/` is untouched. Rollback
point: main `9e55af69691d3dc1463aec34bfa5aba83fff4029`. To return to it, do not
merge the PR, or `git revert` its squash commit.

## Session flow

Full screen only (`--screen-size` required), camera index 0, `.venv-fatih`.

1. **Calibration:** the Issue #77 5×5 grid (0.1–0.9), shuffled (seed 81),
   0.8 s settling + 1.2 s sampling, at least five usable frames each.
2. **Live mapping**, fitted once from calibration presentation medians using the
   Issue #77 common-frame and blink rules (eyeBlink > 0.5 excluded): y from
   COMBO (production vertical, eye opening, blendshape `lookDown − lookUp`,
   head pitch); x from the production horizontal feature. At least 20/25
   calibration presentations are required, otherwise the session fails.
3. **Zone trials**, 34 per session. 3×3: each cell twice (18). 4×4: each cell
   once (16). Order within a layout is shuffled (seed 81 + session). Session A
   runs 3×3 then 4×4; Session B runs 4×4 then 3×3.
   - **Cue (0.75 s):** a grey dot in the mirrored cell (the center cell cues the
     top-left), so every trial requires a gaze shift. Nothing is judged.
   - **Target:** the target cell is outlined in orange with a dot. The cell under
     the current estimate is shaded as feedback, and a ring shows dwell progress.
   - **Estimate:** median of the last 7 valid frame estimates no older than
     0.5 s (so short blinks do not drop the estimate); points beyond the screen
     clamp to the edge cell.
   - **Selection:** whichever cell stays under the estimate continuously for
     **1.0 s** is selected. Target cell = success, other cell = **wrong
     selection**, nothing within **5.0 s** = timeout. A 0.5 s feedback follows.

Fatih completes Session A, stands up and reseats, then Session B. He should look
at the target naturally and may correct his gaze using the shaded feedback, as
a user would.

```bash
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.coarse_vertical_targeting.run \
  --participant fatih --session A --camera-index 0 --screen-size 1512x982 \
  --output .venv/coarse-vertical-fatih-A.json
# reseat, then the same with --session B and .venv/coarse-vertical-fatih-B.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.coarse_vertical_targeting.analysis \
  .venv/coarse-vertical-fatih-A.json .venv/coarse-vertical-fatih-B.json
```

Saved data: mapping coefficients, trial outcomes, and per-frame raw and smoothed
estimates, cell and blink score during targets. No landmarks, images or video.

## Frozen pass rule

Per layout and session: **success rate ≥ 80%** and **wrong-selection rate ≤ 10%**.
A layout passes only if **both** sessions pass. Constants are asserted by tests.
Descriptive only: timeout rate, median time to a successful selection, success
by target row, row offsets of wrong selections.

## Differences from earlier targeting studies

[Intentional v2](../intentional_gaze_targeting/README.md) used the production R0
estimator without smoothing, 0.20 × 0.20 targets with gaps, a cursor marker, a
1200×700 canvas and only target-region dwell. Here the grid fills the full
screen, the estimate is smoothed COMBO, any cell can be selected (so wrong
selections are measured), and feedback is a shaded cell. Results are not
directly comparable.

## Limits

One participant, one evening, two sessions; closed-loop feedback lets the user
compensate for bias, which suits the product question but not a pure accuracy
question. Dwell, smoothing and the 80%/10% thresholds are engineering choices.
No OS pointer is moved and nothing is clicked.
