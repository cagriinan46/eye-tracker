# Permanent project work log

Timezone default: **Europe/Istanbul (UTC+03:00)**. Participants: Çağrı İnan Çamlı,
Muhammet Fatih Erdemir, Codex, Claude Opus/Claude Code and ChatGPT.

## Append-only policy

Append a dated entry for every meaningful approved task, attempted task,
failure, success, human decision and publication/merge-state correction. An
experiment failure deserves the same evidence as a success. Never silently
convert FAILURE into SUCCESS or pending into merged. Append a correction with
the original entry reference, new evidence, date and explanation. Update the
compact [CURRENT_STATE](CURRENT_STATE.md) dashboard separately.

Record what actually happened, including unsuccessful attempts and unrun checks.
Do not invent measurements or retroactive task diaries. Link detailed RESULTS
and PRs, keep participant raw data out of this log, and distinguish observed
metrics from hypotheses. If commit/PR identity is not known until publication,
append a publication entry afterward. A record may identify the artifact commit
it describes; the commit that adds the record is recoverable from Git history.
On subsequent sessions verify live PR state and append any merge/close correction.

## Entry template for subsequent tasks

```text
Date/time and timezone:
Human owner / approval (who, exact scope, evidence):
AI agent:
Task / approved issue or explicit exception:
Starting branch and full commit SHA:
Goal / out-of-scope boundaries:
Acceptance criteria:
Files changed:
Exact implementation or documentation summary:
Significant technical decisions and evidence:
Commands actually executed / checks not run and why:
Test counts and pass/fail outcomes / actual GitHub CI link and status:
Empirical measurements, units, dataset/protocol provenance (if applicable):
Unsuccessful attempts and error evidence:
Risks, limitations, unresolved decisions:
Artifact commit SHA / pushed branch:
PR number/link / verified status and verification time:
Production behavior changed? What exactly?:
Next proposed task (proposal, not authorization):
```

## 2026-10-08 — verified baseline and documentation handoff in progress

**Human owner:** Çağrı İnan Çamlı; incoming supervisor: Muhammet Fatih Erdemir.
**Agent:** Codex. **Authorization:** explicit documentation-only handoff request;
no issue required for this bounded task. No recovery, feature work, experiment,
participant evaluation or merge authorized.

**Starting state:** branch
`experiment/gaze-representation-holdout-evaluation` at
`b0cb40dbb727eacc0091d5324285200e57dc6490`; clean tracked/untracked working tree,
one worktree, ignored local data present. Inspected branches, worktrees,
uncommitted work, open PRs/issues and merged PRs. Switched to main and pulled;
synchronized main was `d175b4ce37eb11ede33ff75342af9b36ddd83d75`. Created
`docs/claude-project-handoff` from it. No branch deleted; active B2 branch retained.
PR #71 was not modified.

**Goal / acceptance criteria:** a fresh Claude conversation understands the
entire 28-week assistive project, actual implementation and historical evidence,
consumed-holdout failure, local-data transfer, approval boundaries and append-only
task logging. Scope is root CLAUDE plus five handoff documents and a narrow
historical-status correction. No production, evaluator, workflow, freeze or
raw-data changes. Publish a separate documentation PR without merging.

**Verified historical baseline, not reconstructed task entries:**

