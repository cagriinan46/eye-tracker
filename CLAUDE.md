# Coding Agent Instructions for Claude Code

## Purpose

This file contains operational instructions for AI coding agents. It does not replace or duplicate the complete project specifications.

## Authoritative Project Context

Before making changes, read the documentation relevant to the task:

```text
docs/project-scope.md
docs/requirements.md
docs/architecture.md
docs/roadmap.md
docs/decisions/
```

Treat these sources as authoritative.

- Do not invent project requirements.
- Do not expand project scope.
- Do not contradict accepted ADRs.
- Do not silently resolve architectural decisions marked as TBD.
- If implementation requires a major unresolved architectural decision, stop implementation and report the decision that the human project team must make.

## Issue-Driven Development

Implementation work should normally begin from an approved GitHub Issue.

Before coding:

1. Read the assigned issue completely.
2. Identify its goal, acceptance criteria, affected area, dependencies, and out-of-scope items.
3. Read the relevant project documentation.
4. Inspect the existing implementation before modifying it.
5. Keep the implementation limited to the assigned issue.

Do not opportunistically implement unrelated features or expand an issue because another improvement appears useful. Report unrelated work separately instead of silently including it.

## Git Workflow

Never perform implementation work directly on `main`.

Use this workflow:

```text
approved issue
→ feature/fix/docs branch
→ implementation
→ tests/checks
→ git add
→ git commit
→ git push feature branch
→ pull request
→ human review
→ human merge
```

Agents may:

- create an appropriate feature, fix, experiment, docs, or chore branch,
- modify files within the approved task scope,
- create or update tests,
- run appropriate checks,
- `git add`,
- `git commit`,
- push the current non-main branch,
- create a pull request when explicitly requested or when the assigned workflow calls for it.

Agents must not:

- push directly to `main`,
- merge a pull request into `main`,
- force push,
- bypass branch protection,
- delete or rewrite shared history,
- change repository secrets or credentials,
- perform destructive Git operations unless explicitly authorized by a human.

Before creating a new branch, ensure it starts from the current synchronized `main` unless the task explicitly requires another base.

## Branch Naming

Use short, task-focused branch names.

Examples:

```text
feature/gaze-calibration
feature/blink-detection
fix/camera-reconnect
experiment/gaze-baseline
docs/architecture
chore/agent-instructions
```

When a GitHub Issue number exists, it may be included:

```text
feature/12-gaze-calibration
```

Do not create long-lived personal branches such as:

```text
cagri
fatih
codex
claude
development
```

## Commit Rules

Keep commits focused and understandable. Prefer conventional-style messages such as:

```text
feat: add camera capture module
fix: handle camera disconnect
test: add gaze calibration tests
docs: update calibration experiment notes
chore: configure linting
```

Do not combine unrelated changes in one commit. Multiple local commits are allowed when useful. The final branch must contain only changes relevant to the assigned task.

## Scope Discipline

Modify the smallest reasonable area of the repository.

Before changing a public interface used by another module, determine whether the assigned issue requires that change.

Avoid unnecessary:

- refactoring,
- file renaming,
- dependency additions,
- architectural redesign,
- formatting of unrelated files,
- abstraction layers,
- framework changes.

Do not modify unrelated files merely to make them cleaner.

## Architecture Boundaries

Preserve the approved conceptual dependency flow:

```text
vision
   ↓
gaze / gestures
   ↓
intent
   ↓
actions
   ↓
platform / hardware
```

Important rules:

- Vision must not execute OS actions.
- Gaze estimation must not directly move or click the pointer.
- Gesture detection must not directly execute actions.
- Intent must remain independent of macOS and Windows APIs.
- Platform adapters contain OS-specific execution details.
- Hardware communication remains isolated from desktop platform control.
- Hardware must not depend on gaze implementation internals.
- `app` should coordinate components rather than absorb core algorithms.
- Do not introduce a generic `ai/` module merely because a feature may use machine learning.

## Local-First and Privacy Rules

Core interaction must remain local-first.

Do not introduce an external service dependency into:

- camera processing,
- gaze estimation,
- gesture detection,
- intent processing,
- computer control,
- assistive hardware control.

Do not upload raw camera frames, facial imagery, or raw biometric imagery to external services during normal system operation.

If a task appears to require a network dependency in the core interaction path, report it for human review before implementing it.

## Safety Rules

When hardware is involved:

- follow all SAFE requirements in `docs/requirements.md`,
- uncertain state must prefer no movement,
- communication failure must not create uncontrolled actuator movement,
- software control must not be treated as the only physical safety mechanism,
- do not weaken emergency-stop or movement-limit behavior.

If physical safety behavior is uncertain, stop and request human review rather than guessing.

## AI and Machine Learning Rules

Do not introduce machine learning merely to increase perceived project complexity. Prefer the simplest approach that satisfies the requirement.

Machine learning may be introduced only when:

- simpler approaches have been evaluated,
- there is a clear technical reason,
- the improvement can be measured.

Do not train or add large models without explicit approval. Do not make externally hosted AI services part of the critical accessibility-control path without explicit architectural approval.

## Dependencies

Do not add a dependency without a concrete need for the assigned issue.

Before adding one:

1. Verify that existing project dependencies or the standard library cannot reasonably solve the problem.
2. Prefer actively maintained and appropriate libraries.
3. Keep the dependency limited to the relevant subsystem.
4. Report significant dependency additions in the task summary.

Do not add infrastructure or frameworks for future use.

## Testing and Validation

Implementation is not complete merely because the code runs once.

Where applicable:

- add or update automated tests,
- run relevant existing tests,
- run lint or static checks configured by the repository,
- validate acceptance criteria,
- report anything that could not be tested.

Experimental work should record measurements instead of relying only on subjective observations. Never invent test results.

## Documentation

Update documentation only when the assigned issue requires it.

Important engineering decisions must not be buried only in code comments or chat history.

If implementation reveals a major architectural decision that should become an ADR:

- do not create or approve the decision autonomously,
- report the proposed decision to the human team,
- wait for approval before documenting it as Accepted.

## Collaboration

This is a two-developer project in which both developers may use separate AI coding agents. Optimize work for parallel development.

- Respect module boundaries.
- Keep pull requests focused.
- Minimize unrelated file changes.
- Avoid broad repository-wide refactors.
- Avoid modifying files likely owned by another active issue unless necessary.
- Clearly report cross-module changes.

Do not assume another agent's chat context is available. The repository and its documentation are the shared source of truth.

## Human-Controlled Decisions

The AI coding agent must not autonomously:

- change project scope,
- change the approved roadmap,
- accept new architectural directions,
- change target operating systems,
- weaken privacy constraints,
- weaken safety constraints,
- merge into `main`,
- redefine project goals,
- substantially expand a GitHub Issue.

These decisions belong to the human project team.

## End-of-Task Procedure

Before declaring a task complete:

1. Review the diff.
2. Verify only intended files were changed.
3. Run relevant tests and checks.
4. Confirm acceptance criteria where applicable.
5. Check `git status`.
6. Commit the approved task changes.
7. Push only the non-main working branch.

Then report:

- what was implemented,
- files changed,
- tests and checks executed with their results,
- branch name,
- commit hash,
- push status,
- whether the working tree is clean,
- any unresolved risks, failures, or decisions requiring human input.

Never claim success for tests or commands that were not actually executed.

## Important Principle

The goal is not to produce the maximum amount of code.

Produce the smallest correct, testable, maintainable change that satisfies the approved issue while preserving the project's architecture, accessibility goals, privacy requirements, and safety constraints.
