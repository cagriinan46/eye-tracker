# Camera placement and vertical signals — Issue #88

Preregistered **2026-10-13, Europe/Istanbul**, before any Issue #88 session.
Approved by Fatih in chat ("1–4 tamam"). Diagnostic experiment; no production
change.

## Question

[Issue #86](../../docs/research/iphone-arkit-signal-check.md) found no better
vertical signal from iPhone ARKit. A remaining hypothesis is camera placement:
the built-in camera sits above the screen and looks down at the eyes, so the
upper lid may hide vertical iris movement. **Does an iPhone used as an ordinary
Continuity Camera (rear camera) below the screen improve the existing
pipeline's vertical signals versus the built-in camera, on the same day and in
the same conditions?** Frames are processed on the Mac by the existing
MediaPipe pipeline; this is a standard-camera test, not ARKit.

## Protocol

The [Issue #77 collector and frozen analysis](../vertical_signal_comparison/README.md)
are reused **unchanged**: 50 presentations ≈ 100 s (checkpoints, shuffled 5×5
calibration at 0.1–0.9, shuffled 4×4 validation at 0.2–0.8, seed 77), 0.8 s
settling, 1.2 s sampling, blink ≤ 0.5 common frames, candidates R0 / OPEN /
OPEN_Q / BLEND / COMBO, per-session pass y MAE ≤ 0.08, ordering ≥ 19/21 and
|bias| ≤ 0.05, session validity ≥ 20/25 calibration and ≥ 14/16 validation
presentations. The only code change lets `run.py` also write to the Git-ignored
`validation/results/` directory.

Four sessions, Fatih only, full screen 1512×982, `.venv-fatih`, reseating
between sessions, results not shown between sessions:

| Order | Participant ID | Session | Camera |
| --- | --- | --- | --- |
| 1 | `fatih-builtin` | A | built-in, above screen |
| 2 | `fatih-iphone` | A | iPhone rear camera via Continuity Camera, landscape on a stand below the screen |
| 3 | `fatih-iphone` | B | same |
| 4 | `fatih-builtin` | B | built-in |

The ABBA order balances fatigue and lighting drift. Center Stage, Portrait,
Studio Light and other macOS video effects must be off for the iPhone camera
(Center Stage crops and zooms dynamically). The iPhone's OpenCV index is found
by a no-save smoke test before session 1 and recorded. Model:
`.venv-fatih/models/face_landmarker.task`, downloaded from the official
MediaPipe URL, SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`,
identical to the DATA_INVENTORY record; Çağrı's `.venv/` is not read.

```bash
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_signal_comparison.run \
  --participant fatih-builtin --session A --camera-index 0 --screen-size 1512x982 \
  --model .venv-fatih/models/face_landmarker.task \
  --output validation/results/camera-placement-fatih-builtin-A.json
# then fatih-iphone A, fatih-iphone B (iPhone index), fatih-builtin B
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_signal_comparison.analysis \
  validation/results/camera-placement-fatih-builtin-A.json validation/results/camera-placement-fatih-builtin-B.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_signal_comparison.analysis \
  validation/results/camera-placement-fatih-iphone-A.json validation/results/camera-placement-fatih-iphone-B.json
```

## Preregistered decision

Per camera, the Issue #77 `combine` ranking gives each candidate's mean y MAE
over that camera's two sessions; the **best candidate** is the first ranked one.

- **Vertical solved (iPhone placement):** the iPhone pair has a #77 winner, i.e.
  some candidate passes all thresholds in both iPhone sessions.
- **iPhone placement better:** all four sessions are valid and the best iPhone
  candidate's mean y MAE ≤ the best built-in candidate's mean y MAE − **0.02**.
- Anything else is **negative** for placement. If any session is invalid, the
  result is **inconclusive** for that comparison; no session is repeated or
  replaced after its data are seen.

Descriptive only: per-candidate metrics, calibration R², x MAE, checkpoint
drift, camera resolution, detector latency and frame counts.

## Interpretation boundaries

One person, one day, one location; the iPhone differs from the built-in camera
in position **and** sensor, lens and resolution, so a difference cannot be
assigned to placement alone. A positive result would justify a Çağrı session
and a human decision; it changes no production behavior. A negative result is
recorded results-only and this experiment's code is not merged (Fatih's rule).
