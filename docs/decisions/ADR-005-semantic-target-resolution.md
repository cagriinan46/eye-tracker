# ADR-005 — Semantic Target Resolution and Platform Discovery

## Status

Accepted by the user on 2026-10-21 after review of the first-slice design and
clarification of the macOS-first, Windows-portable implementation sequence.

## Context

Approximate webcam gaze can miss small interface controls. The user approved moving
UI-aware target assistance to Phase 2 and clarified that it must work across desktop
applications, not only a browser. Core target reasoning must remain portable to
Windows while initial native integration is validated on macOS.

## Decision

- Read accessible UI geometry, actionability and context through read-only platform
  adapters. macOS APIs remain in the macOS adapter; Windows gets a separate adapter.
- Put platform-independent target/snapshot contracts and target resolution in the
  intent subsystem. The app passes snapshots to the resolver; intent does not call
  OS APIs. A target candidate is not an activation intent.
- Begin with native accessibility and deterministic, measurable selection rules.
  No screenshot/OCR/model dependency is introduced for this first slice.
- Reject incomplete, stale, ambiguous or unavailable context. UI action metadata
  alone does not prove visibility or user intent.
- Validate discovery and resolution before opt-in target highlighting. Pointer
  snapping follows measured targeting; gesture/dwell activation remains a separate
  later step. Keep the coordinate-only baseline and raw gaze unchanged.
- Implement native access on macOS first and test shared logic without OS APIs.
  Windows native behavior requires later implementation and on-device validation;
  portability is not a claim of current Windows feature support.

## Consequences

This resolves the placement question from architecture section 20 while preserving
ADR-003. Applications that do not expose usable accessible elements can remain
unsupported. Unknown visibility or incomplete neighborhoods can cause abstention;
coverage must be reported alongside target-selection accuracy.

The first slice does not authorize automatic clicks, model changes, human test
sessions, broad new platform abstractions or accepting predicted targets as labels.
Native budgets, supported-role coverage and performance will be measured through
bounded implementation tasks.

See the [approved design](../superpowers/specs/2026-10-21-semantic-gaze-design.md).
