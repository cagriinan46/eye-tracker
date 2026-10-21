# Opt-in semantic desktop preview implementation plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task.

**Goal:** Connect the measured gaze stream to an optional, non-activating target outline.
**Architecture:** Existing app feed/resolver consumes gaze; native adapter owns a separate macOS UI process. A bounded shared latest-value mailbox holds rectangle and absolute monotonic expiration. Child event loop independently hides expired geometry.
**Tech stack:** Existing Python standard library, AppKit/Quartz bridge already installed.
**Spec:** Approved semantic design and ADR-005; issue #112.

## Global constraints

Default off, explicit CLI opt-in and Tab; mutually exclusive with pointer control. No actions, raw-gaze modifications, model changes or new dependencies. Single display, exact logical dimensions, no guessed scaling. Native visual/focus validation is pending; do not start a camera or GUI session during implementation.

## Review focus

- Inference stalls/parent death must expire the outline without another gaze update.
- Invalid gaze/context and noncandidate decisions hide immediately on receipt.
- Renderer cannot become key/main, intercept mouse input or expose actionable AX children.
- Unsupported coordinates/display changes hide rather than remap.
- Exceptions and Escape must release feed/helper resources.

### Task 1: Expiring native outline adapter

Files: `platform_adapters/macos_outline.py`, corresponding tests.
Interfaces: `visible_rect(values, now, size)` validates five floats (x,y,width,height,expires_at); `MacOSOutline(size)` exposes start/check_stop/show(rect,expiry)/hide/close. Helper uses AppKit accessory policy, nonactivating panel, no activate/makeKey calls. Shared geometry only, no images/UI text.
- [x] Write RED tests for expiry, invalid/oversized/offscreen geometry, top-left to Cocoa conversion and non-key panel configuration using fakes.
- [x] Implement helper mailbox, own event-loop expiry, Escape, screen revalidation and bounded shutdown. GREEN tests.

### Task 2: Live coordinator and integration

Files: `app/live_semantic_preview.py`, GazeFollower run.py, tests, experiment README.
Interfaces: injected `LiveSemanticPreview(feed, outline, screen, ...)` exposes activate/check_stop/update(point,captured_at,desktop)/close. Default development config radius50, margin10, stable0.1s, gap0.2s, snapshot0.5s, gaze0.2s; context age0.15s; outline lifetime min(input freshness deadlines, now+0.12s).
- [x] Write RED tests for opt-in, Tab, no move calls, tracking loss, candidate expiration, cleanup and mutually exclusive CLI options.
- [x] Implement optional path; log semantic decision status only. Existing live path unchanged when off. GREEN tests.
- [x] Full suite, lint/format, independent review; docs state native visual test not run; commit/push/PR.

## Execution record

Implemented inline under approved continuation. Pure renderer/coordinator modules and live integration tests were observed failing before implementation, then passed. Independent review found no important issues. Its failed-process-start cleanup observation was reproduced by a failing test and corrected with successful-start tracking. Helper-loop expiry was tested with fake AppKit/Quartz and an unchanged mailbox, not a native window. At initial implementation native validation was unrun; the subsequent smoke results are recorded below. No human gaze or camera session was launched. Separate helper process was chosen to keep outline expiry independent of blocking camera inference; OS scheduling still prevents a hard realtime guarantee.


### Native smoke follow-up

A camera-free synthetic outline smoke check verified WindowServer bounds, unchanged
frontmost application/focused AX window and unchanged center hit-test in one context;
expiry and helper shutdown succeeded. It exposed PyObjC double-release warnings from
manual pool draining. Replaced that with objc.autorelease_pool, verified RED/GREEN
fake-loop pool lifecycle coverage and repeated native smoke without the warnings.
Pixel rendering quality and human gaze accuracy remain unmeasured.
