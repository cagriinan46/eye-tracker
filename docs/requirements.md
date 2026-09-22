# Project Requirements

This document defines the project requirements derived from the approved [project scope](project-scope.md). The project scope remains the governing document.

Stage labels indicate the intended delivery stage:

- **Core** — Minimum capabilities central to the system.
- **Graduation Project I** — Capabilities intended for the functional end-to-end prototype delivered in the first term.
- **Graduation Project II** — Later improvements and advanced capabilities intended for the second term.

## 1. Functional Requirements (FR)

### Core

#### FR-001 — Real-time camera capture

**Stage:** Core

The system shall be able to capture real-time video from a standard computer camera.

#### FR-002 — Face and eye-region tracking

**Stage:** Core

The system shall be able to track the user's face and eye regions from the camera feed.

#### FR-003 — User-specific gaze calibration

**Stage:** Core

The system shall provide a user-specific gaze calibration procedure.

#### FR-004 — Approximate gaze estimation

**Stage:** Core

The system shall estimate the user's approximate gaze position on the screen.

#### FR-005 — Gaze-based cursor control

**Stage:** Core

The user shall be able to control the computer cursor using gaze.

#### FR-006 — Intentional gesture detection

**Stage:** Core

The system shall detect supported intentional gestures such as left/right eye gestures and supported head gestures.

#### FR-007 — Natural and intentional blink distinction

**Stage:** Core

The system shall attempt to distinguish natural blinking from intentional command gestures.

#### FR-008 — Accessible click operations

**Stage:** Core

The user shall be able to perform left-click and right-click operations without using their hands.

#### FR-009 — Accessible scrolling

**Stage:** Core

The user shall be able to perform scrolling through an accessible input method.

#### FR-010 — Configurable input mapping

**Stage:** Core

Supported user inputs shall be configurable and mappable to computer actions.

#### FR-011 — User-specific interaction profiles

**Stage:** Core

The system shall support storing and loading user-specific interaction profiles.

### Graduation Project I

#### FR-012 — Accessible on-screen keyboard

**Stage:** Graduation Project I

The system shall provide an accessible on-screen keyboard for text input.

#### FR-013 — Turkish character support

**Stage:** Graduation Project I

The accessible keyboard shall support Turkish characters.

#### FR-014 — Chair control commands

**Stage:** Graduation Project I

The system shall support at least raise, lower, and stop commands for the chair/seating hardware prototype.

#### FR-015 — Physical control-module communication

**Stage:** Graduation Project I

The desktop application shall communicate with the physical control module.

#### FR-016 — Repeatable calibration

**Stage:** Graduation Project I

The user shall be able to repeat the calibration procedure when necessary.

#### FR-017 — Interaction measurement collection

**Stage:** Graduation Project I

The system shall support collecting measurements required to evaluate the reliability of supported user interactions.

### Graduation Project II and Advanced Capabilities

The requirements in this section are later-stage capabilities and are not part of the minimum core system.

#### FR-018 — Nearby accessible UI-element inspection

**Stage:** Graduation Project II

The system shall eventually be able to inspect accessible UI elements near an approximate gaze position.

#### FR-019 — Probable intended-target correction

**Stage:** Graduation Project II

The system shall eventually support correcting or snapping an approximate gaze position toward a probable intended UI target.

#### FR-020 — Interaction personalization

**Stage:** Graduation Project II

The system shall support personalization of interaction parameters based on the user's capabilities or measured performance.

#### FR-021 — Turkish word prediction

**Stage:** Graduation Project II

The system may support Turkish word prediction or similar mechanisms that improve accessible text-entry efficiency.

#### FR-022 — Windows computer control

**Stage:** Graduation Project II

The system shall support essential computer-control functionality on Windows in addition to macOS.

## 2. Non-Functional Requirements (NFR)

### NFR-001 — Offline core operation

**Stage:** Core

Core gaze, gesture, and computer-control functionality shall operate without requiring an Internet connection.

### NFR-002 — Camera-data privacy

**Stage:** Core

Raw camera video and facial imagery shall not be uploaded to an external server during normal operation.

### NFR-003 — Practical interaction latency

**Stage:** Core

Real-time interaction shall maintain latency low enough to preserve practical usability. A numerical threshold will be defined after initial benchmarking.

### NFR-004 — Recalibration frequency

**Stage:** Graduation Project II

The system should avoid requiring unnecessary or excessively frequent recalibration during normal use.

### NFR-005 — Platform-specific isolation

**Stage:** Core

Operating-system-specific functionality shall be isolated from the core vision, gaze, gesture, and intent logic.

### NFR-006 — Official target platforms

**Stage:** Core

Official target platforms are macOS and Windows.

### NFR-007 — Measurable system performance

**Stage:** Graduation Project I

System performance shall be measurable through predefined experiments and metrics.

### NFR-008 — Controlled runtime failure handling

**Stage:** Graduation Project I

Camera, tracking, or related runtime failures shall be handled in a controlled manner without unsafe behavior.

### NFR-009 — Persistent profiles and settings

**Stage:** Core

User profiles and relevant settings shall persist between application sessions.

### NFR-010 — Extensibility

**Stage:** Graduation Project II

The architecture should allow new supported input methods or assistive hardware modules to be introduced without rewriting the core system.

## 3. Safety Requirements (SAFE)

### SAFE-001 — Movement stop capability

**Stage:** Graduation Project I

Physical movement controlled by the system shall be stoppable by the user or supervisor at any time.

### SAFE-002 — Physical movement limits

**Stage:** Graduation Project I

The hardware prototype shall respect defined physical movement limits.

### SAFE-003 — Safe failure state

**Stage:** Graduation Project I

Communication or software failure shall place or leave the actuator system in a safe state.

### SAFE-004 — Independent emergency stop

**Stage:** Graduation Project I

The prototype shall support an independent physical emergency-stop mechanism where actuator movement is involved.

### SAFE-005 — Commercial equipment restriction

**Stage:** Core

Early prototypes shall not directly modify safety-critical commercial mobility equipment.
