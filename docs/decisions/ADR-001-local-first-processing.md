# ADR-001 — Local-First Processing

## Status

Accepted

## Context

The system provides real-time accessibility functions whose usability depends on low latency and reliable availability. Its camera feed may contain facial imagery and other sensitive biometric data. Core accessibility functions must continue to operate when Internet access or an external service is unavailable.

## Decision

Core real-time accessibility functionality will run locally on the user's computer. This includes:

* camera processing,
* gaze estimation,
* gesture detection,
* intent interpretation,
* cursor and keyboard control,
* communication with the assistive hardware controller.

Normal operation must not require an Internet connection.

Raw camera frames, facial imagery, and similar sensitive biometric data must not be uploaded to external services during normal operation.

Optional non-sensitive telemetry may be considered later, but it is not part of the core real-time control path. This decision does not select a cloud provider or telemetry technology.

## Consequences

* Interaction does not depend on network latency and can remain responsive.
* Core accessibility functions remain available without Internet access and do not stop because a remote service is unavailable.
* Sensitive camera and biometric data remains on the user's computer during normal operation, reducing privacy exposure.
* The system has less operational dependency on external services.
* The user's computer must provide the resources required for core real-time processing.
* Any future optional telemetry must remain outside the core real-time control path and comply with the project's privacy constraints.
