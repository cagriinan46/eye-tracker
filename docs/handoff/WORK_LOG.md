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
