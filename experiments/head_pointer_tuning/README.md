# Head pointer tuning on RAY — Issue #158

Preregistered **2026-11-28, Europe/Istanbul**, before any Issue #158 session.
Approved by Fatih in chat ("devam") after the Issue #156 result. Interaction
experiment; no change to the desktop demo, the OS cursor or the gaze code.
Rollback point: main `7fb4fe4`.

## Question

[Issue #156](../head_pointer/RESULTS.md) chose **RAY** (where the head's forward
axis meets the camera plane). The cursor reached targets in about 1.9 s, but
steadiness was the bottleneck: hold jitter was about 7 px RMS, there were about
2 entries per target, and 30 px targets took about 4.5–4.8 s. The full screen
also needed about 36° of yaw. **Does a steadier filter, alone or with a higher
gain, make RAY pointing faster and more comfortable than the #156 settings?**

## Conditions

All three use RAY and one shared calibration per session:

| Name | One Euro min cutoff | β | Gain |
| --- | --- | --- | --- |
| **BASE** | 1.0 Hz | 0.01 | 1.0 (Issue #156 settings, control) |
| **STEADY** | 0.3 Hz | 0.03 | 1.0 |
| **STEADY_GAIN** | 0.3 Hz | 0.03 | 1.5 |

- **STEADY** smooths more at rest (time constant about 0.53 s instead of about
  0.16 s). Its larger β keeps fast movement responsive.
- **Gain** scales the calibrated mapping around the screen centre:
  `0.5 + gain × (mapping − 0.5) + offset`. A gain of 1.5 needs about
  two-thirds of the head movement, and it also amplifies jitter by 1.5.
- These constants were chosen from the #156 numbers before any #158 session.
  They were not tuned on data.

## Session flow (`run.py`)

The flow is the same as Issue #156 (built-in display 1512×982, built-in camera
index 0, 9-dot "point your nose" calibration, OLS per axis), with these changes:

- The blocks are labelled "Ayar 1/2/3". Order: session A BASE → STEADY →
  STEADY_GAIN, session B the reverse.
- Each block has 4 unscored practice targets, then 16 scored targets:
  8 directions × 30/60 px, 0.8 s dwell, 8 s timeout. The filter and offset are
  reset at the start of each block.
- **Recentring:** pressing `r` makes the current head pose the screen centre
  (offset only, gain unchanged) and resets the filter. It is allowed in every
  condition, and its use is counted per block.
- **Comfort:** after each block, Fatih presses 1–5 (1 very tiring, 5 very
  comfortable). This is descriptive only.
- Session A, reseat, then session B.

```bash
PY=~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python
PYTHONPATH=src:. $PY -m experiments.head_pointer_tuning.run --participant fatih --session A \
  --camera-index 0 --screen-size 1512x982 --output .venv/head-pointer-tuning-fatih-A.json
# reseat, then --session B --output .venv/head-pointer-tuning-fatih-B.json
PYTHONPATH=src:. $PY -m experiments.head_pointer_tuning.analysis \
  .venv/head-pointer-tuning-fatih-A.json .venv/head-pointer-tuning-fatih-B.json
```

What is saved locally in `.venv/` (Git-ignored): the same numeric records as
#156, plus the conditions, comfort ratings, recentre counts and a per-frame
`recentred` flag. No images or landmark sets are saved.

## Frozen rule (asserted by tests)

This is the #156 rule, unchanged, applied to the three conditions:

- A condition **passes** with at most one timeout among its 16 scored trials
  in **each** session.
- The **winner** has the lowest pooled median selection time.
- If another condition is within **5 %** of that time, the lower median hold
  jitter decides.
- **If BASE wins or nothing passes, no tuning is adopted.**

Descriptive only: time by target size, entries, comfort, recentres.

## Limits

One participant, two short sessions, one camera and display. The comfort
rating is a single subjective number per block. Recentring is optional, so
its use may differ between conditions. Fatigue over longer use is not
measured. No OS pointer is moved and nothing is clicked.
