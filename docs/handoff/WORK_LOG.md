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
