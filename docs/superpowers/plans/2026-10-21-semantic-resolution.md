# Semantic target resolution implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Resolve a conservative, non-activating UI candidate from logical gaze coordinates.
**Architecture:** Pure intent code consumes immutable UISnapshot values. Evidence is local to a snapshot, target and caller-supplied current context. A synthetic harness compares three methods without camera or platform imports.
**Tech Stack:** Python standard library and existing pytest.
**Spec:** `docs/superpowers/specs/2026-10-21-semantic-gaze-design.md`, ADR-005.

## Global constraints

- No new dependencies, native calls, actions, camera, live preview or calibration changes.
- Preserve raw gaze. Scores are geometric distances, not probabilities.
- Require complete, fresh snapshots and current matching context.
- Snapshot-local identities cannot establish continuity across scans.
- All thresholds explicit and configurable; synthetic values are development settings, not validated user defaults.

## Review focus

- Repeated/out-of-order timestamps must not manufacture sustained evidence.
- Changing snapshots or geometry with reused IDs must clear evidence.
- Competing nested/overlapping targets must cause abstention.
- Invalid, off-screen or stale gaze must immediately clear a candidate.
- Large time gaps and context changes must require fresh evidence.

### Task 1: Pure resolver and regression tests

**Files:** create `src/eye_tracker/intent/targeting.py`, `tests/intent/test_targeting.py`.
**Interfaces:** frozen `TargetingConfig(radius, separation, stable_seconds, max_sample_gap, max_snapshot_age, max_gaze_age)`; frozen `GazePoint(x, y, captured_at, valid=True)`; frozen `TargetDecision(status, target=None)`; `TargetResolver(config).update(gaze, snapshot, *, now, context_id)`; stateless `select_target(..., method='coordinate'|'nearest')` for comparisons.

- [x] Write tests for clear target acquisition after sustained samples, ambiguity including equal/nested distances, bounded radius, disabled/non-press exclusion, stale/future/invalid inputs, screen bounds, wrong context, snapshot/geometry replacement, nonmonotonic clocks and gaps. Assert no candidate target is attached to abstentions.
- [x] Run targeted pytest; expect missing-module failure before implementation.
- [x] Implement rectangle-distance ranking. Compare runner-up even beyond radius. Require distance gap >= separation; ties always ambiguous. Evidence key includes whole immutable snapshot, target identity and context. Require strictly increasing sample and update times. Reset on every abstention; pending evidence survives only consistent eligible samples with bounded gaps. Validity windows are inclusive. Reject targets whose centers are outside screen.
- [x] Run targeted pytest; expect pass.

### Task 2: Deterministic comparison harness and documentation

**Files:** create `validation/semantic_resolution.py`, `tests/validation/test_semantic_resolution.py`; update `validation/README.md`.
**Interfaces:** `run_comparison()` returns JSON-serializable scenario/method metrics; `main()` prints them. Each independent scenario declares intended target and sample sequence before running algorithms.

- [x] Write tests asserting all three methods are reported, all samples accounted for, isolated offset benefit, dense ambiguity abstention, and loss clearing. Verify JSON CLI output.
- [x] Run tests before implementation, expect missing-module failure.
- [x] Implement isolated offset, dense boundary, nested overlap and tracking-loss scenarios. Report correct/wrong/abstention counts, candidate-to-candidate switches and first-correct time (null if absent). Coordinate baseline requires unique containment; nearest baseline uses radius without temporal/separation requirements but abstains on exact ties. Both share validity gates.
- [x] Run comparison and tests. Document explicit development settings, snapshot-local reset cost, no activation and no human accuracy claims.
- [x] Full suite, Ruff lint/format, diff check, fresh review; commit, push and PR for human merge.

## Execution record

Implemented inline under the already approved design and continuation instructions. Both test modules first failed because their implementation modules did not exist, then passed after implementation. Independent review found no important bugs; additional clock/gap regression coverage was added. No architectural deviations or deferred findings. Synthetic output is reproducible and is not a human-accuracy claim.
