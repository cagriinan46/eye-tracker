# Semantic Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Produce a bounded, read-only macOS target-discovery adapter and diagnostic command that return portable UI snapshots with explicit failure states.

**Architecture:** Immutable contracts live in intent. A macOS native bridge supplies a bounded collector in the platform adapter; neither can execute UI actions. A standalone diagnostic command exercises discovery outside the camera/gaze loop.

**Tech Stack:** Python 3.12, standard-library ctypes, macOS ApplicationServices/CoreFoundation, pytest and Ruff; no new runtime dependency.

**Spec:** [Approved first-slice design](../specs/2026-10-21-semantic-gaze-design.md) and [ADR-005](../../decisions/ADR-005-semantic-target-resolution.md).

Status: ready for implementation-plan review. Recommended execution: native (same session), with independent review at the end. Product code has not been changed.

## Global Constraints

- Local-only; no camera, screenshot, UI title, URL, document/input value or password reads.
- Do not move the pointer, click, scroll, type, change focus or launch applications.
- Lazy native imports; shared contracts and fake-backend tests run without macOS.
- Preserve the checkpoint, all existing environments/results and Stage B2 records.
- No changes to gaze models, calibration, filtering or existing live behavior.
- Unsupported, incomplete or uncertain context produces no selectable targets.
- Human merge only. Start implementation from synchronized main after the documentation PR is merged; preserve open branches. PR #97 is needed before later live-trace integration, not this standalone discovery task.

## Review Focus

1. Hidden menu entries advertise actions: require verified bounds and hit testing (Task 2).
2. Partial traversal misses competing controls: discard targets on truncation/error (Task 2).
3. Application/window changes during collection: invalidate the entire snapshot (Task 2).
4. Native reference leaks or an unresponsive app: release on every path, bounded calls (Task 2).
5. Custom-rendered/nested UI and multiple displays: explicit unsupported coverage; no guessed geometry (Tasks 1–3).

## Scope and follow-ups

This plan implements the first independently testable deliverable of the approved
design: discovery and shared contracts. Target ranking/temporal selection, synthetic
method comparison and live highlighting are subsequent tasks, not claimed complete
by this adapter. Keeping them separate allows rejecting a discovery strategy before
coupling it to gaze. A standalone diagnostic is the observable result of this plan.

### Task 1: Portable snapshot contracts

**Files:** Create `src/eye_tracker/intent/targets.py`; test `tests/intent/test_targets.py`.

**Interfaces:** Frozen slotted dataclasses: `TargetRect(x, y, width, height)` with
`center` and `distance_to(x, y)`; `UITarget(target_id, role, rect, enabled, category)`;
`UISnapshot(snapshot_id, captured_at, context_id, screen, targets, status)`.
Coordinates are logical screen points with top-left origin; time is monotonic
seconds. IDs/context are opaque strings, targets an immutable tuple. Status is one
of `ok`, `unavailable`, `incomplete`, `context_changed`, `unsupported_coordinates`.
Only `ok` may carry targets. IDs are unique within a snapshot, not persistent labels.

- [ ] Write tests: rectangle `(10,20,30,40)` has center `(25,40)`, distance zero at `(15,25)` and ten at `(0,25)`; negative screen origins are allowed; NaN/infinite values, nonpositive sizes and duplicate IDs raise `ValueError`; non-ok snapshots carrying targets raise `ValueError`.
- [ ] Run `python -m pytest tests/intent/test_targets.py -q`; confirm missing-contract failure.
- [ ] Implement the contracts and validation, with no platform/native imports.
- [ ] Run those tests and import the module on CI's non-macOS environment; all must pass.
- [ ] Commit `feat: add portable UI target snapshots`.

### Task 2: Native access and bounded visible-target collection

**Files:** Create `src/eye_tracker/platform_adapters/_macos_ax.py`, `src/eye_tracker/platform_adapters/macos_accessibility.py`; tests in `tests/platform_adapters/test_macos_accessibility.py` and `tests/platform_adapters/test_macos_ax.py`.

