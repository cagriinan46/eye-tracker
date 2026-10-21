# Pre-semantic recovery point — 2026-10-21

This preserves the working source immediately before the user approved desktop-wide
semantic gaze development. It is a source checkpoint, not a disk or memory snapshot.

## Exact source identity

- Commit: `3be40615f3c4119e45ce7470edc2768449bf586f`
- Annotated tag: `checkpoint/pre-semantic-2026-10-21` (pushed to origin)
- Existing branch: `feature/gazefollower-live-trace`
- Existing PR: [#97](https://github.com/cagriinan46/eye-tracker/pull/97)
- At capture, the working tree was clean and the branch matched origin.
- PR #97 was still open; `main` was `70dbbb341d315bb88cafae7e64570bb0db158e47`.
  Checking out `main` therefore does **not** recover this exact checkpoint.

## Return to the exact source in this checkout

Run from the project directory. First inspect the status; if there is unfinished
work, commit it to its task branch or preserve it separately before switching.
Do not force checkout or discard changes. Stop any running gaze session first.

```sh
git status --short --branch
git fetch origin tag checkpoint/pre-semantic-2026-10-21
git switch --detach checkpoint/pre-semantic-2026-10-21
git rev-parse HEAD
git status --short
```

The last two commands must show the full commit above and no tracked/untracked
changes before describing the source as restored. Detached HEAD is intentional:
it opens the old revision without moving or rewriting any development branch.
If continuing development there, create a new task branch before editing.

Return to the previous branch with `git switch -` after preserving any new work.
These commands do not reset shared history or delete ignored experiment records.

## Inspect separately without switching this checkout

Choose a destination that does not already exist:

```sh
git fetch origin tag checkpoint/pre-semantic-2026-10-21
git worktree add --detach ../eye-tracker-pre-semantic-20261021 \
  checkpoint/pre-semantic-2026-10-21
```

The separate worktree does not contain this checkout's ignored experiment records.
It is suitable for inspecting the source; it is not a copy of the local data.

## Local runtime and data to preserve

- Python environment: `~/.virtualenvs/eye-tracker-gazefollower-20261019`
- Support/assets: `~/.virtualenvs/eye-tracker-gazefollower-20261019-support`
- Upstream GazeFollower: support directory's `upstream`, pinned to
  `c61ffe20cd8c16b35291e5ac198d1b76c7702290`.
- Package snapshot at the checkpoint:
  `experiments/gazefollower_baseline/requirements-macos.lock.txt`.
- Local inventory captured before semantic changes:
  `validation/results/PRE_SEMANTIC_RUNTIME_2026-10-21.json`.
  It contains installed versions, asset hashes, upstream identity and existing
  session directory names. It is ignored and must remain local.
- Preserve all of `validation/results/`, including calibration models, live traces,
  the handoff document and the consumed Stage B2 records. Do not rerun/reset Stage B2.
- Preserve `.venv`, `.venv-fatih` and all existing external environments.

The inventory is **not a backup**: hashes cannot restore deleted assets or records.
Git cannot restore ignored results, environments, OS permissions, live filter state,
camera positioning, lighting or a participant's previous session. No runtime or
participant data is uploaded with the checkpoint. A future session starts fresh;
restoring this code does not reproduce an earlier gaze accuracy result.

## Existing launch command (only when ready for a human session)

From the restored project root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python \
  -m experiments.gazefollower_baseline.run --control-pointer
```

This starts the existing preview/calibration/evaluation flow, then optional
movement-only live control. It never clicks. Tab reveals the desktop from the live
view; Escape stops. Recovery documentation and verification do not run this command.