| Evidence | Verified status / meaning |
| --- | --- |
| [PR69](https://github.com/cagriinan46/eye-tracker/pull/69) | Merged 2026-10-07T12:56:59Z; Stage A raw-geometry instrumentation |
| [PR70](https://github.com/cagriinan46/eye-tracker/pull/70) | Merged 2026-10-07T17:54:37Z by squash; original freeze `c4ad261b63fcce3b3998ce8335f8d81fa2118b32`, merged main d175b4c; complete trees matched by Git diff |
| [PR71](https://github.com/cagriinan46/eye-tracker/pull/71) | OPEN, DRAFT, UNMERGED, latest verified head b0cb40d; Stage B2 incomplete |
| B2 sealed evaluator | `14843fd0e43f4e7f7e661b74498c32414452d84d`, before outcome computation |
| B2 aborted report | `58a8b860a164fd67c2174978004e22221d5a17d3`; aggregate computation returned in memory, then JSON serialization failed on NumPy boolean; lost numerical outcomes |
| Original one-shot attempt | geometry-2 consumed; no R1/R2 PROMISING/FAIL decision exists; no subsequent scientific tuning/retry documented |
| Original local marker | `.venv/stage-b2-one-shot-evaluation.json`, read-only provenance inspection confirmed `status: started`, sealed evaluator/freeze/input identities |
| Historical CI FAILURE | [Run37772361172](https://github.com/cagriinan46/eye-tracker/actions/runs/37772361172): 444 passed / 1 failed; `test_freeze_source_identity_without_participant_files` could not read original Git object in checkout |
| Subsequent CI correction / SUCCESS | Fix `b0cb40dbb727eacc0091d5324285200e57dc6490` fetches/verifies original PR70 head; [run37774315728](https://github.com/cagriinan46/eye-tracker/actions/runs/37774315728) completed successfully, 445 passed. This resolves CI, not B2 serialization or scientific results |

**Documentation summary / files:** `CLAUDE.md`; `docs/handoff/PROJECT_CONTEXT.md`,
`CURRENT_STATE.md`, `WORK_LOG.md`, `DATA_INVENTORY.md`, `STAGE_B2_RECOVERY.md`;
`docs/PROJECT_STATUS.md` dated dashboard pointer/historical clarification only.
Context covers approved phases 0–11, software and mandatory safe chair, macOS /
Windows boundaries, production source modules, historical negative results and
latest freeze/failure. Human governance remains authoritative. No other scope
or architecture decision made.

**Evidence inspected:** governing documentation/ADRs; source/test/workflow file
inventory and production modules; experiment README/RESULTS/preregistration;
PR69/70/71, recent merged history, PR43's separate Fatih report; actual successful
CI run and workflow patch. Baseline GitHub inventory had only PR71 open and no
open non-PR issues. Existing README placeholder noted, not changed.

**Local provenance check:** 57 relevant JSON/CSV/model/provenance assets inventoried
using metadata and opaque SHA-256 hashing; no capture JSON/CSV parsed and no
outcome computed. Both geometry hashes/sizes matched documented identities.
Marker SHA-256 matched
`763a89a38347a7cdea895c6fa6b843aa63d05d441fecd38d45fc67537e467660`, 445 bytes.
Fatih calibration file was absent on this Mac; all Fatih-machine availability
is UNVERIFIED. See DATA_INVENTORY for exact identities and private transfer plan.
No private asset was copied, changed or committed.

**Checks:** Git status/worktrees/branches, synchronized main and whole-tree freeze
comparison completed; GitHub merge/draft/head/CI statuses checked. Documentation
link/scope verification, Ruff/pytest/diff results and publication identities will
be appended after execution, rather than claimed in advance.

**Failures / limitations:** the historic B2 serialization failure and historic
CI failure are preserved above; only CI recovered. Lost outcomes cannot support
scientific success/failure. Current handoff cannot authorize another attempt.
Targeting/vertical transfer, cross-user behavior, delivered interaction features,
telemetry and hardware remain unresolved. Transfer has not occurred.

**Human decision outstanding / next proposed task:** decide whether to retain
inconclusive B2 or authorize a bounded synthetic-tested, audited deterministic
recovery. Claude may propose; Fatih/Çağrı authorize. Wider/denser calibration is
a separately unapproved future idea. No next task started. Artifact commit and
handoff PR publication are pending this entry; append actual identities later.

## 2026-10-08 15:28 +03:00 — handoff validation completed before publication

Same human authorization/agent/task as the baseline entry. The existing root
CLAUDE.md was replaced with the concise navigation/lifecycle entry point; five
handoff documents were created and PROJECT_STATUS narrowly dated/corrected.
AGENTS and governing documents remain unchanged.

Actually executed checks:

- `.venv/bin/ruff check .`: PASS.
- `.venv/bin/ruff format --check .`: PASS, 219 files already formatted.
- `PYTHONPATH=.venv/stage-b1-audit .venv/bin/python -m pytest`: **422 passed,
  0 failed**, 2.24 s. An existing read-only audit hook prevented opening either
  real geometry capture. These are main-derived tests, distinct from PR71's
  successful 445-test CI; no B2 evaluator ran.
- Local Markdown existence check: **166 links, zero missing**; required dashboard
  opening heading and seven-file documentation scope verified.
- `git diff --check`: PASS; protected production/experiment/test/workflow and
  governance paths compared to main with no differences.
- Complete document/change review and independent read-only review: no actionable
  findings. No review access to participant assets.
- Original marker rehashed after checks: still 445 bytes and identical original
  SHA-256. Neither B2 rerun nor any new scientific metric produced.

No task failure or implementation change occurred. Current limitation remains
the unapproved B2 recovery decision and unverified transfer/data availability.
Commit/push/PR publication metadata will be appended after those actions; no
handoff GitHub CI result claimed before a run exists. No next task authorized.

## 2026-10-08 15:30 +03:00 — handoff published; human review pending

Continuation of the same approved documentation task, Çağrı/Codex. Artifact
commit **`203210adc2daa20173845607f84f2928ffe10fcc`** committed all seven intended
documentation files with message `docs: establish Claude handoff and persistent
project history`, then pushed `docs/claude-project-handoff`. Working tree was
clean after push. Opened [PR #72](https://github.com/cagriinan46/eye-tracker/pull/72)
against main; verified OPEN, non-draft, UNMERGED. This publication entry and the
dashboard link are subsequent documentation-only changes; their commit identity
is available in Git history. No merge requested or performed.

The GitHub connector's create-PR request returned 403 (`Resource not accessible
by integration`). The same authorized PR creation succeeded through GitHub's
API using existing repository access; no credentials were printed, stored in
documentation, or changed. This was a publication access failure/recovery,
not a scientific evaluation recovery.

Reverified PR71 remained OPEN/DRAFT/UNMERGED at the unchanged b0cb40d head.
Main/freeze/evaluator/production were not altered; B2 was not rerun. No local
data transfer or new experiment occurred. Local validation results are in the
preceding entry. At 15:30, [handoff CI run37777293463](https://github.com/cagriinan46/eye-tracker/actions/runs/37777293463)
was in progress on the initial artifact 203210a; no success claimed at that time.
The independent PR71 run remains verified successful 445 tests. Inspect GitHub
Actions for the latest handoff head rather than assuming an earlier run covers
a later commit.

Outstanding decision and proposed next task are unchanged: humans decide whether
to authorize audited B2 recovery, or retain incomplete/inconclusive status.
Fatih first reads CLAUDE and its ordered context, verifies code/private assets,
and proposes a bounded task for explicit approval. No new approval was granted.

## 2026-10-08 15:33 +03:00 — publication retry and CI status correction

Same documentation task/authorization. The publication-record commit
`85195e78154e96070cc4664c142102803a8cb43f` initially failed to push because the
Mac could not resolve `github.com`; repeated normal pushes and a read-only
remote-ref query failed for the same reason. No Git history/data was reset.
Verified a current DNS answer and reachable HTTPS with normal TLS validation;
a **command-scoped** `http.curloptResolve` override then pushed the commit
successfully. No persistent Git/DNS/network settings were changed. This is a
publication infrastructure incident, not permission for B2 recovery.

Correction to the 15:30 pending-CI observation: [run37777293463](https://github.com/cagriinan46/eye-tracker/actions/runs/37777293463)
subsequently completed **SUCCESS** on artifact
`203210adc2daa20173845607f84f2928ffe10fcc`. Later publication-log commits trigger
their own runs; consult the latest PR72 head/Actions for their status. Earlier
CI success is never substituted for a later-head check.

Read-only remote refs still matched main d175b4c, original PR70 head c4ad261,
and preserved active B2 branch b0cb40d. PR71 remains open/draft/unmerged; no
scientific computation or production change occurred. This appended incident
record is the only additional file change; diff/link/scope checks remain required
before its commit. Handoff awaits human review, and the next task still awaits
human approval.

## 2026-10-08 15:48 +03:00 — correction: handoff PR #72 merged

Correction to the 15:30 and 15:33 entries, which recorded PR #72 as open and
unmerged. Verified live through GitHub by Claude Code for Fatih:
[PR #72](https://github.com/cagriinan46/eye-tracker/pull/72) **MERGED** at
2026-10-08T12:36:37Z (15:36 +03:00) by Çağrı (`cagriinan46`), head
`618a9f0cc71aa35427ea09d1a5c4a64fe1864ebb`, squash commit on main
`a703de9d7a4a93f1c37c3e7570ae1e7da1ece8eb`. `git diff 618a9f0 a703de9` returned
no difference, so main holds exactly the reviewed handoff content.
[Main push CI run37778099516](https://github.com/cagriinan46/eye-tracker/actions/runs/37778099516)
completed SUCCESS. Branch `docs/claude-project-handoff` still exists locally and
on origin; it was not deleted in this session.

PR #71 rechecked at the same time: OPEN, DRAFT, UNMERGED, head unchanged at
`b0cb40dbb727eacc0091d5324285200e57dc6490`; its CI check remains pass. No open
issues. Old local experiment branches whose remotes are gone were not deleted.

## 2026-10-08 15:48 +03:00 — Fatih's local environment and data identity check

**Human owner / approval:** Muhammet Fatih Erdemir, explicit chat request on
2026-10-08: read the handoff, verify GitHub, create a separate Python 3.12
environment named `.venv-fatih` without touching `.venv`, ignore it locally,
install dependencies, run tests and Ruff, record the work, then propose (not
start) the next task. Explicitly excluded: re-evaluating geometry-1/2 and any
B2 recovery. Treated as a bounded documentation/environment exception; no issue.
**Agent:** Claude Code (Claude Opus 5.5). **Start:** main
`a703de9d7a4a93f1c37c3e7570ae1e7da1ece8eb`, clean; branch
`docs/fatih-local-environment` created from it for this log only.

**Environment:** Fatih's Mac (macOS 26 / Darwin 25.6.0, Apple Silicon). The
existing `.venv` is a transferred copy whose `pyvenv.cfg` points at Çağrı's
`/opt/homebrew` Python, which does not exist on this Mac, so it is not usable as
an interpreter here; it was used only as a configuration reference (`pyvenv.cfg`
read) and kept as the private data store. New `.venv-fatih` was created with
`~/.local/bin/python3.12 -m venv .venv-fatih` (uv-managed CPython 3.12.13,
matching `.venv`'s 3.12.13). It is ignored via `.git/info/exclude` only
(`.venv-fatih/`), so no tracked ignore file changed. Installed: pip 26.2.1;
`pip install -r requirements-dev.txt` → pytest 9.1.1, ruff 0.16.10, numpy 2.5.3;
then `pip install --group vision` from pyproject → mediapipe 0.10.35,
opencv-contrib-python 5.0.0.93 (+ transitive packages). `pip check`: no broken
requirements. Imports of mediapipe/cv2/numpy succeeded. Requirements are not
locked (ADR-004), so other machines may resolve newer unpinned dev packages.

**Checks actually executed in `.venv-fatih`:**

- `.venv-fatih/bin/ruff check .`: PASS ("All checks passed!").
- `.venv-fatih/bin/ruff format --check .`: PASS, 219 files already formatted.
- `.venv-fatih/bin/python -m pytest -q -p no:cacheprovider`: **422 passed,
  0 failed**, once with dev requirements only (CI scope, 2.09 s) and again after
  the vision group (1.53 s). Both runs used a scratch `sitecustomize` audit hook
  (outside the repo) that raises on any file open under this repo's `.venv/`;
  a probe confirmed the hook was active. No test was blocked. The count matches
  the 422 main-derived tests recorded at 15:28; PR #71's 445 includes its
  unmerged B2 tests and was not rerun here.

**Data identity (no parsing):** every one of the 57 DATA_INVENTORY manifest
entries is present under `.venv/` on Fatih's Mac and matches its recorded byte
size and SHA-256 (57 ok / 0 mismatch / 0 missing), including both geometry
captures, the detector model and the original one-shot marker
(`763a89a3…7467660`, 445 bytes). Only `shasum`/`stat` were used; no capture JSON
or CSV was decoded. `.venv/real-calibration-fatih.json` remains **absent** on
this Mac too. A metadata fingerprint (size/mtime/path of all 5,959 files in
`.venv/`) was identical before and after the work: `.venv` was not modified.

**Not done:** no B2 repair/recovery/rerun, no geometry-1/2 evaluation, no camera
run, no production/experiment/test change, no branch deletion, no merge.
Production behavior unchanged. Next task is proposed to Fatih in chat and awaits
explicit approval; this entry is not that approval. Commit/PR metadata will be
appended after publication.

## 2026-10-08 15:55 +03:00 — Fatih environment record published; review pending

Same task/authorization as the 15:48 environment entry. Artifact commit
**`802d9c64e3f22ccf1ff25ca2e5165e7d4cf5a25c`** (`docs: record Fatih local
environment and PR #72 merge`) changed only CURRENT_STATE and WORK_LOG; pushed
`docs/fatih-local-environment` and opened
[PR #73](https://github.com/cagriinan46/eye-tracker/pull/73), verified OPEN,
non-draft, UNMERGED. [CI run37779593684](https://github.com/cagriinan46/eye-tracker/actions/runs/37779593684)
on 802d9c6 completed **SUCCESS**. This publication entry is a later commit with
its own CI run; check the latest PR #73 head. No merge requested or performed by
the agent; Fatih reviews and merges. Next task still awaits Fatih's approval.

## 2026-10-08 16:05 +03:00 — correction: PR #73 merged

Correction to the 15:55 entry (PR #73 OPEN/UNMERGED, review pending). Verified
through GitHub: [PR #73](https://github.com/cagriinan46/eye-tracker/pull/73)
**MERGED** at 2026-10-08T12:55:11Z (15:55 +03:00) by Fatih (`MFatihErdemir`) as
squash commit `b8aee60179a543fa0a3b55f9529a601c7ba7f0af`; `git diff` against the
PR head `3db235d` showed no difference. The agent did not merge it. Branch
`docs/fatih-local-environment` was not deleted in this session.

## 2026-10-08 16:05 +03:00 — Fatih production-path calibration validation, session 1

**Human owner / approval:** Muhammet Fatih Erdemir, explicit chat approval on
2026-10-08 for one session of the existing 9-calibration + 16-validation
protocol with himself as participant; use only `.venv-fatih`; save the result
only to a new, unique Fatih-owned JSON inside `.venv/` without overwriting
anything; do not delete/modify Çağrı's `.venv` contents, models, captures or
the B2 marker; do not rerun or repair B2. This is the new participant capture
authorization required by CLAUDE.md. **Agent:** Claude Code (Claude Opus 5.5).
**Start:** main `b8aee60179a543fa0a3b55f9529a601c7ba7f0af`, clean; log branch
`docs/fatih-real-calibration-validation`. No code changed.

**Pre-checks:** `system_profiler SPCameraDataType` listed one camera, the
built-in "MacBook Pro Kamerası". An OpenCV AVFoundation probe (frames read in
memory, never saved) opened index 0 at 1920×1080; indices 1 and 2 were out of
bounds. So **index 0** is the built-in camera on Fatih's Mac (Çağrı's setup used
1). Model `.venv/models/face_landmarker.task` 3,758,596 bytes, SHA-256
`64184e22…bc9ff`, matching DATA_INVENTORY. Output path confirmed absent first.

**Command (15:59:30–16:00:23 +03:00, exit 0):**
`PYTHONPATH=src .venv-fatih/bin/python -m validation.real_calibration
--camera-index 0 --model .venv/models/face_landmarker.task --output
.venv/real-calibration-fatih-20261008.json`. Output written with exclusive
create: 16,969 bytes, SHA-256
`3552acbcc6ad48ac595fdd53a8aa13aed60d653d74a88ae3b853d894f297365b`; local and
Git-ignored, not committed. A size/mtime fingerprint of all 3,694 other
non-cache `.venv/` files was identical before and after; marker SHA unchanged
(`763a89a3…7467660`). Stderr held only MediaPipe/TFLite init messages; no
`portable_clearcut_uploader` line appeared in this run (not proof of no
telemetry).

**Collection:** seed 42; 9 calibration + 16 held-out presentations; 50.57 s;
1,511 camera reads, 0 failed, 0 no-face observations (≈29.9 reads/s); 901
sampling attempts, 901 usable (34–37 per presentation), 0 unavailable.
`window_image_area` was reported as **1200×700**, which equals the harness's
initial canvas, so fullscreen may not have been applied when it was measured.
Pixel-equivalent errors below are in that 1200×700 image area, not monitor
pixels; normalized coordinates are unaffected. Whether the window looked full
screen is still to be confirmed by Fatih.

**Results (normalized screen units; Fatih only, not pooled):**

| Metric | Calibration fit (9) | Held-out (16) |
| --- | --- | --- |
| x MAE / median / p95 | 0.0332 / 0.0252 / 0.0723 | **0.0481** / 0.0371 / 0.1132 |
| y MAE / median / p95 | 0.1748 / 0.1566 / 0.3057 | **0.2487** / 0.2386 / 0.5234 |
| 2D error mean / median | 0.1818 / 0.1586 | 0.2591 / 0.2425 |
| Signed bias x / y | ≈0 / ≈0 (OLS) | −0.0364 / **+0.2477** |
| Ordering x / y | 27/27 / **19/27** | **21/21** / **7/21** |
| Pixel-equivalent mean (1200×700 area) | 134.1 | 191.5 |

**Interpretation (descriptive, one session):** the production pipeline works end
to end on Fatih's Mac (camera, model, 100% availability). Horizontal mapping is
good and comparable to Çağrı's PR #43 run (x MAE 0.0519, 21/21). Vertical
mapping carries **no usable information on held-out targets**: mean predicted y
was ≈0.76 for the 0.35 targets, ≈0.79 for 0.50 and ≈0.70 for 0.65 (ordering
7/21), and all predictions shifted
downward by ≈+0.25. The vertical failure is already in the calibration fit:
predicted-y row means were ≈0.35 / 0.58 / 0.57 for the 0.2 / 0.5 / 0.8 rows, so
the middle and bottom rows were not separated, and within rows y varied with
column (top row 0.25 → 0.29 → 0.51). This repeats Fatih's 2026-09-25 PR #43
finding (y ordering 4/21) in a different form: the earlier output was flat near
0.50–0.52, this one is spread out but biased and unordered. Possible
contributors (lid occlusion when looking down, head pose, feature shift between
calibration and validation, glasses) are **hypotheses only**; the report holds
no feature values, so feature gain/drift cannot be separated from this file
without new analysis.

**Not done:** no B2 action, no geometry-1/2 access, no Çağrı-data comparison
beyond published numbers, no tuning, no code change, no second session.
Production behavior unchanged. Next options are proposed to Fatih in chat and
await approval.

## 2026-10-08 16:10 +03:00 — validation record published; review pending

Same task/approval as the 16:05 validation entry. Artifact commit
**`51cbe9503ab36bb82bcb1d8f243a75106953c526`** changed only CURRENT_STATE and
WORK_LOG; pushed `docs/fatih-real-calibration-validation` and opened
[PR #74](https://github.com/cagriinan46/eye-tracker/pull/74), verified OPEN,
non-draft, UNMERGED. [CI run37781221911](https://github.com/cagriinan46/eye-tracker/actions/runs/37781221911)
on 51cbe95 completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih reviews and merges. Open question for Fatih:
did the target window actually cover the full screen (reported 1200×700)?

## 2026-10-08 16:30 +03:00 — correction: PR #74 merged; human priority decision

Correction to the 16:10 entry (PR #74 OPEN/UNMERGED): verified through GitHub,
[PR #74](https://github.com/cagriinan46/eye-tracker/pull/74) **MERGED** at
2026-10-08T13:06:32Z (16:06 +03:00) by Fatih (`MFatihErdemir`) as squash commit
`ea5bd9ee908062148ce7be534847dd7f82d51c03`; no tree difference from its head.
Fatih has not yet answered whether the 16:00 validation window looked full screen.

**Human decision (Fatih, chat, 2026-10-08):** the main goal is eye control, so
the vertical axis is completed **before** Phase 2 or other subsystems. Fatih
accepted Claude's proposed measurable exit criteria and timebox ("dediklerini
yapalım"): held-out y MAE ≤ 0.08, y ordering ≥ 19/21 and |y bias| ≤ 0.05 for
both developers in at least two sessions each, coarse 3×3 targeting ≥ 80%,
timeboxed to 1–2 weeks followed by a team review. This is within Phase 1 of the
roadmap, not a scope change; Çağrı may revise it on return. B2 recovery remains
a joint decision for when Çağrı returns.

## 2026-10-08 16:30 +03:00 — Issue #75 vertical diagnosis preregistered

**Approval:** Fatih approved task V1 in chat ("dediklerini yapalım dikey eksen
için iyi olacaksa"): diagnose Fatih's vertical failure as signal inadequacy vs
drift before any fix; two new Fatih sessions with new unique outputs in `.venv/`.
**Agent:** Claude Code (Claude Opus 5.5). **Issue:**
[#75](https://github.com/cagriinan46/eye-tracker/issues/75). **Start:** main
`ea5bd9ee908062148ce7be534847dd7f82d51c03`, branch
`experiment/75-vertical-signal-drift-diagnosis`.

**Scope change during planning:** the approved plan proposed adding feature
logging to `validation/real_calibration.py`. Inspection found the merged Issue
#44 collector `experiments.vertical_collapse_diagnostics.run` already records
per-frame binocular/left/right features, eye opening, head-center proxy and
mapping coefficients under the same protocol, and its README anticipated a
Fatih run. It is reused unchanged, so **no harness or production code changes**.
The 1200×700 window-measurement question is therefore not fixed here; it affects
pixel-equivalent metrics only.

**Preregistration (committed and pushed before any session):**
[README](../../experiments/vertical_signal_drift_diagnosis/README.md) and
`experiments/vertical_signal_drift_diagnosis/analysis.py` freeze the rule:
SIGNAL if calibration R² < 0.80 or same-column ordering < 8/9; else INSTABILITY
if held-out feature ordering < 17/21; else DRIFT if |shift_y| > 0.10; else
NOT_REPRODUCED; overall only if A and B agree, otherwise MIXED. Thresholds were
chosen after seeing the 16:00 prediction-level summary but before any Fatih
feature data. 13 synthetic tests cover each category, sign handling, missing
samples, combination and CLI. Session results will be appended after collection.

## 2026-10-08 16:45 +03:00 — Issue #75: full-screen target defect found and fixed before sessions

Time note for the preceding two entries: they were headed 16:30, but their
commit `6b43f0f` was actually made and pushed at about **16:19 +03:00**.

**Finding:** Fatih reported that the 16:00 validation targets appeared in the
middle of the screen, not full screen. A probe (no camera) showed OpenCV on this
Mac sets the window full screen (property 1.0) but displays the 1200×700 canvas
centered at its own size; `getWindowImageRect` stayed 1200×700. Finder reports a
1512×982-point desktop (3024×1964 Retina). Targets therefore spanned about 43%
of the screen height instead of 60%. A 1512×982 canvas measured exactly
1512×982 and Fatih visually confirmed the red test border was at the screen
edges. **Every historical report found in the repository (Experiment 006,
drift, collapse, sensitivity, position, fixed-center) records 1200×700**, so
earlier vertical studies may also have used a reduced on-screen span; whether
Çağrı's display showed the same effect is unverified and should be checked
with him. This is a protocol observation, not a re-analysis of old data.

**Fix (approved by Fatih: "evet tam ekrandı, düzeltmeyi uygula"):** shared
`open_target_window` and `parse_screen_size` in `validation/real_calibration.py`;
opt-in `--screen-size WIDTHxHEIGHT` on the validation harness and on the Issue
#44 collector. With it, the canvas is drawn at display size after a 1.5 s
full-screen settle, and the run fails if the measured area differs. Without it,
behavior is byte-for-byte the historical sequence. Reports add
`requested_screen_size`. Validation README documents the option. A real-display
smoke call returned (1512, 982). The Issue #75 README records this as a protocol
amendment made before any data; rule and thresholds unchanged.

**Checks:** `.venv-fatih/bin/ruff check .` PASS; `ruff format --check .` PASS
(223 files); `pytest` **440 passed** (5 new window/CLI tests + 13 analysis tests
over the 422 main baseline); `git diff --check` PASS.

## 2026-10-08 16:30 +03:00 — Issue #75 sessions completed: Fatih vertical failure is SIGNAL

Time note: the previous entry was headed 16:45, but its commit `893f1b9` was
made and pushed at **16:25 +03:00**. Header times from here on come from the
system clock at writing time.

Same approval/task as the Issue #75 entries. Both sessions ran with
`--screen-size 1512x982`, camera index 0, `.venv-fatih` only:

- Session A 16:26:14–16:27:08, exit 0; 1,502 reads, 0 failed, 0 no-face,
  891/891 usable; `.venv/vertical-collapse-fatih-A.json` 781,140 B, SHA-256
  `690e03fbb9bef4f03d636a659cddb60473c1a5f1e988a35f7e1fbbd89303ab10`.
- Fatih stood up and reseated (results were not shown to him in between).
- Session B 16:27:54–16:28:48, exit 0; 1,508 reads, 0 failed, 0 no-face,
  893/893 usable; `.venv/vertical-collapse-fatih-B.json` 783,794 B, SHA-256
  `97c4b870be240778e1a83ab35aa08889dcbe1aa51f9744ce0b996b15e3873eda`.
- Both reports record a measured 1512×982 target image area. Outputs are
  Git-ignored and not committed. All 3,695 pre-existing non-cache `.venv/`
  files unchanged by size/mtime; B2 marker SHA unchanged.

**Preregistered result** (`python -m experiments.vertical_signal_drift_diagnosis.analysis`):
**A = SIGNAL, B = SIGNAL, overall SIGNAL.** Production vertical feature:
calibration R² 0.238 / 0.205, column ordering 7/9 / 6/9, fitted direction
reversed between sessions (β −0.00875 / +0.00427), held-out feature ordering
6/21 / 14/21. Held-out predictions: y MAE 0.213 / 0.203, y ordering 6/21 / 14/21,
y bias +0.185 / −0.131; x MAE 0.066 / 0.058 with 21/21. Full-screen targets did
not rescue the production vertical estimate.

**Descriptive:** binocular eye opening vs target y had calibration R² 0.970 /
0.901 with 9/9 column ordering in both sessions (slope −0.089 / −0.070).
**Exploratory, not preregistered:** eye opening ordered held-out targets 18/21
and 21/21, but a calibration-only inverse line gave y MAE 0.209 / 0.146 with
bias −0.194 / −0.108 (eyes more open during validation). Full tables and limits:
[RESULTS](../../experiments/vertical_signal_drift_diagnosis/RESULTS.md).

**Interpretation:** for Fatih the current iris-vs-corner vertical feature lacks
usable vertical signal; recentering/filtering it is unlikely to help. Eye
opening is a promising but shifting candidate. One participant, one day. No
production change; no B2 action; no Çağrı data. Next options are proposed to
Fatih and await approval.

## 2026-10-08 16:31 +03:00 — Issue #75 published; review pending

Artifact commit **`afc7f7c262d5920388f0d154777c81bd532f3bb8`** on
`experiment/75-vertical-signal-drift-diagnosis` (after `6b43f0f` preregistration
and `893f1b9` full-screen fix). Opened [PR #76](https://github.com/cagriinan46/eye-tracker/pull/76)
(Closes #75), verified OPEN, non-draft, UNMERGED. [CI run37784938372](https://github.com/cagriinan46/eye-tracker/actions/runs/37784938372)
on afc7f7c completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih reviews and merges. Next task awaits approval.

## 2026-10-08 21:51 +03:00 — correction: PR #76 merged; Issue #77 V2 preregistered

**Correction** to the PR #76 publication entry (OPEN/UNMERGED): verified through
GitHub, [PR #76](https://github.com/cagriinan46/eye-tracker/pull/76) **MERGED** at
2026-10-08T14:13:09Z (17:13 +03:00) by Fatih (`MFatihErdemir`) as squash commit
`9b97e9d44ca675c408e38049f080af9af0009728`; no tree difference from its head;
Issue #75 CLOSED.

**Approval:** after Claude outlined options for better vertical results, Fatih
approved V2 in chat ("onaylıyorum, V2'yi başlat"): compare vertical signals in
one protocol, experiment-only capture of blendshapes and head pose, full-screen
5×5 calibration with repeated checkpoints, preregistered candidates and rule,
two Fatih sessions. **Agent:** Claude Code (Claude Opus 5.5). **Issue:**
[#77](https://github.com/cagriinan46/eye-tracker/issues/77). **Start:** main
`9b97e9d`, branch `experiment/77-vertical-signal-comparison`.

**Implementation (experiment-only):** `experiments/vertical_signal_comparison/`
with `protocol.py` (50 presentations: 3 checkpoint blocks, shuffled 5×5
calibration at 0.1–0.9, shuffled 4×4 validation at 0.2–0.8, seed 77),
`capture.py` (`SignalExtractor` subclass of the production adapter requesting
blendshapes and the transformation matrix; production adapter unchanged),
`run.py` (requires `--screen-size`, refuses overwrite, serializes with
`allow_nan=False` before opening the output file), `analysis.py` and README
preregistration. Candidates R0, OPEN, OPEN_Q, BLEND, COMBO; pass per session =
y MAE ≤ 0.08, ordering ≥ 19/21 of 96 pairs, |bias| ≤ 0.05; winner must pass
both sessions. Blink frames (eyeBlink > 0.5) excluded from all candidates.

**Pre-data hardware smoke (no data saved):** a first 60-frame probe right after
opening the camera gave 0/60 usable frames (camera warm-up); after discarding
30 warm-up reads, both the production adapter and `SignalExtractor` gave 60/60
usable, and a 90-frame check found every blendshape/pose field in 90/90 frames.
Median detector call 6.81 ms extended vs 6.70 ms production.

**Checks:** `ruff check .` PASS; `ruff format --check .` PASS (230 files);
`pytest` **454 passed** (14 new). One intermediate test failure (R0 vs
production fitter compared slopes near zero with a relative tolerance) was a
fixture problem and fixed by giving the synthetic feature a real y slope.
Sessions follow after this commit is pushed.

## 2026-10-08 21:59 +03:00 — Issue #77 sessions: no winner; eye-opening finding corrected

Small correction to the previous entry: `ruff format --check .` reported 231
files at the preregistration commit `e4cd8dc` (230 was the count before the
README was added). Preregistration pushed at 21:51 +03:00.

**Sessions** (`--screen-size 1512x982`, camera 0, `.venv-fatih`):
A 21:53:15–21:55:00, B 21:56:01–21:57:46 after reseating; both exit 0, 50
presentations, 0 failed reads, 0 no-face; usable 1,790 / 1,781, common frames
after blink exclusion 1,786 / 1,781. Files `.venv/vertical-signals-fatih-A.json`
(2,162,026 B, SHA-256 `e3b0127d2f8e920d3ec48c756e5d09139e05b5018bb2d5b10326d8b0f3ace25a`)
and `-B.json` (2,150,241 B, `06b550bcc746ef472ef03ca7b331b3a642bf11daab9d4757055f91aa81a03bfd`),
Git-ignored. All 3,697 pre-existing non-cache `.venv/` files unchanged; B2 marker
unchanged. Detector median 5.63 / 5.73 ms.

**Telemetry observation:** both runs' stderr contained MediaPipe
`portable_clearcut_uploader` "Failed to send to clearcut: FAILED_PRECONDITION"
lines (2 lines each). Earlier runs today with production options showed none.
The open telemetry question in PROJECT_CONTEXT remains unresolved; this is a
recorded observation, not an investigation.

**Preregistered result: no winner.** Mean y MAE ranking COMBO 0.100, R0 0.138,
OPEN_Q 0.150, OPEN 0.150, BLEND 0.255; none passed both sessions. COMBO: A y MAE
0.092, ordering 95/96, bias +0.031 (failed MAE only); B 0.109, 83/96, −0.007.
R0 calibration R² 0.707 / 0.771 (vs 0.24 / 0.21 in #75). x MAE 0.046 / 0.062,
96/96. Checkpoint repeats varied widely (mean |block3−block1| R0 0.105 / 0.163,
OPEN ≈0.5). Exploratory single-checkpoint recentering made R0/COMBO worse.

**Correction of an earlier interpretation (mine):** the 16:30 #75 entry and
RESULTS called eye opening "promising". #75 calibration was row-major, so time
trend and row were confounded; with shuffled calibration, eye opening drifted
≈0.5 screen-y and was not better than R0. A dated correction note was appended
to the #75 RESULTS without altering its original text.
Full tables: [RESULTS](../../experiments/vertical_signal_comparison/RESULTS.md).
No production change, no B2 action. Next options await Fatih's approval.

## 2026-10-08 22:00 +03:00 — Issue #77 published; review pending

Artifact commit **`9f78bc004cd382cd31e8d5cccdf9382648818439`** on
`experiment/77-vertical-signal-comparison` (after preregistration `e4cd8dc`).
Opened [PR #78](https://github.com/cagriinan46/eye-tracker/pull/78) (Closes #77),
verified OPEN, non-draft, UNMERGED. [CI run37828546276](https://github.com/cagriinan46/eye-tracker/actions/runs/37828546276)
on 9f78bc0 completed **SUCCESS**. Branch diff: 11 files, no `src/` change. This
entry is a later commit with its own CI run. No merge by the agent; Fatih
reviews and merges. Next task awaits approval.

## 2026-10-08 22:12 +03:00 — correction: PR #78 merged; Issue #79 appearance-model options

**Correction** to the PR #78 publication entry (OPEN/UNMERGED): verified,
[PR #78](https://github.com/cagriinan46/eye-tracker/pull/78) **MERGED** at
2026-10-08T19:08:12Z (22:08 +03:00) by Fatih as `5449f91921a734ca77b241d7a8fae2865dec422f`;
Issue #77 CLOSED.

**Approval:** Fatih chose option A in chat ("A ya başlayalım o zaman"): a decision
document on appearance-based gaze models, no code. **Agent:** Claude Code
(Claude Opus 5.5). **Issue:** [#79](https://github.com/cagriinan46/eye-tracker/issues/79).
**Start:** main `5449f91`, branch `docs/79-appearance-gaze-options`.

**Work:** web research (search results, the L2CS-Net arXiv abstract, the
ETH-XGaze, L2CS-Net, FAZE and UniGaze GitHub pages) and a new
[docs/research/appearance-gaze-options.md](../research/appearance-gaze-options.md).
Nothing downloaded or installed. Unsuccessful: the Noldus white paper PDF could
not be read on this Mac (no pdftotext/pdftoppm), so its figures are marked as
search-summary, vendor-reported values. The FAZE and UniGaze code license files
were not read.

**Findings:** Fatih's display is about 30.2 × 19.6 cm; the 0.08 y MAE criterion is
1.57 cm (≈1.6° at an assumed, unmeasured 55 cm). COMBO's 0.092 / 0.109 is
1.8 / 2.1 cm. Calibrated webcam systems in the literature report about 2 cm or
2°, and appearance models report 3–4° on benchmarks, so a large vertical gain
from an appearance model is not supported by published numbers. All candidate
weights are non-commercial or trained on non-commercial datasets.

**Human decisions requested:** licensing of non-commercial weights for the
prototype; a bounded L2CS-Net/ONNX spike with stop rule (option 1); designing
for coarse vertical (option 2); revisiting the 0.08 exit criterion (option 3);
running the Issue #77 protocol with Çağrı (option 4). No production change.

## 2026-10-08 22:13 +03:00 — Issue #79 published; review pending

Artifact commit **`9ad27cafb29167249d945ecdfb1c1af3c92e2ea4`** on
`docs/79-appearance-gaze-options`. Opened [PR #80](https://github.com/cagriinan46/eye-tracker/pull/80)
(Closes #79), verified OPEN, non-draft, UNMERGED. [CI run37830213613](https://github.com/cagriinan46/eye-tracker/actions/runs/37830213613)
on 9ad27ca completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih reviews and merges. The listed human
decisions are pending; no follow-up task started.

## 2026-10-08 22:42 +03:00 — correction: PR #80 merged; Issue #81 coarse zone targeting preregistered

**Correction** to the PR #80 publication entry (OPEN/UNMERGED): verified,
[PR #80](https://github.com/cagriinan46/eye-tracker/pull/80) **MERGED** at
2026-10-08T19:18:07Z (22:18 +03:00) by Fatih as `9e55af69691d3dc1463aec34bfa5aba83fff4029`.

**Approval:** Fatih chose option 3 of the Issue #79 list in chat ("3 numarayı bir
deneyelim ama eski haline de dönebilelim"): try coarse-vertical interaction design,
reversibly. **Rollback point: main `9e55af69691d3dc1463aec34bfa5aba83fff4029`.**
All work is experiment-only (`experiments/coarse_vertical_targeting/` and its
tests); `src/` is untouched; revert by not merging or `git revert` of the squash.
**Agent:** Claude Code (Claude Opus 5.5). **Issue:**
[#81](https://github.com/cagriinan46/eye-tracker/issues/81). **Branch:**
`experiment/81-coarse-vertical-targeting`.

**Design (preregistered in the README before data):** shuffled 5×5 calibration,
live COMBO y and production-style x mapping, screen-filling 3×3 (each cell ×2) and
4×4 (each ×1) grids, 34 trials, mirrored-cell cue 0.75 s, 7-frame/0.5 s median
smoothing, 1.0 s dwell on any cell selects it (wrong cells count as wrong
selections), 5.0 s timeout, shaded current-cell feedback. Pass per layout and
session: success ≥ 80% and wrong ≤ 10%; a layout passes only if A and B pass.
Session A 3×3 first, B 4×4 first.

**Checks:** 12 new tests (schedule, mapping, blink exclusion, smoother, clamping,
dwell, pass rule, schedule validation, CLI). One fixture initially made the
COMBO design rank-deficient (features were linear combinations of each other);
fixed in the fixture, not the code. `draw_grid` rendered offscreen with real
OpenCV for both layouts and all states. Full-suite results are in the commit
check below. Sessions follow after push.

## 2026-10-08 22:53 +03:00 — Issue #81 sessions: coarse zone targeting FAILED

Preregistration `e3d5237` pushed at 22:42 +03:00; full suite at that commit:
`ruff check` PASS, `ruff format --check` PASS (240 files), `pytest` **466 passed**.

**Sessions** (`--screen-size 1512x982`, camera 0, `.venv-fatih`): A 22:43:35–22:47:00,
B 22:47:54–22:51:42 after reseating; both exit 0, 25/25 calibration, 34/34
trials; reads 5,478 / 6,170, 0 failed, no-face 0 / 15. Files
`.venv/coarse-vertical-fatih-A.json` (1,054,424 B, SHA-256
`f5a4647aee03062b42c2ed51f10923c01e865f1468cb7a14cca1ae6e13024b62`) and `-B.json`
(1,271,168 B, `0c8b410270c1cba71fd524aa54a1c497d4945979b196015881de1306cccd8bc1`),
Git-ignored. All 3,699 pre-existing non-cache `.venv/` files unchanged; B2 marker
unchanged. Six MediaPipe clearcut "Failed to send" lines per run.

**Preregistered result: both layouts FAIL.** 3×3 success 22% / 44%, wrong 61% /
22%; 4×4 success 6% / 19%, wrong 75% / 31% (A / B). The 3×3 ≥ 80% exit criterion
is not met. Wrong selections were mostly one row above the target.

**Exploratory:** live estimates were biased on both axes (median y −0.19 / −0.16,
x +0.24 / +0.10), unlike Issue #77's open-loop x MAE ≈0.05; x bias grew within
trials. An open-loop constant-offset simulation from the first six trials did
not help. Possible causes (posture change, grid brightness affecting eye
opening, feedback capture) cannot be separated: frames did not log head or
eye-opening values. Details: [results record](../research/coarse-zone-targeting-results.md).

**Rollback:** no production change; rollback point main `9e55af6` unchanged.
Whether to keep this experiment and its negative result on main (recommended,
as evidence) or close the PR unmerged is Fatih's choice. Next options await
approval.

## 2026-10-08 22:54 +03:00 — Issue #81 published; review pending

Artifact commit **`d827637822c9a5655cdc2c4f55c2b4527b591770`** on
`experiment/81-coarse-vertical-targeting`. Opened [PR #82](https://github.com/cagriinan46/eye-tracker/pull/82)
(Closes #81), verified OPEN, non-draft, UNMERGED. [CI run37835375529](https://github.com/cagriinan46/eye-tracker/actions/runs/37835375529)
on d827637 completed **SUCCESS**. Branch diff 10 files, no `src/` change. This
entry is a later commit with its own CI run. No merge by the agent; Fatih decides
whether to merge (keep the negative result) or close (exact rollback to 9e55af6).

## 2026-10-08 23:05 +03:00 — Issue #81: code not merged by decision; results-only record; mirror observation

The four preceding Issue #81 entries were written on the experiment branch and
are carried to main unchanged except that the RESULTS link now points to the
results-only record below.

**Human decision (Fatih, chat):** "işe yaramadıgı için kodun degişmesine bence
gerek yok": because the experiment did not work, its code is **not merged**.
Only results and logs go to main. Claude closes
[PR #82](https://github.com/cagriinan46/eye-tracker/pull/82) unmerged and keeps
branch `experiment/81-coarse-vertical-targeting` (tip `62dc8f9`) as a
reference. Main stays at rollback point `9e55af6` plus this documentation.
Clarification given to Fatih: the branch and PR had already been pushed to
GitHub before this decision. Raw session data (`.venv/coarse-vertical-fatih-*.json`)
are Git-ignored and were never uploaded; GitHub holds only summary numbers.

**Participant observation (Fatih):** during the test, moving the eyes right
moved the feedback left and vice versa, "as if a mirror mode were on". Checked
against data: no code mirror. The live x mapping slope (−11.1 / −8.0) has the
same sign as Issue #77 (96/96 horizontal ordering), the camera image is never
flipped, and median estimated x increased with target column except in A's 4×4
block (rightmost column 0.47). Hypothesis, unproven: the features are
eye-in-head; turning the head toward the target or the shaded feedback while
fixating moves the eyes the opposite way inside the head, so the estimate moves
opposite to the head turn. Head pose was not logged during trials (design
gap). New record:
[coarse-zone-targeting-results.md](../research/coarse-zone-targeting-results.md).
No production change. Next direction awaits Fatih/Çağrı.

## 2026-10-08 23:06 +03:00 — Issue #81 results-only record published; PR #82 closed

Artifact commit **`e726a79d8576d987403f77b96f4d1884aa453afa`** on
`docs/81-coarse-targeting-results` (3 documentation files). Opened
[PR #83](https://github.com/cagriinan46/eye-tracker/pull/83) (Closes #81), verified
OPEN, non-draft, UNMERGED; [CI run37836876885](https://github.com/cagriinan46/eye-tracker/actions/runs/37836876885)
on e726a79 completed **SUCCESS**. [PR #82](https://github.com/cagriinan46/eye-tracker/pull/82)
**CLOSED unmerged** with an explanatory comment, per Fatih's decision; its branch
was not deleted. This entry is a later commit with its own CI run. No merge by
the agent; Fatih reviews and merges PR #83.

## 2026-10-08 23:37 +03:00 — correction: PR #83 merged; Issue #84 head-assisted pointing preregistered

**Correction** to the PR #83 publication entry (OPEN/UNMERGED): verified,
[PR #83](https://github.com/cagriinan46/eye-tracker/pull/83) **MERGED** at
2026-10-08T20:11:33Z (23:11 +03:00) by Fatih as `2f73004fe5a1aab71da32049d13cf08eb24c4d29`;
Issue #81 CLOSED.

**Approval:** Fatih in chat: "dikey ekseni baş hareketine baglı yapsak o nasıl olur
bunu da bir deneme gibi yapalım". Claude stated upfront that pushing the branch
puts the code on GitHub but not on main, and that failed code will not be
merged (Fatih's preference). **Rollback point: main `2f73004`.** **Agent:** Claude
Code (Claude Opus 5.5). **Issue:** [#84](https://github.com/cagriinan46/eye-tracker/issues/84).
**Branch:** `experiment/84-head-vertical-targeting`.

**Design (preregistered in the experiment README):** 15-presentation calibration
in blocks eye_x (head still), head_y and head_x ("point your nose"); 1-D OLS
lines; conditions HYBRID (eye horizontal + head pitch) and HEAD (head yaw + head
pitch); Issue #81 zone mechanics (3×3 then 4×4 per condition, 50 trials, 1.0 s
dwell on any cell, 5.0 s timeout, 7-frame/0.5 s median). Per-frame head pose, eye
features, opening and blink are now logged. Pass per condition × layout: success
≥ 80% and wrong ≤ 10% in both sessions.

**Checks so far:** 9 new tests pass; drawings rendered offscreen with real
OpenCV. Full-suite results follow in the commit check. Sessions after push.

## 2026-10-08 23:49 +03:00 — Issue #84 sessions: head pointing PASSES; hybrid fails

Preregistration `06bfbc2` pushed at 23:37 +03:00; full suite at that commit:
`ruff check` PASS, `ruff format --check` PASS (241 files), `pytest` **463 passed**.

**Sessions** (`--screen-size 1512x982`, camera 0, `.venv-fatih`): A 23:39:24–23:43:28,
B 23:44:46–23:48:40 after reseating; both exit 0, 50/50 trials; reads 6,369 / 6,087,
0 failed, no-face 18 / 114. Files `.venv/head-vertical-fatih-A.json` (3,509,097 B,
SHA-256 `b155e116942eb2adc3ecb8110241cbf6738bb8c40aa6a3916b998cea513d3aba`) and
`-B.json` (3,280,546 B, `ed54e2e36f3e6b0bb4aad879a1721934a89d20822063a7a26a25f90d7cd2529e`),
Git-ignored. All 3,701 pre-existing non-cache `.venv/` files unchanged; B2 marker
unchanged. MediaPipe clearcut "Failed to send" lines: 8 / 6.

**Preregistered result:** **HEAD passes both layouts in both sessions** (3×3 100% /
100%, 4×4 100% / 94%, one wrong selection, no timeouts; median success time
≈2.0–2.5 s including 1.0 s dwell). **HYBRID fails** (3×3 56% / 67%, 4×4 56% / 50%);
its errors were mostly wrong columns, i.e. eye-based horizontal failed while head
pitch carried the vertical. The accepted "coarse 3×3 ≥ 80%" criterion is met by
head pointing, not by eye gaze.

**Exploratory:** calibration head pitch spanned about 40–53° top to bottom (vs
≈20° physically expected at an assumed 55 cm; cause unmeasured); yaw about 30–40°.
During the "head still" eye block, yaw still drifted ≈4°, consistent with the
Issue #81 mirror/head-rotation hypothesis. Within-target head-angle SD was
0.6–1.2°. [RESULTS](../../experiments/head_vertical_targeting/RESULTS.md).

**Human decisions:** (1) whether head pointing becomes the primary pointer (scope
and architecture; Fatih and Çağrı); (2) merge this working experiment code or
keep results only (Fatih's rule). Comfort/fatigue not measured; Fatih asked to
report comfort. No production change.

## 2026-10-08 23:50 +03:00 — Issue #84 published; review pending

Artifact commit **`84e2a3ac06a640665e69f266a072452013891027`** on
`experiment/84-head-vertical-targeting`. Opened [PR #85](https://github.com/cagriinan46/eye-tracker/pull/85)
(Closes #84), verified OPEN, non-draft, UNMERGED; [CI run37842402970](https://github.com/cagriinan46/eye-tracker/actions/runs/37842402970)
on 84e2a3a completed **SUCCESS**. No `src/` change. This entry is a later commit
with its own CI run. No merge by the agent; Fatih decides between merging the
working experiment code and a results-only record.

## 2026-10-09 15:38 +03:00 — correction: PR #85 merged; Issue #86 iPhone ARKit signal checks recorded

**Correction** to the PR #85 publication entry (OPEN/UNMERGED): verified,
[PR #85](https://github.com/cagriinan46/eye-tracker/pull/85) **MERGED** at
2026-10-08T21:00:03Z (2026-10-09 00:00 +03:00) as `fe7d4a7aec0d8b7913a0e84140cb12ce678cacc8`;
Issue #84 CLOSED. Merged by Fatih's decision (working experiment code kept).

**Request (Fatih, chat):** try iPhone TrueDepth/ARKit derived numbers (no
images) as an alternative vertical gaze source; Stage 1 discovery, Stage 2
signal validation, Stage 3 `GazeSource` design only if Stage 2 is positive;
`.venv-fatih` only; no own iOS app. **Agent:** Claude Code (Claude Opus 5.5).
**Start:** main `fe7d4a7`, clean.

**Stage 1 (discovery):** web research and the open-source PyLiveLinkFace
decoder established the Live Link Face UDP 11111 format; iFacialMocap's
protocol page was read. Neither app provides `lookAtPoint` or 4×4 eye
transforms. A stdlib listener in the Claude session scratch directory (not in
the repository) was tested with synthetic packets, then with Fatih's iPhone over
his personal hotspot. Nothing was written under `.venv/`; no images or video.

**Sanity checks (Fatih in chat approved each attempt):** five runs between
14:57 and 15:31 +03:00. Run 1 free looking (Fatih had not performed the
direction looks); runs 2–3 silent on-screen dots with the phone in portrait,
**invalid vertically** because the phone covered the lower screen (Fatih's
report); run 4 **no data** because the Mac had joined another network
(172.20.34.163) and packets went to the old address; run 5 landscape, all dots
visible, 4,993 face packets, valid. Claude's early readings from runs 1–2
("lookUp barely responds", "no vertical separation") were premature and were
retracted in chat.

**Result (run 5, exploratory, not preregistered):** eye pitch separated
**down** from center in both cycles (+0.024 / +0.033 rad) but **up** only in
cycle 2; `eyeLookUp` stayed 0 throughout; top–bottom range 1.6°–4.3° vs ≈20°
physical; horizontal left/right ordering correct, ≈7° vs ≈30°. Conclusion: **no
meaningfully better vertical signal than the webcam**; Stages 2 and 3 not
started. Details, packet layout, limitations and five alternatives:
[iphone-arkit-signal-check.md](../research/iphone-arkit-signal-check.md).

**Approval for this record:** Fatih in chat, "a yı yapalım" (results-only
documentation). [Issue #86](https://github.com/cagriinan46/eye-tracker/issues/86),
branch `docs/86-iphone-arkit-signal-check`. Unresolved: source of the "y MAE
0.175" figure in the request; the next direction (head pointing decision with
Çağrı, Continuity Camera placement test, or other) awaits Fatih. No production
change.

## 2026-10-09 15:38 +03:00 — Issue #86 published; review pending

Artifact commit **`4767be84841b4480145ccbc5a1175087f3abccf9`** on
`docs/86-iphone-arkit-signal-check` (3 documentation files). Checks at that
commit with `.venv-fatih`: `ruff check` PASS, `ruff format --check` PASS (243
files), `pytest` **463 passed**, `git diff --check` clean. Opened
[PR #87](https://github.com/cagriinan46/eye-tracker/pull/87) (Closes #86), verified
OPEN, non-draft, UNMERGED; [CI run37931350933](https://github.com/cagriinan46/eye-tracker/actions/runs/37931350933)
on 4767be8 completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih reviews and merges.

## 2026-10-13 12:15 +03:00 — correction: PR #87 merged; Issue #88 camera placement preregistered

**Correction** to the PR #87 publication entry (OPEN/UNMERGED): verified,
[PR #87](https://github.com/cagriinan46/eye-tracker/pull/87) **MERGED** at
2026-10-09T12:44:00Z (15:44 +03:00) by Fatih as `e15e793d239d92e0b7282474c0ec3c213bd032ae`;
merged content identical to branch `docs/86-iphone-arkit-signal-check` (branch
not deleted). No other main change or open PR besides #71 at 2026-10-13 12:14.

**Approval:** Fatih chose option 2 of the Issue #86 alternatives ("2 yi
deneyelim") and approved the four proposal points ("1–4 tamam"): merge #87
first, a fresh official model copy, `validation/results/` output, and the
decision rule. **Agent:** Claude Code (Claude Opus 5.5). **Issue:**
[#88](https://github.com/cagriinan46/eye-tracker/issues/88). **Branch:**
`experiment/88-camera-placement-vertical` from main `e15e793`.

**Setup:** official MediaPipe `face_landmarker.task` downloaded to
`.venv-fatih/models/` (3,758,596 B, SHA-256 `64184e22…6544e0bc9ff`, identical to
DATA_INVENTORY); `.venv/` not read. `run.py` of Issue #77 now also accepts the
new Git-ignored `validation/results/` (test extended); frozen analysis
untouched.

**Design (preregistered in the
[experiment README](../../experiments/camera_placement_vertical/README.md)):**
Issue #77 protocol unchanged; sessions built-in A → iPhone (Continuity Camera,
rear, below screen) A → iPhone B → built-in B. "iPhone placement better" if all
four sessions are valid and the best iPhone candidate's mean y MAE is at least
0.02 below the best built-in one; "vertical solved" if the iPhone pair has a
#77 winner. Otherwise negative; invalid sessions make it inconclusive.

## 2026-10-13 12:35 +03:00 — Issue #88 sessions: iPhone below screen better, vertical not solved

Preregistration `b518be7` committed at 12:15:25 +03:00 and pushed before session 1; full suite at that commit:
`ruff check` PASS, `ruff format --check` PASS (244 files), `pytest` **463 passed**.

**Setup:** wireless Continuity Camera did not appear while the iPhone shared
its connection (Personal Hotspot); the USB cable worked. A no-save brightness
test (cover the iPhone lens) established **OpenCV index 0 = built-in, 1 =
iPhone**, the opposite of Swift's AVFoundation device list. Video effects off
was requested but not explicitly confirmed by Fatih.

**Sessions** (`--screen-size 1512x982`, `.venv-fatih`, model `.venv-fatih/models/`,
reseat between, results hidden until all four ended): built-in A 12:24:04–12:25:48,
iPhone A 12:26:12–12:27:57, iPhone B 12:30:05–12:31:50, built-in B 12:32:19–12:34:03;
all exit 0, 50/50 presentations, 25/25 calibration and 16/16 validation, all
valid. Git-ignored files in `validation/results/`:
`camera-placement-fatih-builtin-A.json` (2,160,959 B, SHA-256
`b44173fc6371e73a4ccbacce0cc39a31f26af0a27061983b0bfd5c50c3a46ab2`),
`-iphone-A.json` (2,182,613 B, `92182600c3bea7f1b54e18677d9bfdd18c988be6c6263cef7c2667823da1761b`),
`-iphone-B.json` (2,172,047 B, `1908bf67fe01d8f625b3a9e60a08e1aa82902a8b44b770daa7c66d261301b4cf`),
`-builtin-B.json` (2,166,134 B, `8ac448de4d3a3d49a7fc24f99301f43a1ea4eedff95cc88019c789ee491fe228`).
`.venv/` was neither read nor written. One MediaPipe clearcut "Failed to send"
line per run.

**Preregistered result:** best candidate COMBO for both cameras; mean y MAE
**0.077 iPhone vs 0.103 built-in** → **"iPhone placement better": YES** (margin
0.025 vs required 0.020). **"Vertical solved": NO** — COMBO passed iPhone A
(y MAE 0.071, bias −0.045, ordering 96/96; first single-session pass for Fatih)
but failed iPhone B on y MAE (0.084). No #77 winner for either camera.

**Exploratory:** eye opening degraded from below (OPEN R² 0.47 / 0.32);
checkpoint drift was not smaller with the iPhone (top −0.21 / −0.38). x MAE
unchanged (≈0.03–0.05). Position and sensor are confounded. Details:
[RESULTS](../../experiments/camera_placement_vertical/RESULTS.md).

**Human decisions:** whether to pursue a low/external camera (Çağrı session,
cable/stand practicality, scope), versus head pointing (#84); whether to merge
this branch's small `run.py` output-path change or keep results only. No
production change.

## 2026-10-13 12:36 +03:00 — Issue #88 published; review pending

Artifact commit **`356abc8467b2ead80e3ae5f8aac2bd749b4dd0cc`** on
`experiment/88-camera-placement-vertical` (after preregistration `b518be7`).
Opened [PR #89](https://github.com/cagriinan46/eye-tracker/pull/89) (Closes #88),
verified OPEN, non-draft, UNMERGED; [CI run38377468674](https://github.com/cagriinan46/eye-tracker/actions/runs/38377468674)
on 356abc8 completed **SUCCESS**. No `src/` change. This entry is a later commit
with its own CI run. No merge by the agent; Fatih decides between merging (with
the small `run.py` output-path change) and a results-only record.

## 2026-10-13 13:47 +03:00 — PR #89 merged; Issue #90 dual-camera preregistration

**Correction to pending state:** PR #89 (Issue #88) was **merged by Fatih** at
2026-10-13 09:40:54Z as `f042500bf272588c3f401e60e68856aefb517870`; its tree is
identical to reviewed head `cfc086f`. Main synchronized.

**Issue #90** (approved in chat, "çift kamerayla deneyelim"; preregistration
approved by Fatih, "hazır"): built-in camera (top) and iPhone Continuity Camera
(bottom, USB, #88 stand) recorded **simultaneously** with the frozen #77
protocol; tests whether fusing both cameras beats the best single camera.
Branch `experiment/90-dual-camera-vertical`. New experiment-only collector and
analysis in `experiments/dual_camera_vertical/` (two MediaPipe instances, rows
tagged per camera, derived numbers only); frozen #77 code unchanged. Decision
rule in the [README](../../experiments/dual_camera_vertical/README.md): primary
`LATE` (mean of the two cameras' COMBO predictions) better if its mean y MAE ≤
best of ten single-camera methods − 0.01; secondary `SPLIT`; "vertical solved"
if `LATE` or `SPLIT` passes both sessions; placement replication with the #88
0.02 rule. Checks before commit: `ruff check` PASS, `ruff format --check` PASS
(250 files), `pytest` **472 passed**, `git diff --check` clean.

**No-save smoke test** (scratchpad script, nothing written): lens cover dropped
index 1 brightness 149.4 → 127.8 and left index 0 at 126.3 → 127.7, so
**index 0 = built-in (top), 1 = iPhone (bottom)**. Both 1920×1080, no failed
reads; 295 loops in 22.1 s = **13.3 loops/s per camera** (vs ≈30 fps single
camera in #88), inter-camera frame gap median 16.8 ms, max 52.7 ms; face found
295/295 (top) and 277/295 (bottom, includes the covered phase); detector median
7.9 / 6.9 ms.

## 2026-10-13 13:55 +03:00 — Issue #90 sessions: LATE fusion passes both sessions

Preregistration `4be1081` (log-time correction `840e640`) pushed before session A.
Sessions (`fatih-dual`, top index 0 built-in, bottom index 1 iPhone, 1512x982,
`.venv-fatih`, reseat between, results not inspected until both ended):
A 13:49:30–13:51:16 (895 loops), B 13:52:28–13:54:14 (726 loops); both exit 0,
50/50 presentations, 50/50 common presentations, no failed reads or missing
faces; both valid. Git-ignored files: `validation/results/dual-camera-fatih-A.json`
(2,239,146 B, SHA-256 `e79a5bd935da37d891b0d110c46f2527a47b775d6d6b7e44f29929a0de809395`),
`-B.json` (1,818,053 B, `00243f5f143ef1be8cf568b87c32b6f06a6be100995a6b65b83b9f24069ed169`).
`.venv/` neither read nor written.

**Preregistered result:** `LATE` (mean of top and bottom COMBO predictions)
y MAE **0.054 / 0.057**, bias −0.039 / +0.018, ordering 96 / 94 of 96 →
**passes both sessions; vertical solved by fusion: YES**. Primary "fusion
better": **YES**, 0.056 ≤ best single (BOTTOM:BLEND 0.068) − 0.01 (margin 0.012,
0.002 above the rule). Secondary SPLIT 0.069: NO. Placement replication
(bottom best 0.068 vs top best TOP:COMBO 0.083, rule 0.02): **NO**. No
single-camera method passed both sessions.

**Exploratory / limits:** gain is largely bias cancellation between cameras
(COMBO biases A −0.005 / −0.072, B +0.086 / −0.050); LATE checkpoints drift
downward +0.03…+0.16 within ≈100 s; per-camera rate ≈13 fps; one person, one
day, ≈1.1 cm mean error on this display. Product use needs an iPhone + cable +
stand and a multi-camera Vision layer: human decision. Details:
[RESULTS](../../experiments/dual_camera_vertical/RESULTS.md).

## 2026-10-13 13:56 +03:00 — Issue #90 published; review pending

Results commit **`f43aed2dc4ea953871247de1d0e38396df805aa4`** on
`experiment/90-dual-camera-vertical`. Opened
[PR #91](https://github.com/cagriinan46/eye-tracker/pull/91) (Closes #90),
verified OPEN, non-draft, UNMERGED; [CI run 38386687457](https://github.com/cagriinan46/eye-tracker/actions/runs/38386687457)
on f43aed2 completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih decides.

## 2026-10-13 14:35 +03:00 — PR #91 merged; Issue #92 eye-sphere preregistration

**Correction to pending state:** PR #91 (Issue #90) was **merged by Fatih** at
2026-10-13 11:00:52Z as `9926105d8615481b71562ac3abba3d556c554575`; tree identical
to reviewed head `0d49a1d`. Main synchronized. Verified-merged inactive branches
`experiment/88-camera-placement-vertical` and `experiment/90-dual-camera-vertical`
deleted locally and on origin; other branches untouched.

**Human decision (Fatih, chat, 2026-10-13):** eye (gaze) control is the
priority; head pointing (#84) and other directions are secondary. The iPhone is
too costly as a camera; a standard webcam (Logitech Brio 100 or similar) is to
be bought for the low/dual-camera setup. Çağrı may revise on return.

**Issue #92** (approved in chat, "webcami almadan şimdiki laptop kameram ile
bunu bir deneyelim"; preregistration approved, "hazır"): port of the 3D
eye-sphere gaze feature from Jason Orlosky's MIT prototype
(JEOresearch/EyeTracker `Webcam3DTracker/MonitorTracking.py`) to the frozen #77
protocol on the built-in camera. Branch `experiment/92-sphere-gaze-vertical`.
New `experiments/sphere_gaze_vertical/` (extractor adds nose-PCA head-frame
rotation, nose scale and scale-normalized local iris coordinates per frame;
analysis locks eyeball centres at the first `K-center` checkpoint, radius 20 px
× width/640). The #77 collector `run()` gained optional `signal_extractor` and
`experiment` parameters (defaults unchanged). Decision rule in the
[README](https://github.com/cagriinan46/eye-tracker/blob/experiment/92-sphere-gaze-vertical/experiments/sphere_gaze_vertical/README.md) (experiment branch, not merged): primary SPHERE ≤ R0 −
0.02; secondary SPHERE_COMBO ≤ COMBO − 0.01; solved if either passes both
sessions. Checks before commit: `ruff check` PASS, `ruff format --check` PASS
(257 files), `pytest` **483 passed**, `git diff --check` clean.

**No-save smoke test** (scratchpad, nothing written; index 0, 1920×1080, 29.7 fps;
"Fatih Kamerası" still listed by macOS, index 0 = built-in per today's #90
cover test): sphere pitch median center −0.04° / −0.24°, top +1.31° / +2.52°,
bottom −3.43° / −3.69° (lock 90 frames); production vertical −0.057 / −0.064 /
−0.040 (center/top/bottom, first cycle). The feature responds in the expected
direction with a ≈5–6° top–bottom range.

## 2026-10-13 14:43 +03:00 — Issue #92 sessions: eye-sphere feature negative

Preregistration `ae48969` pushed before session A. Sessions (`fatih-sphere`,
index 0 built-in, 1512x982, `.venv-fatih`, reseat between, results not inspected
until both ended): A 14:37:44–14:39:28, B 14:40:01–14:41:45; both exit 0, 50/50
presentations, 1,775 / 1,779 rows all usable with eye-sphere numbers, no missing
faces; both valid; lock at presentation 2 (33 / 35 frames). Git-ignored files:
`validation/results/sphere-gaze-fatih-A.json` (3,346,654 B, SHA-256
`ef92422143aa95b930f57c3327cf558bf89e1653c0c97f0d669512e063768b1d`), `-B.json`
(3,355,877 B, `ec2d7f465bcc0445e628f3e84de9c284b40b7e743b6abe6fbe1e0342f521c6d5`).
`.venv/` neither read nor written. Between the smoke test and session A, Fatih
removed an accidental "h" typed into `tests/gaze/test_calibration_aggregation.py`
(never committed; tree clean before session A).

**Preregistered result: negative.** Mean y MAE SPHERE **0.140** vs R0 0.129
(primary: NO), SPHERE_COMBO 0.139 vs COMBO 0.123 (secondary: NO); no sphere
candidate passed any session (solved: NO). SPHERE calibration R² 0.66 / 0.29.
Only R0 passed one session (A 0.059). Session B had a large within-session
shift for all methods (R0 centre checkpoint 0.46 / 0.11 / 0.33); built-in COMBO
was worse than in #88/#90. Prototype's own ±5° mapping (descriptive): 0.261 /
0.076. Code not merged (Fatih's rule); kept on the experiment branch.

## 2026-10-13 14:43 +03:00 — Issue #92 results-only record

Code and full results remain on `experiment/92-sphere-gaze-vertical` (head
`a7ce540`, pushed; preregistration `ae48969`, results `6aa14ac`), **not merged**
and no code PR opened (Fatih's rule for failed experiments). This branch
`docs/92-sphere-gaze-results` carries only the
[results record](../research/sphere-gaze-vertical-results.md), this log and
CURRENT_STATE. The #77 collector's optional `signal_extractor`/`experiment`
parameters exist only on the experiment branch.

## 2026-10-13 14:44 +03:00 — Issue #92 record published; review pending

Docs commit **`c61e1924302d0d08ffc48788c1118d7147272776`** on
`docs/92-sphere-gaze-results`. Opened
[PR #93](https://github.com/cagriinan46/eye-tracker/pull/93) (Closes #92), verified
OPEN, non-draft, UNMERGED; [CI run 38392227636](https://github.com/cagriinan46/eye-tracker/actions/runs/38392227636)
on c61e192 completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih decides.

## 2026-10-31 13:53 +03:00 — Issue #143: desktop cursor glide, dwell gap hold, planner task wording

Approved by Fatih in chat ("bugün yalnızca şu üç değişikliği yap"); scope limited
to the desktop demo. Branch `feature/desktop-cursor-dwell-instructions` from
synchronized main `db3fe9a`. Calibration, UniGaze/MGaze, HeuristicFilter,
experiment data, other UI features, architecture and dependencies unchanged.

**Observations before changes:** the macOS cursor timer runs at 60 Hz but warped
straight to each new estimate (about 8 FPS for UniGaze), so it moved in jumps.
Any missing measurement (blink/eye-gap gate, lost face, late frame) reset the
whole 1.2 s dwell. All 12 tasks used the generic “X” öğesini seç wording.

1. **Cursor:** new display-only `PointerSmoother` (`src/eye_tracker/actions/window_pointer.py`)
   used by `MacOSWindowPointer`. Exponential glide toward the latest estimate,
   time constant ≈30 ms for moves ≥80 logical px up to 100 ms for small jitter;
   no overshoot/extrapolation, no movement without a valid gated sample, snap
   after a 150 ms gap, reset on viewport change. Dwell still uses the raw point.
2. **Dwell:** `RegionDwell.missing()` holds progress for at most 0.5 s after the
   last in-region observation; the gap is subtracted from observed time, so it
   can only delay a selection. Outside/other-region points, longer gaps, pause
   and layout changes still reset. Records add `dwell_max_interruption_seconds`
   and protocol suffix `12-web-control-trials-v2`. The 0.5 s value is a design
   choice (typical blink plus one ≈8 FPS frame), not a measured optimum.
3. **Wording:** `WEB_INSTRUCTIONS` (12 location-specific Turkish sentences, ≤70
   characters) in `protocol.py`, sent in the snapshot and shown by `app.js`.
   Headless Chrome render at 960×640 and 1280×800: every instruction stays on one
   line and target layout is identical to the old wording (an earlier, longer
   draft wrapped to two lines at 960 px and pushed targets to 0.995 of viewport
   height, so it was shortened).

**Local assets:** none of the UniGaze kit, GazeFollower Python/support
directory, or camera intrinsics JSON exist on Fatih's Mac (`validation/results/unigaze-preflight-kit-20261029/…`,
`~/.virtualenvs/eye-tracker-gazefollower-20261019*`, `validation/results/phone-intrinsics-cdaef08c1c6a/completion.json`);
`.venv-fatih` has no pywebview. **No camera, model or native-window run was
performed**; cursor feel and selection accuracy remain unmeasured.

**Checks (`.venv-fatih`):** `pytest tests/desktop_demo tests/test_pointer_control.py tests/test_package_imports.py`
**76 passed** (60 desktop-demo tests before the change); `ruff check .` PASS;
`ruff format --check .` PASS (354 files); `git diff --check` clean; `node --check`
on `app.js` OK. One existing test expectation changed by design (a 0.1 s gaze
loss no longer zeroes dwell progress). Full suite not run (user asked for
relevant checks only).

## 2026-10-31 13:58 +03:00 — Issue #143 published; review pending

Commit **`9a78b7076d7fc2b029c24e7d5e233db6f36467a7`** on
`feature/desktop-cursor-dwell-instructions`. Opened
[PR #144](https://github.com/cagriinan46/eye-tracker/pull/144) (Closes #143), verified
OPEN, non-draft, UNMERGED; [CI run 41194636172](https://github.com/cagriinan46/eye-tracker/actions/runs/41194636172)
on 9a78b70 completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih decides.

## 2026-10-31 14:10 +03:00 — correction: PR #144 branch commits reworded at Fatih's request

Fatih asked that commits and the PR description must not show Claude as co-author
or contributor. The "Generated with Claude Code" line was removed from the PR #144
description. With Fatih's explicit approval ("full silip"), the two unmerged task-branch
commits were reworded to drop their `Co-Authored-By: Claude` trailer and pushed with
`--force-with-lease` to `feature/desktop-cursor-dwell-instructions` only: `9a78b70`
→ `674667e`, `8b1a352` → `9b8f76f`. Trees are identical (code unchanged); the
SHAs cited in the two entries above refer to the pre-reword commits. `main`
untouched; PR still OPEN and UNMERGED; Fatih merges.

## 2026-10-31 21:05 +03:00 — correction: PR #144 merged

Verified at the start of Issue #145: [PR #144](https://github.com/cagriinan46/eye-tracker/pull/144)
is **MERGED** (2026-10-31T11:15:56Z, squash commit `8528974feed059c3234c601b5181fb172f9380c0`
on main; main CI run on 8528974 SUCCESS). The entries above recorded it as pending.
Local branch `feature/desktop-cursor-dwell-instructions` was not deleted by this task.

## 2026-10-31 21:05 +03:00 — Issue #145: opt-in performance diagnostics for the desktop demo lag

Task text pasted into the session by Fatih (measurement only; branch, commit, push
and PR requested; no merge). Issue [#145](https://github.com/cagriinan46/eye-tracker/issues/145),
branch `feature/145-desktop-perf-diagnostics` from synchronized main `8528974`.

**Reported (not measured here):** after the first calibration the web-test cursor
was smooth and accurate for 2–3 s, then jerky and late; after a second calibration
it lagged from the start. Sessions: 388 tracking / 446 processing_delayed (46.5 %
on time); 984 / 273 / 4 no_gaze (78.0 %); 673 / 686 (49.4 %); 606 / 627 (49.0 %);
almost all measurements `valid`; `latest_filter_history_ms` ≈778–821 ms.

**Code reading (no conclusion):** per processed frame the UniGaze worker runs, in
series, frame copy + undistortion + SHA-256 hashes, a ≈1.8 MB IPC round trip to
the vision worker (MGaze face/gaze + MediaPipe landmarks + diagnostics), then the
UniGaze branch (face detector + FAN landmarks, normalization, B16 forward on MPS
or CPU), mapping and HeuristicFilter. The GUI marks a valid estimate delayed when
receipt minus capture time exceeds 300 ms. `latest_filter_history_ms` is the time
from the capture three processed frames earlier; ≈800 ms is consistent with about
3–4 processed frames per second in those sessions versus 8.08 FPS measured in
PR #142 — an inference from the definition, not a measurement of cause.

**Change:** new `experiments/desktop_demo/perf.py` (`PerfRecorder`), enabled only by
`python -m experiments.desktop_demo --perf-diagnostics`. For each calibration /
check / demo segment it summarizes `first_3s` and `next_15s` (frames, processed FPS,
status counts and on-time %, eligibility, camera FPS / skipped frames, cursor poll /
lock-busy / fresh-estimate rates, CPU % of the three processes, worker peak RSS,
median/p90/max of frame age and per-stage times). Timing hooks: `runtime.py`
(request, lock wait, lock-held time, filter reset, pointer polls), `unigaze_model.py`
(`timing` request flag, `last_timing`), `desktop_worker.py` (wait, start age,
worker time, CPU, RSS), `paired.py` (`last_timing` side channel; rows unchanged),
`vision_worker.py` (cumulative CPU seconds, popped before the row), `adapter.py`
(detector / normalization / forward wall times; inference unchanged). Output is
one `[perf]` line per window and `validation/results/desktop-perf-*.json`
(≈4 KB per segment, ≤40 segments); no frames, crops, gaze points or per-frame rows.
Models, weights, calibration, 300 ms gate, dwell, PointerSmoother, UI and
dependencies unchanged. Synthetic overhead: ≈1 µs per frame record, ≈4 ms per
window summary with 2,000 frames.

**Checks (`.venv-fatih`):** `ruff check .` PASS; `ruff format --check .` PASS (356
files); `pytest` **898 passed, 16 failed**; the same 16 fail on a clean main
worktree (889 passed, 16 failed: `ModuleNotFoundError: sklearn` in
`tests/gaze/test_svr_calibration.py` and `tests/test_live_svr_demo.py`, an
environment gap; main CI is green); `tests/desktop_demo` 81 passed (9 new);
`git diff --check` clean. **No camera, model or native-window run**: UniGaze kit
and GazeFollower environments are absent on Fatih's Mac, so no real timing exists.

**Next (needs the user's run):** run command and what to share are in
`experiments/desktop_demo/README.md` ("Performance diagnostics"). Any optimization
is a separate task chosen from the measured bottleneck.

## 2026-10-31 21:15 +03:00 — Issue #145 published; review pending

Commit **`bb8a16fc9efacdb9f5ec16d39627b1c0e00af071`** on
`feature/145-desktop-perf-diagnostics`. Opened
[PR #146](https://github.com/cagriinan46/eye-tracker/pull/146) (Closes #145), verified
OPEN, non-draft, UNMERGED; [CI run 41227731035](https://github.com/cagriinan46/eye-tracker/actions/runs/41227731035)
on bb8a16f completed **SUCCESS**. This entry is a later commit with its own CI
run. No merge by the agent; Fatih decides. No real-model measurement yet.
