# Issue #48 — Vertical error decomposition

## Inputs and method

Analyzed the existing Git-ignored `.venv/vertical-drift-cagri-A.json` and `-B.json` independently; no new camera run. Both contain nine calibration targets, 16 held-out trials, and five repeated CENTER checkpoints. The production median aggregator and independent-linear fitter exactly reproduced each report's stored coefficients. The calculations use only derived numerical features and predictions; no camera imagery was loaded or stored.

Calibration residual below means **target minus predicted**. CENTER and held-out signed error mean **predicted minus target**. These have opposite signs. Each calibration-target prediction uses that target's median feature pair. All values are normalized to the target window.

## Calibration fit error

| Session | Axis | Calibration-target MAE | Mean target − predicted | Exact CENTER target − predicted |
| --- | --- | ---: | ---: | ---: |
| A | x | 0.05900 | ~0 | +0.06711 |
| A | y | 0.10176 | ~0 | +0.08903 |
| B | x | 0.06420 | ~0 | +0.05377 |
| B | y | 0.11773 | ~0 | +0.13111 |

The near-zero mean residual across all nine targets is expected from an intercept-bearing least-squares fit; it does **not** indicate low per-target error. At the exact calibration CENTER `(0.5, 0.5)`, vertical predictions were 0.41097 in A and 0.36889 in B. The fitted model therefore already had signed CENTER y errors of −0.08903 and −0.13111 before later feature movement was considered. Stored y slopes were 28.60586 (A) and 31.99278 (B); x slopes were −6.39654 and −7.31770.

## Exact same-target CENTER accounting

All five checkpoints presented the same CENTER `(0.5, 0.5)` target as calibration. The table separates the calibration-center signed y error from the fitted model's output change as the CENTER feature moved. Their sum is the checkpoint signed error. The arithmetic remainder is zero, by identity—not a causal explanation of why the feature changed.

| Session | Checkpoint | Vertical feature shift from calibration CENTER | Calibration-center signed y error | Model output change from feature shift | Checkpoint signed y error |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 0 | −0.000575 | −0.08903 | −0.01646 | −0.10549 |
| A | 1 | +0.000591 | −0.08903 | +0.01691 | −0.07212 |
| A | 2 | −0.003739 | −0.08903 | −0.10695 | −0.19598 |
| A | 3 | −0.001239 | −0.08903 | −0.03544 | −0.12447 |
| A | 4 | −0.005347 | −0.08903 | −0.15295 | −0.24198 |
| B | 0 | −0.001103 | −0.13111 | −0.03530 | −0.16641 |
| B | 1 | −0.003023 | −0.13111 | −0.09670 | −0.22781 |
| B | 2 | −0.002395 | −0.13111 | −0.07662 | −0.20773 |
| B | 3 | −0.002929 | −0.13111 | −0.09370 | −0.22481 |
| B | 4 | −0.003206 | −0.13111 | −0.10256 | −0.23367 |

The feature-output change is not a monotonic time trend. It varies at later checkpoints and, in A, temporarily reverses sign at checkpoint 1. The feature movement's physical cause is not identified here.

## Held-out error and horizontal control

| Session | Held-out trials | x MAE | Signed x bias | y MAE | Signed y bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 16 | 0.06572 | −0.06572 | 0.18687 | −0.18687 |
| B | 16 | 0.04414 | −0.04414 | 0.17961 | −0.16781 |

Horizontal error was lower than vertical error in both sessions. At exact CENTER, the horizontal calibration signed errors were −0.06711 (A) and −0.05377 (B). Horizontal feature-driven output changes across checkpoints ranged from −0.02668 to +0.02302 in A, and −0.01285 to +0.01548 in B, smaller than the later vertical changes in magnitude. This is a reference comparison, not proof that horizontal gaze is stable across users or conditions.

Held-out targets were interstitial, not identical to calibration targets. Targets with y=0.35 or 0.65 have no exact calibration-row counterpart; held-out y=0.5 targets have x=0.35 or 0.65, not the calibration CENTER x=0.5. Consequently, no valid exact same-target calibration feature exists for those held-out observations. Their total errors above are measurable, but the **held-out fit-residual share, drift-attributable share, and remaining unexplained share are unidentified** by these data. Applying CENTER offsets to them would be an unsupported approximation, so no such attribution was made.

## Conclusion and next step

For the identical CENTER target, **both** calibration-fit residual and subsequent feature movement contributed materially to the negative y predictions in both Çağrı sessions. The data do not justify calling either component the sole or universally dominant cause of held-out vertical error. The held-out decomposition remains unidentifiable without a matching calibration-time feature observation for each compared target. The next smallest diagnostic step is to inspect why the current calibration fit has a substantial CENTER residual and, separately, what moves the CENTER feature after fitting—without adding correction constants or changing production behavior. No cross-user conclusion follows from these two single-user sessions.
