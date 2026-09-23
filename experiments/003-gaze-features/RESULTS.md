# Experiment 003 — Results

## Environment

The guided experiment was completed by a human on the development Mac. The input resolution was 1920 x 1080. The exact macOS version, camera index, lighting, seating position, visual aids, and installed package versions for this run were not supplied with the results. The experiment specifies MediaPipe 0.10.35 because Experiment 002 succeeded with it; MediaPipe 1.0.1 produced a native SIGABRT during Face Landmarker initialization on the tested macOS ARM64 / Python 3.12 setup. This compatibility finding is not a permanent framework decision.

## Configuration

The script's defaults are camera index 1, the official float16 Face Landmarker model, five target directions, three trials per direction, one-second transition, two-second sampling, and shuffled order with seed 42. The actual command/options, model checksum, target-window arrangement, and interruption status for this run were not supplied. The measured elapsed time was 49.24 s.

## Protocol

The human completed the guided CENTER, LEFT, RIGHT, UP, and DOWN target sequence. The protocol asks the participant to keep their head approximately stable and look directly at each target, moving primarily their eyes. No independent head-motion or gaze-target ground truth was supplied.

## Measurements

| Measurement | Result |
| --- | ---: |
| Elapsed time | 49.24 s |
| Input resolution | 1920 x 1080 |
| Sampling frames | 896 |
| Usable samples | 896 |
| No-face frames | 0 |
| Invalid geometry | 0 |
| Failed camera reads | 0 |
| Tracking-loss events | 0 |

Combined normalized eye-feature summaries (per-label sample counts were not supplied):

| Target | Horizontal mean | Horizontal std | Vertical mean | Vertical std |
| --- | ---: | ---: | ---: | ---: |
| CENTER | 0.5175 | 0.0015 | 0.4094 | 0.0044 |
| LEFT | 0.5560 | 0.0043 | 0.4173 | 0.0281 |
| RIGHT | 0.4814 | 0.0053 | 0.3955 | 0.0296 |
| UP | 0.5172 | 0.0031 | 0.4107 | 0.0267 |
| DOWN | 0.5177 | 0.0014 | 0.4019 | 0.0173 |

These are the supplied measured and rounded summaries; no raw numerical CSV or per-eye summary was supplied for independent recalculation.

## Directional Separation

The measured horizontal convention was LEFT above CENTER and RIGHT below CENTER:

| Horizontal comparison | Reported mean difference | Raw ranges overlap? |
| --- | ---: | --- |
| LEFT - CENTER | +0.0384 | No |
| RIGHT - CENTER | -0.0362 | No |
| LEFT - RIGHT | +0.0746 | No |

The reported vertical mean differences were small and all raw ranges overlapped:

| Vertical comparison | Reported mean difference | Raw ranges overlap? |
| --- | ---: | --- |
| UP - CENTER | +0.0014 | Yes |
| DOWN - CENTER | -0.0075 | Yes |
| UP - DOWN | +0.0089 | Yes |

The differences above are recorded exactly as reported, not recomputed from the rounded per-label means.

## Trial-to-Trial Repeatability

Horizontal trial means were reported as reasonably repeatable, retaining clear LEFT/CENTER/RIGHT separation. Vertical trial means varied substantially across repeated UP and DOWN trials and did not provide reliable directional separation. Individual trial means and within-trial distributions were not supplied, so their magnitude cannot be independently quantified here.

## Observations

All 896 sampling frames yielded usable features. There were no face-detection failures, invalid-geometry frames, failed camera reads, or tracking-loss events. The supplied results do not include head-position proxy values or observations about blinking, lighting, or eye closure, so those potential confounds remain unassessed.

## Limitations

This was one short, single-user directional study, not ground-truth screen calibration. The supplied aggregate results do not include per-label counts, individual trial values, raw feature distributions, or head-position proxy measurements. Window placement, head movement, eye closure, camera/lighting variation, and individual differences may affect the features. Zero face-detection losses in this run do not establish robustness in other conditions. The results do not establish final gaze accuracy, generalize across users or devices, or select MediaPipe as production architecture.

## Conclusion

Under the tested conditions, normalized iris features provided a clear and reasonably repeatable horizontal gaze signal for LEFT/CENTER/RIGHT. The current vertical feature did **not** reliably separate UP/CENTER/DOWN: the reported vertical ranges overlapped and repeated UP/DOWN trial means varied substantially. Tracking and feature geometry remained stable, so face-detection loss cannot explain the observed vertical weakness in this run. Full 2D screen calibration is **not yet validated**. A next, separately approved experiment should investigate more robust vertical gaze features and relevant confounds before full screen calibration. No production thresholds or permanent vision-framework choice follow from this single-user result.

## Reproduction command

From the repository root after the setup in [README.md](README.md), the following runs the script with its documented defaults and camera index 1. The exact command used for the reported run was not supplied:

```bash
.venv/bin/python experiments/003-gaze-features/gaze_feature_experiment.py --camera-index 1 --output .venv/gaze-features.csv
```
