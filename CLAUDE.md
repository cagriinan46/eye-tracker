# Claude project entry point

Handoff: **2026-10-08, Europe/Istanbul (UTC+03:00)**. Human owners: **Çağrı İnan
Çamlı** and **Muhammet Fatih Erdemir**, Konya Technical University Computer
Engineering. Fatih temporarily leads human-supervised work with Claude Opus /
Claude Code; Çağrı expects to return in 1–2 days. Claude is an engineering
collaborator: inspect evidence, propose bounded tasks, implement approved work,
test it, and leave durable records for Fatih, Çağrı, Codex and ChatGPT.

## Recover context at every new session

Read, in order:

1. This file.
2. [AGENTS.md](AGENTS.md).
3. [CONTRIBUTING.md](CONTRIBUTING.md).
4. [CURRENT_STATE.md](docs/handoff/CURRENT_STATE.md).
5. [WORK_LOG.md](docs/handoff/WORK_LOG.md), especially recent entries.
6. [PROJECT_CONTEXT.md](docs/handoff/PROJECT_CONTEXT.md).
7. [DATA_INVENTORY.md](docs/handoff/DATA_INVENTORY.md).
8. Relevant source, experiment README/RESULTS/preregistration, and governing
   [scope](docs/project-scope.md), [requirements](docs/requirements.md),
   [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and
   [accepted ADRs](docs/decisions/).

These handoff files guide navigation and task continuity. They do not override
repository governance, requirements, architecture, accepted ADRs or the
human-approved roadmap. The root README is currently a placeholder; use the
linked project documentation for substantive context. Recheck Git/GitHub facts
instead of treating a dated snapshot as live state.

## Immediate boundary

Stage B2 is **incomplete**, with no retained R1/R2 scientific decision.
Geometry-2 was consumed by the first attempt, which lost its aggregate output
at JSON serialization. PR #71 is **open, draft, unmerged, with green CI**.
Preserve it, both captures, frozen sources and the original one-shot marker.
Read [STAGE_B2_RECOVERY.md](docs/handoff/STAGE_B2_RECOVERY.md) before proposing
anything related to this failure. No recovery or real-data recomputation is
authorized by the handoff. Do not open participant captures merely to learn
the project.

## Mandatory task lifecycle

Before work, read the context above, inspect status/branch/worktrees/uncommitted
work and active issues/PRs, verify relevant evidence, and propose one bounded
task with goal, risks, scope and measurable acceptance criteria. **Obtain
Fatih's explicit approval for each new task or experiment before implementation.**
Use an approved issue where repository rules apply; an explicit human exception
may authorize a bounded documentation task. Ordinary steps inside an approved
scope need no repeated approval. Synchronize main and create a focused branch
from it, unless the approved task explicitly continues an existing branch.
Preserve unrelated changes and ignored data.

During work, keep changes within scope, preserve module boundaries and privacy /
safety, add relevant tests, and record actual observations and unsuccessful
attempts. Stop at a new human decision boundary. Never tune frozen criteria.
Keep gaze research bounded against the full assistive-product roadmap.

Before opening a PR:

1. Review the complete diff and intended-file scope.
2. Run applicable checks; normally `.venv/bin/ruff check .`,
   `.venv/bin/ruff format --check .`, `.venv/bin/python -m pytest`, and
   `git diff --check`. Record actual commands, counts and failures. Synthetic
   tests do not authorize a participant-data run.
3. Update CURRENT_STATE, append WORK_LOG, and update experiment RESULTS when
   the approved task requires it. Include failures and limitations.
4. Commit and push only the task branch, open a focused PR, and report it to
   Fatih with evidence. Record pending work as pending, never as merged.

Only a human reviews/merges approved PRs. At the next task, verify the previous
merge, synchronize main, verify merged content, append a log correction for
pending merge status, and clean only independently verified merged inactive
branches. An open PR or active worktree blocks branch deletion.

## Authority and escalation

Explicit human decisions are required for scope/roadmap changes, major or TBD
architecture, production representation selection, consumed holdout reuse,
new participant captures, external data transfers, safety-critical hardware,
and changes to frozen experimental criteria. Approval to discuss or repair
synthetic infrastructure is not approval to rerun real data.

Never push directly to main, merge PRs, bypass CI, force-push shared branches,
rewrite experiment history, retune after holdout outcomes, delete active
branches, claim unrun tests, or perform unsafe actuator experiments. The
absence of Çağrı grants no additional authority. Fatih may review and merge
following repository rules.

## End work and return control

Leave CURRENT_STATE readable in 2–3 minutes and WORK_LOG sufficient to recover
every meaningful task without chat history. Record code hashes, PR state,
production changes, tests, measurements, failures, local-data availability and
outstanding decisions. If publication metadata is not yet known, append it
after publication; do not silently rewrite an old failure or pending state.
Report branch/commit/PR, push status and clean/dirty tree. On return, instruct
Çağrı/Codex/ChatGPT to follow the same reading sequence, verify live state, and
read the newest log entries before proposing the next human-approved task.
