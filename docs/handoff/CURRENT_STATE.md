# RETURNING DEVELOPER — READ THIS FIRST

Verified snapshot: **2026-10-09 15:40, Europe/Istanbul (UTC+03:00)**. This is the primary
operational dashboard. [WORK_LOG](WORK_LOG.md) records subsequent tasks and
corrections; [PROJECT_CONTEXT](PROJECT_CONTEXT.md) explains the entire product.
Refresh this dashboard after approved work; verify live GitHub state on return.

**The reusable camera → landmarks → binocular features → session calibration →
gaze-estimate pipeline is on main. It does not move an OS cursor. Vertical
transfer/accuracy remains unresolved, and the full assistive product is not
delivered. This handoff changes documentation only.**

| Work | Latest verified state | Practical consequence |
| --- | --- | --- |
| Phase 0 | Exit gate met for entering Phase 1 | Feasibility evidence, not a finished product |
| Phase 1 | Reusable pipeline implemented; interaction exit criteria incomplete | Precise OS-cursor work remains paused |
| Stage A / PR #69 | COMPLETE / MERGED | Raw-geometry instrumentation on main |
| geometry-1 and geometry-2 collection | COMPLETE; local files match recorded hashes/sizes | Fatih's Mac: all 57 manifest files hash-verified 2026-10-08 |
| Stage B1 / PR #70 | COMPLETE / MERGED by squash | Exactly R0/R1/R2 frozen; freeze content intact |
| Stage B2 / PR #71 | INCOMPLETE / OPEN, DRAFT, UNMERGED | Preserve active branch and failure evidence |
| PR #71 CI | **GREEN: 445 tests passed** | Previous missing-Git-object CI failure fixed |
| Scientific R1/R2 result | No retained PROMISING/FAIL decision | Serialization failure is not scientific failure |
| geometry-2 | **Consumed by the first authorized attempt** | Cannot be described as still unopened/untouched |
| Production behavior | No change from B2 or this handoff | R0 remains the baseline; no replacement selected |
| Handoff documentation / PR #72 | MERGED 2026-10-08 15:36 +03:00 as a703de9 | Main CI green; handoff is on main |
| Fatih environment `.venv-fatih` | Python 3.12.13; dev + vision deps; Ruff PASS; **422 passed** | Locally ignored; `.venv` untouched; PR #73 merged as b8aee60 |
| Fatih validation session 1 | Camera index 0; held-out x MAE 0.048 (21/21), **y MAE 0.249 (7/21), y bias +0.25** | Pipeline runs on Fatih's Mac; vertical fails for Fatih; next step needs approval |
| Vertical priority (Fatih decision) | Vertical before Phase 2; exit: y MAE ≤ 0.08, ordering ≥ 19/21, \|bias\| ≤ 0.05, 2 users × 2 sessions; 1–2 week timebox | Çağrı may revise on return |
| Full-screen target defect | Historical runs drew a 1200×700 canvas centered on screen; opt-in `--screen-size` fix on Issue #75 branch | Check Çağrı's display; old vertical results used reduced span |
| Issue #75 diagnosis (Fatih A/B) | Preregistered **SIGNAL** (3×3 row-major protocol): production vertical R² 0.24 / 0.21 | PR #76 merged; its eye-opening reading was later corrected by #77 |
| Issue #77 signal comparison (Fatih A/B) | **No winner.** Best COMBO y MAE 0.092 / 0.109; R0 R² 0.71 / 0.77 under 5×5 shuffled full screen | PR #78 merged; repeatability limits vertical; eye opening drifts |
| Issue #79 appearance-model options | Decision document (PR #80 merged); criterion 0.08 ≈ 1.57 cm is at/below published calibrated webcam accuracy | Human decisions on NC weights, L2CS spike, exit criterion, Çağrı #77 run still open |
| Issue #81 coarse zone targeting (Fatih A/B) | **FAIL:** 3×3 success 22% / 44%, wrong 61% / 22%; 4×4 6% / 19% | Code not merged (Fatih's decision); results-only record on main; Fatih reported a "mirror" feeling (head-rotation hypothesis) |
| Issue #84 head-assisted pointing (Fatih A/B) | **HEAD pointer PASSES**: 3×3 100% / 100%, 4×4 100% / 94%; HYBRID (eyes x + head y) fails | PR #85 MERGED (fe7d4a7). **Decision needed:** head as primary pointer (scope); gain/comfort untested |
| Issue #86 iPhone ARKit (Live Link Face) checks (Fatih) | Exploratory, valid run 5 only: eye pitch separates down weakly (≈1.5–2°), up inconsistent, `eyeLookUp` always 0; **no better vertical signal than webcam** | Results-only record; no code, no `src/`; Stage 2/3 not started; next direction awaits Fatih |

