# Fixed CENTER offset — fresh live validation results

## Measured sessions and protocol

These are two completed human camera sessions from **one participant (Çağrı)**, saved locally as Git-ignored `.venv/fixed-center-live-cagri-1.json` and `-2.json`. Each used a fresh nine-target 3×3 calibration, one additional exact CENTER presentation immediately afterward, then the same 16 held-out presentations. The CENTER feature was not used to refit the independent-linear mapping. Its fixed offset was computed before any held-out presentation as `0.50 - baseline_prediction_y(anchor_feature)` and added to every held-out y prediction. Baseline and corrected metrics use the same 16 observations per session; x predictions and fitted coefficients were unchanged. Predictions were not clipped.

Both runs used camera index 1 at 1920×1080, a 1200×700 target image area, shuffle seed 42, 0.8 seconds settling and 1.2 seconds sampling per presentation, and a minimum of five usable samples per presentation. The reported condition was normal posture with natural eye opening/blinking and fresh calibration. Collection lasted 52.42 seconds in live-1 and 52.44 seconds in live-2.

| Measured quantity | live-1 | live-2 |
| --- | ---: | ---: |
| Calibration / anchor / held-out presentations | 9 / 1 / 16 | 9 / 1 / 16 |
| Usable calibration / anchor / held-out sampling frames | 300 / 36 / 552 | 319 / 36 / 569 |
| Camera reads, including settling | 1,484 | 1,538 |
| Failed camera reads / no-face observations | 0 / 0 | 0 / 0 |
| Fitted y slope | 61.96450409 | 20.07175694 |
| Fitted y intercept | 2.84202872 | 1.61151150 |
| Calibration CENTER median vertical feature | −0.03967325 | −0.05695507 |
| Post-calibration CENTER median vertical feature | −0.04056511 | −0.05490806 |
| Baseline prediction at post-calibration CENTER | 0.32843155 | 0.50941026 |
| Fixed y offset applied to held-out predictions | +0.17156845 | −0.00941026 |

All sampling attempts yielded usable samples; the reports contain no unavailable sampling observations. The counts above are frame observations, not independent participants or held-out trials.

## Held-out measurements

Errors are in normalized screen y. Signed bias is **prediction minus target**. Median and p95 are for absolute y error; p95 uses the validation harness's linearly interpolated percentile. Ordering uses the repository's distinct-target pair method. Each row covers 16 held-out presentations.

| Session | Method | y MAE | Signed y bias | Median absolute y error | p95 absolute y error | y ordering | Trials |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| live-1 | Independent-linear baseline | 0.31916 | −0.30630 | 0.27481 | 0.63963 | 17/21 | 16 |
| live-1 | Fixed post-calibration CENTER offset | 0.18621 | −0.13473 | 0.17006 | 0.46806 | 17/21 | 16 |
| live-2 | Independent-linear baseline | 0.09453 | +0.08930 | 0.10515 | 0.17350 | 20/21 | 16 |
| live-2 | Fixed post-calibration CENTER offset | 0.08629 | +0.07989 | 0.09574 | 0.16409 | 20/21 | 16 |

In each session, 15 of 16 held-out trials had lower absolute y error with the offset; one worsened. In live-1 the worsened trial was `V-8`, repeat 1 (0.10287 → 0.27444). In live-2 it was `V-4`, repeat 1 (0.04177 → 0.05118). Six live-1 baseline held-out y predictions were outside [0,1]; none of its corrected predictions or either live-2 method's predictions were outside that range. These values were evaluated without clipping. The local JSON reports retain each trial's target, baseline/corrected predictions, errors, and sample count.

## Descriptive comparison

The live-1 offset of +0.17157 lowered held-out MAE by 0.13295 normalized y; its baseline CENTER prediction was 0.32843. The live-2 offset was only −0.00941, lowering MAE by 0.00823; its baseline CENTER prediction was already close to 0.50. Median and p95 absolute y error also fell in **both** sessions. The improvement was therefore substantial in live-1 and modest in live-2.

The following combined figures are descriptive summaries of the **32 held-out observations from the same person**, recomputed from both JSON trial lists. They are not an independent multi-user statistical result, and the session rows above remain the primary evidence.

| Method | y MAE | Signed y bias | Median absolute y error | p95 absolute y error | Trials |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 0.20684 | −0.10850 | 0.13593 | 0.59396 | 32 |
| Fixed CENTER offset | 0.13625 | −0.02742 | 0.10407 | 0.42239 | 32 |

The unchanged y ordering scores are expected: adding one constant to all predictions in a session leaves every pairwise difference unchanged. They show that this correction did not damage ordering; they are **not** evidence of better vertical discrimination. The fitted y slopes differed considerably between these two fresh sessions (about 61.96 versus 20.07), a descriptive indication that mapping sensitivity varied across sessions. These observations do not identify why it varied.

## Supported conclusion and limits

Two fresh live sessions from the same participant support a fixed post-calibration CENTER anchor as a **promising session-bias correction candidate**. The pattern is consistent with a fixed additive offset reducing observed session-level vertical bias when such bias is present. The evidence is the subsequent held-out improvement, not the anchor's own fit.

The correction does **not** resolve within-session or repeated-target vertical variability. It cannot change relative y ordering or the fitted slope. The two slopes differed substantially, and the two offset effect sizes differed. Both sessions were from Çağrı, so this does not resolve Fatih's earlier near-flat vertical result or establish cross-user reliability. Cursor-targeting usability and transition behavior were not evaluated. No cause involving head pose, eyelids, elapsed time, glasses, gaze history, camera position, or physiology can be inferred from these runs.

This is **not a production-approved correction** and does not solve vertical gaze. Production gaze/calibration code remains unchanged; further human decisions and evidence are needed before any production change.
