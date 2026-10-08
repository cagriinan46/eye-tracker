# Results — vertical signal vs drift diagnosis (Issue #75)

Collected **2026-10-08, Europe/Istanbul**, after the preregistration commit
`6b43f0f` and the pre-data full-screen amendment `893f1b9`. Participant: Fatih
only; never pooled with Çağrı. See [README](README.md) for the frozen rule.

## Sessions

| | Session A | Session B |
| --- | --- | --- |
| Time (+03:00) | 16:26:14–16:27:08 | 16:27:54–16:28:48, after standing up and reseating |
| Camera / input | index 0, 1920×1080 | index 0, 1920×1080 |
| Target image area | **1512×982 full screen** (requested 1512×982) | **1512×982 full screen** |
| Camera reads / failed / no-face | 1,502 / 0 / 0 | 1,508 / 0 / 0 |
| Usable sampling rows | 891 / 891 | 893 / 893 |
| Local derived file (Git-ignored) | `.venv/vertical-collapse-fatih-A.json`, 781,140 B, SHA-256 `690e03fb…3ab10` | `.venv/vertical-collapse-fatih-B.json`, 783,794 B, SHA-256 `97c4b870…3eda` |

Both runs exited 0 with 9 calibration and 16 held-out presentations. Stderr
held only MediaPipe/TFLite initialization lines; no `clearcut` line appeared.

## Preregistered classification

| Measure (production binocular vertical feature) | A | B | Threshold |
| --- | --- | --- | --- |
| Calibration slope β (feature per screen-y) | −0.00875 | **+0.00427** | — |
| Calibration R² | **0.238** | **0.205** | ≥ 0.80 |
| Same-column ordering | **7/9** | **6/9** | ≥ 8/9 |
| Held-out feature ordering | 6/21 | 14/21 | ≥ 17/21 |
| Held-out shift_y | +0.780 | −0.637 | \|·\| ≤ 0.10 |
| **Category** | **SIGNAL** | **SIGNAL** | |

**Overall: `SIGNAL` (both sessions agree).** For Fatih, the production vertical
feature does not represent vertical gaze even within the calibration targets.
The fitted direction even reversed between the two sessions. Large shift_y
values follow from dividing by a near-zero slope and are not meaningful once
the category is `SIGNAL`.

Prediction-level metrics with full-screen targets, for comparison with the
16:00 small-window session (y MAE 0.249, ordering 7/21, bias +0.248):

| Held-out | A | B |
| --- | --- | --- |
| x MAE / ordering | 0.0655 / 21/21 | 0.0583 / 21/21 |
| y MAE / ordering | 0.2134 / 6/21 | 0.2035 / 14/21 |
| Signed y bias | +0.185 | −0.131 |

The full-screen display did not rescue the production vertical estimate.

## Descriptive measures (preregistered, no decision role)

| Calibration fit vs target y | A R² / column order | B R² / column order |
| --- | --- | --- |
| Left-eye vertical | 0.041 / 5/9 | 0.336 / 7/9 |
| Right-eye vertical | 0.378 / 7/9 | 0.020 / 4/9 |
| **Binocular eye opening** | **0.970 / 9/9**, slope −0.0893 | **0.901 / 9/9**, slope −0.0701 |

Head-center-y proxy, validation minus calibration median: +0.0112 (A),
+0.0076 (B), in normalized image units. Within-target associations of the
vertical feature: eye opening −0.39 (A) / +0.30 (B); head-center −0.19 / −0.18.
Neither eye's vertical feature is consistently better. The eye-opening measure
(lid-point distance / corner distance, Issue #44 definition) decreased
monotonically as Fatih looked lower, in every column of both sessions.

## Exploratory analysis (NOT preregistered)

Run after seeing the results above, with a scratch script; treat as hypothesis
generation only. Per-presentation medians of binocular eye opening:

| | A | B |
| --- | --- | --- |
| Row-to-row span of fitted line (0.2→0.8) | 0.054 | 0.042 |
| Median within-target IQR | 0.0045 | 0.0032 |
| Held-out target ordering (21 pairs, calibration direction) | **18/21** | **21/21** |
| Held-out y from calibration-only inverse line: MAE / bias | 0.209 / −0.194 | 0.146 / −0.108 |

Eye opening ordered held-out targets far better than the production feature
(6/21, 14/21), but converting it with the calibration line alone left a large
negative bias: eyes were more open during validation than the calibration line
predicts. So, for Fatih, eye opening looks like an **ordered but shifting**
vertical signal. This was not tested against a frozen rule and uses the same
data that suggested it.

## Interpretation and limits

- The vertical failure for Fatih is a **signal problem** in the current iris
  vs eye-corner feature, not only drift. Fixes that only recentre or filter that
  feature are unlikely to succeed for him.
- Eye opening is a promising candidate, but it is known to be affected by
  blinks, fatigue, expression and lighting, and Çağrı's earlier eye-opening
  studies treated it as a confounder of the production feature. Its offset
  between calibration and validation must be addressed before it can map to
  screen coordinates.
- One participant, one day, two sessions, one Mac. The eye-opening measure and
  the vertical feature share landmarks. No physical cause is established. The
  head-center proxy cannot separate translation from pitch.
- Historical runs (both developers) used a 1200×700 canvas centered on the
  screen; this experiment is the first with a confirmed full-screen target span.

## Possible next steps (proposal, not authorization)

1. **Preregistered eye-opening evaluation on new sessions:** a vertical estimate
   from eye opening (alone, or combined with the production feature) with a
   calibration-only fit plus a predeclared offset-handling rule, judged against
   the accepted exit criteria. Ideally run for both Fatih and Çağrı.
2. Ask Çağrı to run the same A/B diagnosis full screen, to learn whether his
   good historical ordering also holds at full span and whether eye opening
   behaves similarly for him.
3. B2 recovery (R1/R2 representations) remains a joint decision; these results
   suggest geometry normalization of the same iris/corner feature may not fix
   Fatih's case, but this was not tested.
