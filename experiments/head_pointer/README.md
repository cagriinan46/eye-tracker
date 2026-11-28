# Head pointer: which head signal makes the best cursor? — Issue #156

Preregistered **2026-11-28, Europe/Istanbul**, before any Issue #156 session.
Approved by Fatih in chat: he wants cursor control by head movement, reliable
first, with eye-based clicking only afterwards. He asked whether the nose is the
right point and wanted the options tried. Interaction experiment; no change to
the desktop demo, the OS cursor or the gaze code. Rollback point: main `df30ec9`.

Making the head the primary pointer changes the product's central input method
(Issue #84's open decision). Fatih decided to pursue it; Çağrı may revise it.

## Question

[Issue #84](../head_vertical_targeting/RESULTS.md) showed that head yaw/pitch
gives reliable **coarse** selection (3×3/4×4 cells). Continuous pointing at
small targets, smoothness and the choice of head signal were not tested.
**Which head signal gives the fastest reliable continuous pointer: the nose
tip's image position, the head's rotation angles, or the head's forward ray?**

## Candidates

All three are computed from the same Face Landmarker result for every frame
(`signals.py`):

| Name | Signal | Moves with |
| --- | --- | --- |
| **NOSE** | image-normalized nose-tip landmark (index 1) | translation and rotation |
| **ANGLES** | yaw/pitch (°) of the facial transformation matrix, Issue #77/#84 convention | rotation only |
| **RAY** | where the matrix's forward (+z) axis meets the camera plane z = 0 | rotation and position |

## Session flow (`run.py`)

Full-screen OpenCV window (`--screen-size` required), MediaPipe 0.10.35 Face
Landmarker, local model file.

1. **Shared calibration:** a 3×3 grid at 0.1/0.5/0.9, shuffled (seed 156).
   Each dot gets 0.8 s settling and 1.0 s sampling. Instruction: point the nose
   at the dot. For each candidate and axis, an OLS line maps the
   per-presentation median signal to the screen coordinate. A candidate needs
   at least 5 frames at at least 7 of the 9 dots. All candidates are fitted on
   the same frames. A candidate that cannot be fitted scores all its trials as
   failures.
2. **One target block per candidate.** The on-screen label is "Aday 1/2/3" (no
   candidate name). Order: session A NOSE → ANGLES → RAY, session B the reverse.
   Each block has 4 unscored practice targets (60 px), then 16 scored targets:
   8 directions on an ellipse (radii 0.40 W, 0.38 H from the centre) × diameters
   30 and 60 logical px. The order is shuffled and the same position never
   comes twice in a row. The cursor is the candidate's mapping, clamped to the
   screen and passed through the **same One Euro filter** (min cutoff 1.0 Hz,
   β 0.01, d-cutoff 1.0 Hz, restart after a 0.5 s gap). **0.8 s** of contiguous
   dwell inside the circle selects. Leaving the circle or losing the face
   restarts the dwell. Timeout is **8 s**, followed by 0.4 s of feedback. The
   filter is reset at the start of each block.
3. Session A, stand up and reseat, then session B.

```bash
PY=~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python
PYTHONPATH=src:. $PY -m experiments.head_pointer.run --participant fatih --session A \
  --camera-index 0 --screen-size 1512x982 --output .venv/head-pointer-fatih-A.json
# reseat, then --session B --output .venv/head-pointer-fatih-B.json
PYTHONPATH=src:. $PY -m experiments.head_pointer.analysis \
  .venv/head-pointer-fatih-A.json .venv/head-pointer-fatih-B.json
```

Saved locally in the Git-ignored `.venv/`: calibration rows and per-frame rows
with the three candidate signals (one nose-tip coordinate pair, angles, ray
point), raw and filtered cursor pixels, trial outcomes, mappings and constants.
No images, video or full landmark sets are saved.

## Frozen winner rule (asserted by tests)

- A candidate **passes** if it has **at most one timeout among its 16 scored
  trials in each session**.
- The **winner** is the passing candidate with the lowest median selection time
  over both sessions' selected scored trials (the time includes the 0.8 s
  dwell).
- If a passing candidate's median time is within **5 %** of the fastest, the
  lowest median hold jitter among them wins. Hold jitter is the RMS distance of
  the filtered cursor from its mean during the selecting dwell.
- If no candidate passes, there is **no winner**, and that is reported.

Descriptive only: median time by target size, median entries before
selection (overshoot), failed reads and no-face frames.

## What happens next

The winner becomes the signal for the next tuning step: gain, filter and
recentring on the winner alone. After that, integration into desktop control
needs a separate approval. Constants are not changed after outcomes are seen;
any new constants are a new, separately recorded run.

## Limits

One participant. Short sessions; comfort and fatigue are not measured. Head
pose comes from MediaPipe's matrix, not a validated head tracker. The filter
constants were chosen before any data, not tuned. A candidate that suits a
lower filter or a different gain may be disadvantaged. The fit is per axis
without cross terms. No OS pointer is moved and nothing is clicked.