**Interfaces:** `DiscoveryLimits(max_nodes=512, max_depth=20, max_children=128, seconds=0.5, message_timeout=0.05)` validates positive finite bounds.
`MacOSAccessibility(backend=None, limits=None, clock=time.monotonic).snapshot() -> UISnapshot` is a synchronous one-shot operation; it is never called from the camera loop in this task.
The injected backend is a context manager owning all native references. Operations:
`trusted() -> bool`, `context() -> str | None`, `screen() -> TargetRect`,
`roots() -> tuple[object,...]`, `children(node, limit) -> (tuple[object,...], bool)`,
`describe(node) -> (role, rect | None, enabled | None, tuple[action,...])`,
`hit_test(x,y) -> object | None`, `parent(node) -> object | None`, `same(a,b) -> bool`.
Child-list boolean indicates truncation; native errors raise a typed internal exception.
Roots are the foreground application's focused window and top-level menu bar.

- [ ] Write fake-backend tests: permission denial returns unavailable with no traversal; offscreen/disabled/occluded targets are excluded; an action alone cannot make a hidden menu item eligible; an unrelated hit-test result rejects the target; a verified descendant is accepted only within the depth bound.
- [ ] Add tests: every node/depth/children/time cap, unreadable required state, or context change clears all targets and returns the corresponding status; cycles terminate; stale handles cannot escape the backend context; references close even after an exception. Multiple displays return unsupported_coordinates in this first adapter, rather than guessed offsets.
- [ ] Run both test files and confirm failure before implementation.
- [ ] Implement lazy native bindings with exact ctypes signatures checked against current official docs and local SDK headers. Native reference wrappers retain/release ownership explicitly. Bind no AX action/set-value functions. Never prompt for permission or turn on app accessibility through mutation.
- [ ] Implement traversal with visited-node detection, incremental child retrieval and all limits. Known unsupported attributes on non-target structural nodes are not errors; unknown required target geometry/state is incomplete. Start with pressable button, checkbox, radio-button, popup-button and link roles. Skip closed menu subtrees; do not classify custom containers or unknown action roles as targets.
- [ ] Clip the target rectangle to its visible window/screen intersection; hit-test that intersection's center. Keep only enabled controls with supported actions and proven hit-test identity/ancestry. Ancestor traversal is bounded. Do not claim that a center hit test proves an entire rectangle is visible.
- [ ] Read context before/after traversal; reject changes. Status `ok` means the declared supported-role scan completed, not universal UI coverage. Document excluded roles. Time budget is cooperative; each IPC has a timeout, but no hard realtime deadline is claimed.
- [ ] Run fake tests plus a native opt-in no-action smoke test. Record actual supported controls and latency without UI strings. Failures must produce explicit unavailable/incomplete results, never synthetic targets.
- [ ] Commit `feat: inspect macOS UI targets without actions`.

### Task 3: Standalone diagnostic and verification

**Files:** Create `validation/semantic_targets.py`, `tests/validation/test_semantic_targets.py`; update `validation/README.md`.

**Interfaces:** `main(argv=None, *, provider=None) -> int`; command `python -m validation.semantic_targets` performs one discovery pass and emits JSON containing status, role counts, target count, elapsed time and configured limits. No titles, coordinates, window identifiers or native handles are printed by default. Exit 0 for a complete supported scan (including zero targets), 2 for explicit unavailable/incomplete/unsupported context.

- [ ] Write tests: injected complete/empty/failed snapshots produce the expected status/exit code; no implicit permission prompt or camera construction; output excludes UI content; importing the CLI does not initialize native APIs.
- [ ] Run `python -m pytest tests/validation/test_semantic_targets.py -q`; confirm failure.
- [ ] Implement the one-shot command and document role/foreground-window/single-display coverage and cooperative timeout limits. This is a diagnostic, not a background service or gaze integration.
- [ ] Run the targeted tests, then the repository suite in the existing development environment with its archival-environment guard. Run `ruff check .`, `ruff format --check .`, and `git diff --check`. Do not install over any existing environment.
- [ ] Inspect the native result in at least two already-open application contexts if available without switching focus automatically. Record unavailable coverage honestly; request user participation later only if it is necessary. Do not initiate a gaze session.
- [ ] Review the final diff for forbidden reads/actions, leaks and missed failure states. Commit `feat: add read-only semantic discovery diagnostic`; push the feature branch and open a PR with actual test/coverage results and human merge status.

## Completion boundary

The deliverable passes when contracts, failure behavior and read-only discovery are
tested and the diagnostic can report a real or explicitly unavailable snapshot.
Native success on one application is not universal coverage. Report target counts
separately from actual gaze-selection accuracy, which this task cannot measure.

Next plan: pure target resolver plus synthetic comparisons; then background snapshot
refresh and non-activating live highlight. Those steps must enforce stale snapshot
rejection and coordinate consistency before integration with existing gaze output.