The first B2 calculation returned both sessions' aggregates in memory but
failed serializing a NumPy boolean to JSON. The process exited; numerical
outcomes were not persisted or printed. PR #71's RESULTS and JSON are
**failure/provenance records**, not completed benchmark results. Its CI problem
was separate: a shallow checkout lacked the original squash-merged freeze Git
object. Commit `b0cb40dbb727eacc0091d5324285200e57dc6490` fixed retrieval and
identity checks. The [successful GitHub Actions run](https://github.com/cagriinan46/eye-tracker/actions/runs/37774315728)
completed on that SHA. Do not report CI as currently failing.

**Next attention: a human decision, not another evaluation.** Fatih/Çağrı must
choose between retaining B2 as incomplete/inconclusive and explicitly approving
a controlled, audited deterministic recovery of the lost output. Read the
[recovery decision document](STAGE_B2_RECOVERY.md). No recovery is authorized;
do not repair/rerun B2, read participant captures, reset its marker, change its
formulas/gates, merge/close PR #71 or delete its active branch during handoff.

The overall project also still needs intentional gestures and intent handling,
left/right click and scroll, configurable mappings, persistent profiles,
sensitivity settings, an accessible Turkish keyboard/text workflow, safe chair
prototype/communication/emergency stop, robustness and usability evidence, and
later UI-aware selection, Windows support and advanced personalization. Humans
must prioritize bounded tasks against the graduation prototype, rather than
let gaze research continue indefinitely. A wider/denser 5×5 calibration idea
from Çağrı is **unapproved future mapping research**, not B2 recovery permission.

## Exact provenance and source locations

| Identity | Verified value |
| --- | --- |
| Synchronized main at handoff start | `d175b4ce37eb11ede33ff75342af9b36ddd83d75` |
| Original B1 freeze | `c4ad261b63fcce3b3998ce8335f8d81fa2118b32` |
| Sealed B2 evaluator before outcome computation | `14843fd0e43f4e7f7e661b74498c32414452d84d` |
| Aborted B2 report commit | `58a8b860a164fd67c2174978004e22221d5a17d3` |
| Latest verified PR #71 head / CI fix | `b0cb40dbb727eacc0091d5324285200e57dc6490` |
| Active experiment branch — preserve | `experiment/gaze-representation-holdout-evaluation` |
| Local one-shot marker — preserve | `.venv/stage-b2-one-shot-evaluation.json` (`status: started`, historical report) |

[PR #69](https://github.com/cagriinan46/eye-tracker/pull/69) merged
2026-10-07T12:56:59Z; [PR #70](https://github.com/cagriinan46/eye-tracker/pull/70)
merged 2026-10-07T17:54:37Z. The original B1 SHA need not be a main ancestor:
squash merging created d175b4c. At handoff, `git diff <original-freeze> main`
returned no difference across the complete trees. Historical `refs/pull/70/head`
points to the original freeze; PR #71 CI fetches that ref and verifies its SHA,
commit object and readable frozen source. The CI step is on PR #71, not merged
into main. Preserve original source identity verification.

Authoritative [REPRESENTATION_FREEZE](../../experiments/gaze_representation_benchmark/REPRESENTATION_FREEZE.md)
and [preregistration](../../experiments/raw_geometry_gaze_diagnostic/PREREGISTRATION.md)
remain unchanged. Their phrases about an untouched holdout describe the
**pre-evaluation** boundary, not today's data status. B2 files are not on main:
use the preserved [PR #71 failure report at its verified head](https://github.com/cagriinan46/eye-tracker/blob/b0cb40dbb727eacc0091d5324285200e57dc6490/experiments/gaze_representation_benchmark/RESULTS.md)
and [machine-readable failure record](https://github.com/cagriinan46/eye-tracker/blob/b0cb40dbb727eacc0091d5324285200e57dc6490/experiments/gaze_representation_benchmark/results_summary.json).

## Operational blockers and approval boundaries

1. Output serialization defect and lost scientific metrics remain unresolved.
2. Explicit human authorization is required for any recovery/recomputation of
   consumed geometry-2. Infrastructure repair alone does not authorize it.
3. Private data/model identity on Fatih's Mac was hash-verified (57/57) without
   parsing; the old `.venv/real-calibration-fatih.json` is absent, and the new
   `.venv/real-calibration-fatih-20261008.json` holds session 1. Verification is not
   permission to use the data; see [DATA_INVENTORY](DATA_INVENTORY.md).
4. Vertical robustness/cross-user reliability and Phase 1 targeting are unresolved.
5. Third-party MediaPipe telemetry behavior is unresolved; no safe chair or
   desktop OS-input adapter has been delivered.

The historical CI blocker is **resolved**, not a second active blocker. As of
the GitHub inventory, PR #71 was the only open PR and no non-PR issues were open;
the separate [handoff documentation PR #72](https://github.com/cagriinan46/eye-tracker/pull/72)
was merged by Çağrı at 2026-10-08 15:36 +03:00 (see WORK_LOG correction).
Its initial artifact commit is `203210adc2daa20173845607f84f2928ffe10fcc`;
publication records are appended afterward. See WORK_LOG and GitHub for checks
at each head. No stale branch was deleted by this task. Old local experiment
branches were retained; cleanup requires separate proof of merged/inactive
status. Main was clean before switching; ignored experimental data were preserved.

## Human team and next session

Fatih temporarily supervises Claude; Çağrı returns in approximately 1–2 days.
Use [CLAUDE.md](../../CLAUDE.md) for the session reading order and mandatory task
lifecycle. Propose the next task with scope, risks and acceptance criteria and
obtain Fatih's explicit approval before implementation. Record each meaningful
attempt, failure, success and merge-state correction in the append-only log.
An approval discussion is not an approval; absent data or chat history must
not be replaced by guesses.
