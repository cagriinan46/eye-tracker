# ADR-003 — Modular Architecture and Platform Isolation

## Status

Accepted

## Context

The system combines computer vision, gaze estimation, gesture detection, intent interpretation, desktop control, and assistive hardware communication. These concerns contain different uncertainties and may change at different rates. The two-person team and AI coding agents also need to work on separate areas with minimal coupling and Git conflicts throughout the 28-week project.

## Decision

The core processing flow is conceptually:

```text
Vision
  ↓
Gaze / Gesture
  ↓
Intent
  ↓
Action
  ↓
Platform / Hardware
```

Responsibilities must remain separated according to these boundaries:

* Vision extracts visual information but does not execute operating-system actions.
* Gaze estimates user gaze but does not control the mouse directly.
* Gesture detection reports physical signals but does not directly trigger clicks.
* Intent determines what the user appears to want to do.
* Action dispatches validated intent.
* Platform adapters contain macOS- or Windows-specific execution details.
* Hardware modules handle assistive hardware communication separately from desktop platform control.

## Consequences

* Reduced coupling makes individual modules easier to understand and test.
* Two developers can work on separate modules in parallel with fewer Git conflicts.
* AI coding-agent tasks can be constrained to clear module boundaries.
* Uncertain algorithms can change without requiring unrelated parts of the system to be rewritten.
* macOS- and Windows-specific differences can be handled without entering core gaze, gesture, or intent logic.
* The project will contain more explicit module boundaries than a single-script prototype.
* The additional structure creates some coordination and interface overhead, but it is justified by the 28-week project scope and multi-developer workflow.
