# Offline one-point vertical offset results

## Source and baseline verification

The inputs were the existing Git-ignored `.venv/vertical-drift-cagri-A.json` and `-B.json` from Issue #46: two separate Çağrı Mac sessions, each with fresh nine-target calibration, 16 held-out trials, and CENTER checkpoints 0–4. No new camera collection was performed. The reconstructed linear coefficients and all 16 held-out x/y trial predictions matched the recorded baseline in each session. The fitted y slopes remained **28.60586** (A) and **31.99278** (B). Predictions were never clipped.

All values below are normalized screen y. Bias is signed prediction minus target. Ordering is correctly ordered pairs among distinct held-out targets, using the existing validation rule. Each full-session row evaluates the same 16 trials.

| Session | Candidate | Offset(s) used | y MAE | Signed bias | Median absolute | p95 absolute | y ordering | Trials |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | Linear baseline | 0 | 0.18687 | −0.18687 | 0.19240 | 0.27464 | 21/21 | 16 |
| A | Calibration CENTER | +0.08903 | 0.09841 | −0.09784 | 0.10336 | 0.18561 | 21/21 | 16 |
| A | Immediate checkpoint 0 | +0.10549 | 0.08400 | −0.08138 | 0.08691 | 0.16915 | 21/21 | 16 |
| A | Causal checkpoint refresh | +0.10549/+0.07212/+0.19598/+0.12447 | 0.08136 | −0.06236 | 0.08298 | 0.18022 | **20/21** | 16 |
| B | Linear baseline | 0 | 0.17961 | −0.16781 | 0.20328 | 0.33191 | 20/21 | 16 |
| B | Calibration CENTER | +0.13111 | 0.09391 | −0.03670 | 0.08071 | 0.22559 | 20/21 | 16 |
| B | Immediate checkpoint 0 | +0.16641 | 0.08896 | −0.00140 | 0.05463 | 0.20815 | 20/21 | 16 |
| B | Causal checkpoint refresh | +0.16641/+0.22781/+0.20773/+0.22481 | 0.08772 | +0.03888 | 0.05175 | 0.23256 | 20/21 | 16 |

Checkpoint 4's observed offsets would be +0.24198 (A) and +0.23367 (B), but each was measured **after** the final held-out trial. Neither was applied to any trial or included as an evaluated refresh segment.

## Causal refresh by chronological block

Each row has four held-out presentations. The offset comes only from the CENTER checkpoint immediately before that block. The p95 values use the existing linear-interpolation percentile rule. Ordering denominators vary because blocks contain different target sets.

| Session | Prior checkpoint | Offset | Baseline MAE → corrected | Baseline bias → corrected | Baseline median abs → corrected | Baseline p95 abs → corrected | Ordering before → after | Trials |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| A | 0 | +0.10549 | 0.17372 → 0.06823 | −0.17372 → −0.06823 | 0.19240 → 0.08691 | 0.20382 → 0.09833 | 5/5 → 5/5 | 4 |
| A | 1 | +0.07212 | 0.19500 → 0.12288 | −0.19500 → −0.12288 | 0.19928 → 0.12716 | 0.25877 → 0.18665 | 4/4 → 4/4 | 4 |
| A | 2 | +0.19598 | 0.17627 → 0.03631 | −0.17627 → +0.01971 | 0.17296 → 0.03159 | 0.22179 → 0.06106 | 5/5 → 5/5 | 4 |
| A | 3 | +0.12447 | 0.20250 → 0.09800 | −0.20250 → −0.07802 | 0.21270 → 0.08822 | 0.28723 → 0.16276 | 2/2 → 2/2 | 4 |
| B | 0 | +0.16641 | 0.16610 → 0.04453 | −0.16610 → +0.00031 | 0.16369 → 0.04484 | 0.21656 → 0.05207 | 5/5 → 5/5 | 4 |
| B | 1 | +0.22781 | 0.15945 → 0.11555 | −0.11226 → +0.11555 | 0.16023 → 0.06758 | **0.22018 → 0.29063** | 4/4 → 4/4 | 4 |
| B | 2 | +0.20773 | 0.15683 → 0.08658 | −0.15683 → +0.05090 | 0.18187 → 0.06154 | 0.25400 → 0.18312 | 5/5 → 5/5 | 4 |
| B | 3 | +0.22481 | 0.23605 → 0.10422 | −0.23605 → −0.01124 | 0.26404 → 0.11547 | 0.35199 → 0.16067 | 2/2 → 2/2 | 4 |

The block-local ordering scores do not capture cross-block inversions. In A, changing offsets between blocks reduced full-session ordering from 21/21 to 20/21 despite unchanged ordering inside each block.

## Bounded conclusion

**The fixed one-point anchors are promising offline candidates, not validated production corrections.** Both calibration-CENTER and immediate-post-calibration offsets substantially reduced held-out MAE, median error, and p95 error in both sessions without changing ordering. This supports a material additive component of the *observed model-output error* in these sessions. It does not isolate a physical source or prove the same bias persists in live use. The immediate anchor had lower held-out MAE than the calibration anchor in both sessions, but this is an observation on the same data, not a tuned selection or universal ranking.

Causal checkpoint refresh reduced full-session MAE slightly further, but **failed the no-ordering-damage criterion in A** (21/21 to 20/21), increased A's p95 versus its immediate anchor, and increased B block 1's p95 versus baseline. It also overcorrected B's signed full-session bias to +0.03888. These results do not justify refresh as a production policy. A fixed anchor merits independently approved fresh live validation if the team elects to pursue it. No mapping model, feature, production offset, or other correction was adopted. The sessions cover one person only and do not explain Fatih's near-flat vertical result, transition latency, or the cause of repeated-target feature variability.
