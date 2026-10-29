# ADR-006 — UniGaze as the primary development gaze model

## Status

Accepted by the human project owner on 2026-10-29.

This selects the primary development model. It does not declare a completed
assistive system or claim that desktop integration is already implemented.

## Decision

Use UniGaze as the primary model for subsequent gaze development. Preserve
MGazeNet as the comparison baseline and explicit rollback option, including its
code, weights, environments, calibration behavior and historical measurements.
Continue evaluating new techniques against MGaze on the same frames with separate
personal calibrations. Do not silently substitute MGaze when UniGaze fails.

The initial operating condition is a comfortable, approximately stable posture
matching the personal calibration. Head-position robustness remains an open
development problem, rather than a prerequisite for selecting UniGaze as primary.
This condition is not a claim that all target users can maintain a fixed posture
or have identical movement capabilities.

## Evidence and rationale

Four same-day normal-posture comparisons favored UniGaze in equal-target mean
error on eight targets not used for training. Both branches used the existing
HeuristicFilter, not a Kalman filter. Lower values are better:

| Local session suffix | MGaze filtered error, px | UniGaze filtered error, px |
| --- | ---: | ---: |
| paired-unseen-c3275f969f8a | 71.75 | 46.17 |
| paired-unseen-d069108b792e | 112.00 | 35.74 |
| posture-8e67745ab828, normal block | 65.29 | 35.58 |
| posture-ddd92abcda8c, normal block | 80.44 | 39.49 |

These are one participant's local research results, not population validation.
The research calibration used 13 targets and 20 jointly valid frames per target;
MGaze used original 258 features and unstandardized Ridge alpha 0.1, while UniGaze
used two camera-frame angles and separately standardized Ridge alpha 0.1.
Reports and replay audits remain locally in `validation/results/unigaze-*`;
raw camera imagery is not part of the committed evidence.

The tilt session showed filtered errors of 468.79 px for MGaze and 97.38 px for
UniGaze after approximately 18.70 degrees of estimated head rotation. However,
the subsequent lateral-translation session showed 159.79 px for MGaze and
330.11 px for UniGaze. All eight translated targets favored MGaze. In that
session the observed face center moved about 58 image pixels with only 2.92
degrees of estimated rotation. These geometry estimates are not physical motion
measurements. Return to the original posture substantially reduced the error.

The human owner accepts this known limitation while prioritizing the repeated
normal-posture accuracy improvement. Keeping MGaze primary until all movement
conditions improve was considered and rejected for this development stage.
Removing MGaze was explicitly rejected.

## Consequences and implementation boundary

- UniGaze is the primary development direction; MGaze remains available for
  comparison and rollback. Fresh calibration is required when changing models.
- Preserve raw and filtered metrics, per-target failures, center displacement,
  jitter, availability and timing. Lower jitter alone does not mean accuracy.
- Lateral translation, variable regional errors, filter latency and runtime
  slowdown remain unresolved. No new compensation algorithm is accepted here.
- Core processing remains local. No automatic downloads or image uploads are
  authorized by this decision. Existing privacy and safety requirements apply.
- No OS actions or hardware control are added. No change to target platforms,
  roadmap or individual capability assumptions is made.
- The existing desktop prototype in open PR #137 still uses MGaze. Connecting
  UniGaze there requires a separate implementation: a default UniGaze adapter,
  explicit MGaze selection, model-specific fresh calibration, provenance and
  lifecycle checks. Changing this ADR does not change that runtime.
- The validated UniGaze implementation currently lives in ignored local research
  kits with prepared dependencies and measured camera intrinsics. Portable
  dependency/asset configuration and desktop validation are still required.

No historical measurement or MGaze implementation is removed by this decision.
