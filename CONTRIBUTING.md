# Contributing

This guide defines the collaboration workflow for the two human developers and the AI coding agents they use. The repository documentation is the shared source of truth.

## Development Model

The project uses a lightweight GitHub Flow style.

`main` must represent the latest reviewed and accepted state of the project. Human developers and AI coding agents must not perform normal development directly on `main`.

Work should flow through:

```text
approved issue
→ task branch
→ implementation
→ tests/checks
→ push
→ pull request
→ review
→ CI
→ squash merge
→ delete branch
```

## Starting New Work

Before starting a new task after previous work has been merged, update the local `main` branch:

```bash
git switch main
git pull origin main
```

Then create a new task-focused branch from the updated `main`.

Do not continue new unrelated work on an old branch.

## GitHub Issues

Meaningful development tasks should normally have an approved GitHub Issue before implementation begins.

Issues should define:

* goal,
* acceptance criteria,
* affected area,
* dependencies where applicable,
* out-of-scope items.

Issues should be small enough to review independently. Do not create giant issues covering an entire project phase.

The project roadmap defines direction. GitHub Issues define concrete work.

## Task Ownership

Each active issue should have one primary owner. The owner may use Codex or Claude Code to implement the task.

Avoid having both developers independently implement the same issue.

If a task must touch files currently being modified by another active task, coordinate before making overlapping changes.

## Branches

Use short-lived task branches.

Examples:

```text
feature/12-gaze-calibration
feature/18-blink-detection
experiment/21-gaze-baseline
fix/31-camera-reconnect
docs/requirements
chore/ci
```

Do not use long-lived personal branches such as:

```text
cagri
fatih
codex
claude
dev
development
```

Branches should normally live only for the duration of one task.

## Commits

Commits should be focused and understandable.

Prefer messages such as:

```text
feat: add gaze calibration flow
fix: handle camera disconnect
test: add blink detector tests
docs: document gaze experiment
chore: configure CI
```

AI coding agents may automatically stage, commit, and push changes on their own non-main task branches.

Humans remain responsible for reviewing the resulting changes before merge.

## Pull Requests

Every change intended for `main` should normally enter through a Pull Request.

Pull Requests should:

* solve one primary issue,
* stay focused,
* explain what changed,
* explain how it was tested,
* reference the related issue where applicable,
* mention unresolved limitations or risks.

Avoid mixing unrelated refactors or features into the same Pull Request.

## Review

The developer who did not primarily own the task should review the Pull Request where practical.

The reviewer should check:

* whether the issue acceptance criteria are satisfied,
* whether the change respects architecture boundaries,
* whether unrelated files were modified,
* whether the implementation is understandable,
* whether tests are appropriate,
* whether new dependencies are justified,
* whether documentation needs updating,
* whether any architectural decision should be escalated into an ADR.

AI-generated code must still be understood by the human team. “An AI wrote it” is not sufficient justification for merging code that the team cannot explain.

## CI Requirement

Configured CI checks should pass before merge.

Initial checks may include:

* linting,
* automated tests.

Later checks may include:

* integration tests,
* macOS build validation,
* Windows build validation.

Do not bypass failing CI without understanding and documenting the reason.

## Merge Strategy

Use **Squash and merge** for normal Pull Requests.

The resulting commit on `main` should have a clear message describing the completed change.

After a successful merge, delete the merged task branch unless there is a concrete reason to retain it.

## Handling Merge Conflicts

Merge conflicts are normal but should remain small.

If another task was merged while a branch is still active, synchronize with the latest `main` before opening or finalizing the Pull Request.

Prefer the following when appropriate:

```bash
git fetch origin
git rebase origin/main
```

Coordinate before rebasing a branch that another person or agent may be using. If rebasing a published branch would require rewriting shared history, use a non-destructive alternative unless a human explicitly authorizes otherwise.

Resolve conflicts carefully and rerun relevant tests afterward.

Do not use destructive Git commands merely to make conflicts disappear.

If frequent large conflicts occur, treat that as a sign that issue boundaries or module boundaries may need improvement.

## Parallel Development

The architecture is designed to support parallel work. Prefer assigning tasks to separate modules when possible.

Example:

```text
Developer A:
gaze / calibration

Developer B:
gestures / experimental tooling
```

This is not a permanent ownership model. Developers may work in different areas across different tasks.

The goal is to reduce concurrent edits to the same files.

## Working With AI Coding Agents

Codex and Claude Code are implementation tools, not independent project managers.

The human team determines:

* roadmap direction,
* issue priority,
* project scope,
* architecture decisions,
* merge decisions.

Agents may:

* implement approved issues,
* create task branches,
* run tests,
* stage changes,
* commit,
* push their task branch,
* create Pull Requests according to repository instructions.

Agents must not autonomously merge into `main`.

Important project knowledge must be stored in repository documentation rather than existing only inside ChatGPT, Codex, or Claude conversations.

## Architectural Decisions

If implementation reveals a significant unresolved architectural choice:

1. Do not silently make the decision inside a feature Pull Request.
2. Bring the decision to the human project team.
3. Compare realistic alternatives.
4. Record the approved decision as an ADR when appropriate.
5. Continue implementation according to the approved decision.

Small implementation details do not require ADRs.

## Experiments

Experimental work should use dedicated experiment tasks or branches when appropriate.

Experiments should record:

* hypothesis or question,
* setup,
* relevant measurements,
* result,
* conclusion.

A failed experiment is acceptable. Do not hide negative results if they materially affect engineering decisions.

Experimental code does not automatically become production architecture.

## Definition of Done

An AI agent may finish its implementation handoff after pushing a task branch, but the team task remains open until the applicable review and merge steps below are complete.

A task is considered complete when applicable:

* issue acceptance criteria are satisfied,
* code or documentation has been reviewed,
* relevant tests and checks pass,
* no unrelated changes remain,
* documentation is updated if necessary,
* unresolved risks are stated,
* Pull Request is approved,
* CI passes,
* change is squash-merged into `main`.

## Team Principle

Optimize for:

* small changes,
* clear ownership,
* understandable code,
* measurable results,
* low-conflict parallel work,
* human review of AI-generated implementation.

The goal is not to maximize development speed at the expense of understanding or reliability.
