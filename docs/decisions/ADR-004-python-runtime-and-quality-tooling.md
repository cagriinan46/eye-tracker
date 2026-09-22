# ADR-004 — Python Runtime and Quality Tooling

## Status

Accepted

## Context

The project needs a consistent development runtime and minimal shared quality and testing tooling before feature implementation begins.

The project is developed by two developers using separate AI coding agents, so local development and CI behavior should remain consistent, understandable, and simple. The initial toolchain should avoid unnecessary complexity while supporting automated validation of future implementation work.

## Decision

The project adopts the following initial development toolchain:

* Python 3.12 is the initial project runtime.
* pytest is the Python test runner.
* Ruff handles Python linting and formatting.
* GitHub Actions provides Continuous Integration.
* Standard `venv` and `pip` provide the current local environment and dependency workflow.
* More complex dependency or environment tooling will be considered only if a concrete need emerges.

This decision does not select or resolve:

* a computer-vision framework,
* MediaPipe usage,
* OpenCV usage,
* a GUI framework,
* the packaging or distribution strategy,
* production runtime dependencies,
* the gaze-estimation algorithm.

These remain separate decisions.

## Consequences

* Developers have a simple and consistent onboarding path.
* Local and CI checks use the same shared configuration.
* The initial toolchain remains small and understandable.
* Ruff provides fast linting and formatting checks.
* Pull Requests and changes to `main` receive automated quality validation.
* Dependency locking is not yet implemented.
* Only Python 3.12 is checked initially.
* Platform-specific CI is deferred.
* The packaging strategy remains unresolved.
