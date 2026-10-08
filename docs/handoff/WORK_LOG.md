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
