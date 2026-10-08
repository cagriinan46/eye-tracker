# Stage B2 — recovery decision, not execution authorization

Date: **2026-10-08, Europe/Istanbul**. Owners: Çağrı İnan Çamlı and Muhammet Fatih
Erdemir. This document proposes a decision process. It does not implement a fix,
authorize capture access, or authorize another calculation. See [CURRENT_STATE](CURRENT_STATE.md).

## What happened and what it means

The first authorized Stage B2 evaluation calculated both sessions' aggregate
results in memory. JSON serialization then rejected a NumPy boolean; the process
exited before persisting or printing numerical outcomes. The results were lost.
Geometry-2 was accessed and is **consumed**. There is no valid R1/R2 PROMISING or
FAIL decision. A software failure is not evidence of a scientific gate failure.

The [preserved failure report](https://github.com/cagriinan46/eye-tracker/blob/b0cb40dbb727eacc0091d5324285200e57dc6490/experiments/gaze_representation_benchmark/RESULTS.md)
documents the exception and a synthetic reproduction. A NumPy-valued transfer
ratio comparison can create a NumPy boolean. Existing end-to-end synthetic
captures had zero baseline transfer, so they exercised an undefined-denominator
branch returning a Python boolean instead. Passing those tests did not verify
the failing output path.

The earlier CI source-verification failure was a separate Git-object availability
problem. PR #70 was squash-merged; its original commit is not guaranteed in a
shallow checkout's main ancestry. CI fix `b0cb40dbb727eacc0091d5324285200e57dc6490`
fetches `refs/pull/70/head`, checks the exact original freeze SHA, verifies the
commit object, and reads its frozen `__init__.py`. The [actual successful run](https://github.com/cagriinan46/eye-tracker/actions/runs/37774315728)
passed all 445 tests. **CI is resolved.** Do not reopen that fix as an active
failure or weaken source verification. Its squash/shallow-checkout lesson remains
part of the audit; no additional CI repair is currently established as necessary.

## What remains protected

| Item | Identity / preservation requirement |
| --- | --- |
| R0/R1/R2 definitions and original gates | Freeze `c4ad261b63fcce3b3998ce8335f8d81fa2118b32`; [authoritative definitions](../../experiments/gaze_representation_benchmark/REPRESENTATION_FREEZE.md) |
| Original sealed evaluator | `14843fd0e43f4e7f7e661b74498c32414452d84d` |
| Original aborted report | `58a8b860a164fd67c2174978004e22221d5a17d3`, preserved in PR #71 history |
| Original captures | Exact hashes/sizes in [DATA_INVENTORY](DATA_INVENTORY.md); never modify |
| Original one-shot marker | `.venv/stage-b2-one-shot-evaluation.json`; retain byte-identical, never reset/delete/overwrite |
| Failed-attempt record | RESULTS, JSON failure record, Git/PR history and append-only WORK_LOG |
| Active PR | [#71](https://github.com/cagriinan46/eye-tracker/pull/71), open draft/unmerged; not altered by this handoff |

No formula, landmark, z scale, transform, availability rule, binocular aggregation,
calibration procedure, analysis window, metric or gate may be changed because
the holdout has been viewed. Exactly R0/R1/R2 remain; no R3, fallback, parameter
search, target-specific correction or production selection follows this failure.

## Technical investigation for a separately approved task

Investigate conversion of NumPy scalar types to JSON-compatible Python primitives
**only at output boundaries**. Preserve computed values, undefined-metric handling,
and finite-value requirements. Do not change the calculations to avoid an
unfavorable or hard-to-serialize result.

Design synthetic full-path tests with nonzero vertical transfer and NumPy boolean
gate results; exercise nested aggregate serialization, both gate pass/fail paths,
undefined denominators, deterministic output and absence of raw geometry in
output. Validate all five gate requirements without participant data. Compare
source and computation paths to the sealed evaluator and frozen definitions;
review any difference before real-data access. Preserve the already-correct CI
freeze-object retrieval and its identity test.

A recovery must establish that it uses the **same frozen calculations and
metrics**, with no tuning or selection. This is a review obligation, not a claim
that a proposed patch has already satisfied it.

## Human options

**Option 1 — retain Stage B2 as incomplete/inconclusive.** Preserve all evidence
and record that candidate decisions are unavailable. Humans may separately
approve a new engineering direction with bounded costs, measurable criteria
and appropriate independent data. Do not relabel this consumed capture as new
holdout evidence or infer candidate failure from missing metrics.

**Option 2 — explicitly authorize a narrowly scoped, audited deterministic
recovery of output lost in serialization.** A second calculation is not covered
by the original one-shot permission. Humans must decide whether recovery is
acceptable and record that approval before any participant-data recomputation.
Recovery output must be described as recovery of a failed first attempt, not a
new independent untouched-holdout experiment.

No option has been selected by this handoff. Claude may recommend; Fatih/Çağrı
authorize. Approval must name the task, permitted code changes, exact inputs,
audit/marker handling and whether real-data execution is allowed.

## Proposed bounded task if Option 2 is approved

First obtain approval for a synthetic-only infrastructure patch and audit plan.
Repair serialization without changing scientific computation; add the full-path
regressions; review the complete diff, run Ruff/pytest/diff checks, and seal exact
recovery code hashes. A reviewable patch is necessary before asking for final
real-data execution approval. Continuing PR #71 or using another branch must be
explicitly agreed by humans; this handoff does neither.

Before real-data execution, require explicit recorded approval of the reviewed
code and recovery procedure. Acceptance criteria must include:

- Original capture bytes/hashes, first-attempt marker and failure records preserved.
- Frozen formulas, per-session calibration-only references/maps, metrics/windows
  and all five thresholds unchanged, with source identity verified.
- Synthetic serialization tests and actual CI pass before participant access.
- No representation/parameter selection, label leakage, validation fitting or
  future-frame dependence.
- A separately identified recovery audit trail records original attempt, human
  authorization, exact code/input hashes, commands, times, any failures and
  outputs. Its approved design must preserve the original guard/marker rather
  than silently bypass, delete or reset it.
- Deterministic aggregate-only output, complete native/common-frame analyses,
  and all required metrics/availability/undefined cases faithfully recorded.
- Original failure remains in history; recovered metrics are explicitly labeled
  deterministic recovery, with consumed-holdout limitations.
- No production change or automatic merge; humans review results and next steps.

The frozen gate remains: y-MAE ratio ≤0.80; normalized vertical-transfer ratio
relative to R0 ≤0.75; lose none of R0's correct vertical ordering checks; x-MAE
ratio ≤1.15; and no leakage/validation fitting/future dependence/post-holdout
tuning. All five are required; an undefined required denominator cannot pass.
Unavailable original metrics permit **no current scientific conclusion**.

If recovery is declined, record the decision in WORK_LOG and keep the failure
records. Propose a separate evidence-based task against the complete product
roadmap. Çağrı's denser/wider 5×5 calibration suggestion is unapproved future
mapping research; it cannot replace B2, retune its outputs, or authorize reuse
of geometry-2. Do not implement either path during handoff.
