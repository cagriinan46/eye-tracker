# Head-assisted pointing: head pitch for vertical — Issue #84

Preregistered **2026-10-08, Europe/Istanbul**, before any Issue #84 session.
Approved by Fatih in chat ("dikey ekseni baş hareketine baglı yapsak ... bunu
da bir deneme gibi yapalım"). Interaction experiment; no production change.
Rollback point: main `2f73004fe5a1aab71da32049d13cf08eb24c4d29`. Per Fatih's
preference, the code is merged only if the experiment works and he decides so;
otherwise only a results record goes to main.

## Question

Eye-only vertical failed in [Issue #77](../vertical_signal_comparison/RESULTS.md)
and live zone targeting with eye-based COMBO failed in
[Issue #81](../../docs/research/coarse-zone-targeting-results.md), where Fatih
also felt a left-right "mirror" effect, plausibly from head rotation acting on
eye-in-head features. **Does using head pitch for the vertical axis make zone
selection reliable, either with eyes for horizontal (HYBRID) or with head yaw
for horizontal (HEAD, a full head pointer)?**

## Session flow

Full screen only (`--screen-size` required), camera index 0, `.venv-fatih`.

1. **Calibration**, 15 presentations (0.8 s settling, 1.2 s sampling, at least
   five usable frames each), in three blocks with the order shuffled inside
   each block (seed 84):
   - `eye_x`: 5 columns at y = 0.5, x 0.1–0.9. Instruction: keep the head
     still and look at the dot.
   - `head_y`: 5 rows at x = 0.5, y 0.1–0.9. Instruction: point your nose at
     the dot.
   - `head_x`: 5 columns at y = 0.5. Instruction: point your nose at the dot.
2. **Lines:** for each block, OLS of the screen coordinate on the per-presentation
   median of its feature: production binocular horizontal (eye_x), head pitch
   from the facial transformation matrix (head_y), head yaw (head_x). Each
   block needs at least 4/5 presentations, otherwise the session fails. Eye
   frames with eyeBlink > 0.5 are excluded; head-pose frames are not
   blink-filtered.
3. **Zone trials**, identical in mechanics to Issue #81: mirrored-cell cue
   0.75 s; target cell outlined; current cell shaded; median of the last 7
   valid estimates within 0.5 s; **1.0 s** on any cell selects it; **5.0 s**
   timeout; 0.5 s feedback. Each condition runs 3×3 then 4×4, each cell once
   (25 trials), for 50 trials per session.
   - **HYBRID:** x = eye_x line(horizontal), y = head_y line(pitch).
   - **HEAD:** x = head_x line(yaw), y = head_y line(pitch).
   Session A runs HYBRID then HEAD; Session B runs HEAD then HYBRID. The
   smoother is reset when the condition changes.

Fatih completes Session A, stands up and reseats, then Session B. The
on-screen hint names the current condition.

```bash
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.head_vertical_targeting.run \
  --participant fatih --session A --camera-index 0 --screen-size 1512x982 \
  --output .venv/head-vertical-fatih-A.json
# reseat, then the same with --session B and .venv/head-vertical-fatih-B.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.head_vertical_targeting.analysis \
  .venv/head-vertical-fatih-A.json .venv/head-vertical-fatih-B.json
```

Saved data (Git-ignored): calibration rows and per-frame target data with
status, production horizontal and vertical features, eye opening,
head-center-y, head pitch/yaw/roll, blink scores and detector time, plus raw
and smoothed estimates, cells, lines and outcomes. Logging head and eye values
per frame closes the Issue #81 diagnostic gap. No landmarks, images or video.

## Frozen pass rule

For each condition × layout and session: **success ≥ 80%** and **wrong
selections ≤ 10%**. A cell of the table passes only if **both** sessions pass.
Constants are asserted by tests. Descriptive only: timeout rate, median time to
success, success by row, wrong-selection offsets.

## Limits

One participant, one evening. Head pointing needs sustained neck movement:
fatigue, comfort and suitability for target users with limited head control
are **not** evaluated. Head pose comes from MediaPipe's transformation matrix
(Euler convention documented in the Issue #77 capture code), not a validated
head tracker. No OS pointer is moved and nothing is clicked.
