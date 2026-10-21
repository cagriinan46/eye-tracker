# Semantic preview feed implementation plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task.

**Goal:** Supply fresh, independently context-checked UI snapshots to a future non-activating preview without blocking gaze inference.
**Architecture:** Platform owns an ephemeral native discovery session; an app worker owns that session and publishes one immutable latest result. The pure preview coordinator gates coordinates, context freshness and opt-in before using the existing resolver.
**Tech stack:** Python standard library threads/context managers and existing pytest.
**Spec:** `docs/superpowers/specs/2026-10-21-semantic-gaze-design.md`, ADR-005, issue #108.

## Global constraints

No camera, GUI, actions, new dependencies or native handles in shared contracts/disk. Existing one-shot discovery remains available. Native references live only in a worker-owned session and are released on session exit. No cross-snapshot identity inference. This prerequisite does not claim visible live preview.

## Review focus

- Blocked native calls must not block polling or shutdown indefinitely.
- Closed or invalidated sessions cannot republish old candidates.
- Context checks must be timed from their start, so slow checks cannot look fresh.
- Coordinate mismatch, stale evidence and opt-out must clear resolver state.
- Window/display change invalidates the session even if the original context returns.

### Task 1: Scoped discovery session

Files: `platform_adapters/macos_accessibility.py`, its existing tests.
Interface: `MacOSAccessibility.session()` context manager yields an object exposing immutable `.snapshot` and `.current_context()`; all methods are worker-thread confined. Session exit permanently invalidates access. Reuse current traversal through a non-owning context wrapper, not a new algorithm.
- [x] Write tests for retained lifetime, context/display change and post-close rejection. Run RED.
- [x] Implement context/display/permission revalidation; invalidate permanently on failure. Run GREEN.

### Task 2: Latest-only feed and pure preview coordinator

Files: `app/semantic_preview.py`, `tests/app/test_semantic_preview.py`, validation README.
Interfaces: `PreviewFeed(provider, refresh_seconds=.4, check_seconds=.05, clock=monotonic)` explicit `start()`, `latest()`, `close(timeout=.1)->bool`; immutable `CheckedSnapshot(snapshot, checked_at, context_id)`; `SemanticPreview(config, max_context_age).update(gaze, checked, *, now, input_screen, enabled=False)` returns existing TargetDecision.
- [x] Write event-controlled tests for blocked work, background failures, closure, cache expiration and coordinator opt-in/coordinate/time guards. Run RED.
- [x] Implement one daemon worker, one latest slot, short publication lock; never hold it across native work. Invalidate before each new scan. Use check-start timestamp and expire from snapshot capture. No queue of frames or scans. Shutdown clears state immediately and never publishes afterward; report whether worker actually stopped.
- [x] Test and document limitations: cooperative native timeouts, bounded freshness (not instantaneous UI observation), no visible overlay/runtime wiring yet. Same-window geometry is refreshed only by rescanning.
- [x] Run full suite/lint/format, independent review, commit/push and PR for human merge.

## Execution record

Implemented inline under approved continuation. Session tests first failed on missing session(); feed tests first failed on missing module. All then passed. Independent review found no important issues; its timing-test race observation was addressed by event-gating subsequent checks. Native read-only probes started no camera/UI actions: a three-second probe observed 13 incomplete scans, zero available polls, and successful bounded shutdown. A separate diagnostic probe observed node-cap and native -25202 read failures (zero-area exclusions were also counted but are not scan failures). Coverage remains unresolved; limits were not loosened. No visible preview is claimed.
