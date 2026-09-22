# ADR-002 — Target Platforms

## Status

Accepted

## Context

The project is being developed by a two-person team within a 28-week graduation-project schedule. Supporting every desktop operating system would increase development, testing, and maintenance effort beyond the approved scope. At the same time, coupling core processing logic directly to one operating system would make support for both approved platforms harder.

## Decision

The officially supported desktop operating systems are:

* macOS
* Windows

Development will primarily take place on macOS.

Linux is not an official product target for the current graduation project. This is a project-scope decision based on available development time and team size, not a statement about the accessibility needs of Linux users.

Core gaze, gesture, and intent logic will avoid unnecessary coupling to a particular operating system. Operating-system-specific behavior must be isolated behind platform-specific components or adapters.

The exact macOS and Windows input APIs remain TBD.

## Consequences

* Development and validation effort is focused on macOS and Windows.
* macOS can serve as the primary development environment while Windows remains an official target.
* Platform isolation allows core gaze, gesture, and intent behavior to remain consistent across the supported operating systems.
* Platform-specific behavior and testing are still required for both macOS and Windows.
* Linux-specific implementation, testing, packaging, and support are outside the current project scope.
* Exact operating-system input APIs require a later explicit decision.
