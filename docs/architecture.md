# System Architecture

## 1. Architecture Goals

The architecture should:

* keep real-time interaction local-first,
* separate computer vision from interaction logic,
* isolate operating-system-specific behavior,
* support user-specific adaptive interaction,
* allow assistive hardware to be integrated independently,
* allow different team members and coding agents to work on separate modules with minimal conflict,
* remain simple enough for a two-person graduation-project team,
* avoid unnecessary infrastructure or abstraction.

The architecture must favor clear module boundaries over premature complexity.

---

## 2. High-Level Data Flow

The primary processing flow is:

```text
Camera
  ↓
Vision Layer
  ↓
Feature Extraction
  ├── Eye Features
  ├── Facial Features
  └── Head Pose Features
  ↓
  ├───────────────┐
  ↓               ↓
Gaze Engine   Gesture Engine
  │               │
  └───────┬───────┘
          ↓
     Intent Engine
          ↓
     Action Engine
       ↙       ↘
Platform       Hardware
Adapter        Adapter
```

User Profile and Metrics/Evaluation are supporting components that interact with the relevant stages of this pipeline.

---

## 3. Vision Layer

Responsibilities:

* capture frames from the selected computer camera,
* manage camera lifecycle,
* obtain raw face and eye tracking information,
* expose vision data to downstream modules,
* report camera or tracking failures in a controlled way.

The vision layer must not:

* move the cursor,
* execute operating-system actions,
* decide user intent,
* control hardware.

Camera handling should live inside the vision module rather than having a separate top-level camera package.

Potential internal modules:

```text
vision/
├── camera.py
├── face_tracker.py
└── feature_extractor.py
```

Implementation libraries are not fixed by this architecture document unless already approved elsewhere.

---

## 4. Feature Extraction

The feature-extraction responsibility belongs to the vision layer.

It converts raw tracking output into normalized features that can be consumed by other modules.

Examples may include:

```text
left_eye_openness
right_eye_openness
iris_relative_x
iris_relative_y
head_yaw
head_pitch
head_roll
```

Exact features are TBD and will be determined experimentally.

Downstream modules should depend on normalized project-level feature representations where practical rather than directly depending on a specific computer-vision library's raw output.

This boundary is intended to make future replacement or modification of the underlying vision implementation easier.

---

## 5. Gaze Engine

Responsibilities:

* consume relevant eye, face, and head features,
* consume user calibration data,
* estimate the user's approximate gaze position,
* map gaze estimation to screen coordinates,
* provide confidence information where practical,
* support filtering or stabilization of gaze output.

Conceptual output:

```text
GazeResult
- x
- y
- confidence
- timestamp
```

The exact gaze-estimation technique is intentionally TBD.

Do not mandate:

* a specific regression algorithm,
* machine-learning model,
* exact calibration-point count,
* smoothing algorithm,
* Kalman filtering,
* neural-network architecture.

These choices will be determined through experiments.

Potential internal modules:

```text
gaze/
├── estimator.py
├── calibration.py
└── smoothing.py
```

---

## 6. Gesture Engine

Responsibilities:

* detect supported intentional eye gestures,
* detect supported head gestures,
* expose gesture events with useful confidence and timing information,
* avoid directly triggering computer actions.

Possible gesture outputs may include:

```text
LEFT_WINK
RIGHT_WINK
LONG_BLINK
HEAD_NOD
HEAD_LEFT
HEAD_RIGHT
```

The exact supported gesture set is not permanently fixed.

Initial implementations may use deterministic thresholds and timing rules.

Machine learning may be introduced later only if experimental evidence justifies it.

Potential structure:

```text
gestures/
├── blink.py
├── wink.py
└── head_pose.py
```

---

## 7. Intent Engine

The Intent Engine is responsible for interpreting user behavior rather than merely detecting physical signals.

It consumes information such as:

* gaze position,
* gaze stability,
* gesture events,
* gesture confidence,
* user profile,
* interaction context.

Example:

```text
stable gaze
+
intentional left wink
+
sufficient confidence
=
LEFT_CLICK intent
```

A detected blink or gesture must not automatically imply an action.

Possible intent outputs:

```text
MOVE_POINTER
LEFT_CLICK
RIGHT_CLICK
SCROLL_UP
SCROLL_DOWN
TYPE
CANCEL
CHAIR_UP
CHAIR_DOWN
CHAIR_STOP
NO_ACTION
```

The Intent Engine should remain independent of operating-system-specific APIs and hardware protocols.

Potential structure:

```text
intent/
└── engine.py
```

---

## 8. Action Engine

The Action Engine receives validated intents and dispatches them to the appropriate execution mechanism.

It should not contain platform-specific implementation details.

Examples:

```text
LEFT_CLICK
→ Platform Adapter

CHAIR_UP
→ Hardware Adapter
```

Potential structure:

```text
actions/
└── controller.py
```

The Action Engine acts as the boundary between interpreted user intent and external side effects.

---

## 9. Platform Adapters

Operating-system-specific behavior must be isolated from the core system.

Target platforms:

* macOS
* Windows

A common conceptual interface should support functionality such as:

```text
move_cursor(x, y)
left_click()
right_click()
scroll(amount)
type_text(text)
```

Possible repository structure:

```text
platform/
├── base.py
├── macos.py
└── windows.py
```

The exact OS APIs and libraries are TBD.

The core vision, gaze, gesture, and intent modules must not directly call macOS- or Windows-specific APIs.

Linux is not an official target platform.

---

## 10. Hardware Module

Hardware integration must remain separate from platform-specific desktop control.

Responsibilities may include:

* communication with the chair/seating prototype,
* sending safe movement commands,
* receiving hardware state where applicable,
* handling communication loss safely.

Initial commands:

```text
CHAIR_UP
CHAIR_DOWN
CHAIR_STOP
```

Potential structure:

```text
hardware/
├── controller.py
└── chair.py
```

The exact microcontroller communication protocol is TBD.

Safety requirements defined in `docs/requirements.md` govern this module.

The software architecture must not assume that software control alone is sufficient for physical safety.

---

## 11. User Profiles

User-specific interaction configuration should be represented separately from the core interaction engines.

A profile may eventually contain:

```text
gesture mappings
calibration data
sensitivity settings
gesture thresholds
preferred interaction methods
keyboard preferences
platform-related preferences
```

Examples:

```text
left wink → left click
head nod → right click
long blink → cancel
```

Different users must be able to use different mappings.

Potential structure:

```text
profiles/
├── model.py
└── repository.py
```

The exact persistence format is TBD.

---

## 12. Metrics and Evaluation

Measurement must be treated as part of the system design rather than added only at the end of the project.

The system should eventually support recording experiment-relevant data such as:

```text
timestamp
target position
predicted gaze position
cursor position
gesture
intent
action
latency
success/failure
false activation
```

This data is intended primarily for:

* experiments,
* debugging,
* benchmarking,
* graduation-project evaluation,
* TEKNOFEST validation.

Production telemetry and experimental logging must remain conceptually separate.

Potential structure:

```text
metrics/
├── logger.py
└── models.py
```

Sensitive camera frames or biometric imagery must not be uploaded externally during normal operation.

---

## 13. Application Layer

The application layer coordinates the main runtime lifecycle.

Responsibilities may include:

* application startup and shutdown,
* configuration loading,
* initialization of system components,
* user-interface coordination,
* profile selection,
* calibration workflow,
* switching between interaction modes.

Potential structure:

```text
app/
└── main.py
```

The application layer should orchestrate modules rather than contain computer-vision or gesture-detection algorithms itself.

---

## 14. Proposed Source Structure

The architecture-level target structure is:

```text
src/
├── vision/
│   ├── camera.py
│   ├── face_tracker.py
│   └── feature_extractor.py
│
├── gaze/
│   ├── estimator.py
│   ├── calibration.py
│   └── smoothing.py
│
├── gestures/
│   ├── blink.py
│   ├── wink.py
│   └── head_pose.py
│
├── intent/
│   └── engine.py
│
├── actions/
│   └── controller.py
│
├── platform/
│   ├── base.py
│   ├── macos.py
│   └── windows.py
│
├── hardware/
│   ├── controller.py
│   └── chair.py
│
├── profiles/
│   ├── model.py
│   └── repository.py
│
├── metrics/
│   ├── logger.py
│   └── models.py
│
└── app/
    └── main.py
```

This is an architectural target, not an instruction to create all source files during this documentation task.

---

## 15. Dependency Direction

Preferred conceptual flow:

```text
vision
   ↓
gaze / gestures
   ↓
intent
   ↓
actions
   ↓
platform / hardware
```

Supporting components:

```text
profiles
metrics
app
```

Important restrictions:

* Vision must not depend on platform adapters.
* Vision must not control hardware.
* Gaze must not execute OS actions.
* Gesture detection must not directly click or scroll.
* Intent must not contain macOS or Windows API calls.
* Hardware modules must not depend on gaze-estimation internals.
* Platform adapters must not contain gaze or gesture algorithms.
* Application orchestration should not become a dumping ground for core logic.

---

## 16. Data Contracts

The architecture should favor explicit data contracts between modules.

Conceptual examples may include:

```text
VisionFeatures
GazeResult
GestureEvent
Intent
ActionRequest
UserProfile
MetricEvent
```

Exact Python classes, dataclasses, schemas, or typing strategies are TBD.

Do not implement them during this task.

The goal is to prevent modules from passing loosely defined arbitrary dictionaries throughout the system.

---

## 17. Error Handling Philosophy

Errors should remain local where practical and propagate through explicit failure states.

Examples:

* camera unavailable,
* face not detected,
* gaze confidence too low,
* calibration unavailable,
* hardware disconnected,
* unsupported platform action.

Failure of one subsystem must not silently cause unsafe physical actions.

In particular:

```text
uncertain intent
→ NO_ACTION
```

should generally be preferred over performing an uncertain external action.

---

## 18. Concurrency and Performance

Real-time camera processing and user interaction will eventually require careful runtime design.

However, this document does not prematurely mandate:

* threads,
* multiprocessing,
* asyncio,
* GPU execution,
* specific frame rates.

Concurrency and optimization strategy are TBD until baseline profiling exists.

The architecture should allow these optimizations later without requiring major redesign.

---

## 19. AI and Machine Learning Boundary

AI/ML is not a separate top-level architectural requirement.

Machine-learning techniques may exist inside appropriate modules if justified.

Examples:

```text
gaze estimation → gaze module
gesture classification → gesture module
target prediction → intent/semantic interaction module
text prediction → accessible text-input subsystem
```

Do not create a generic `ai/` module merely because AI may be used.

---

## 20. Future Semantic Interaction

Semantic gaze / UI-aware target correction is an approved future direction but is not part of the initial implementation.

It may eventually introduce a component responsible for:

* reading accessible UI elements,
* locating nearby actionable controls,
* combining approximate gaze with UI context,
* estimating the most probable intended target.

Its exact architectural placement remains TBD until the baseline gaze system has been evaluated.

Do not add implementation-specific modules for it yet.

---

## 21. Architectural Principles

1. Local-first interaction.
2. Safety before convenience.
3. Simple solutions before complex ones.
4. Measurement before optimization.
5. Experiment before locking uncertain algorithms.
6. Operating-system details remain isolated.
7. Detected physical signals are not automatically treated as user intent.
8. User capabilities vary; interaction must be adaptable.
9. Core modules should have clear responsibilities.
10. Architecture should enable parallel development by two developers and AI coding agents.

---

## 22. Current Architectural TBDs

The unresolved decisions are:

* gaze-estimation algorithm,
* gaze-filtering technique,
* calibration method and point count,
* gesture thresholds,
* whether ML is needed for gesture classification,
* persistence technology,
* GUI framework,
* exact macOS input API,
* exact Windows input API,
* hardware communication protocol,
* concurrency model,
* packaging strategy,
* semantic gaze implementation,
* word-prediction implementation.

These are not omissions.

They are intentionally deferred engineering decisions that should be resolved through experiments or Architecture Decision Records.

---

## 23. Architecture Decision Records

Major implementation choices should later be documented under:

```text
docs/decisions/
```

using Architecture Decision Records.

Examples:

```text
ADR-001 — Programming language
ADR-002 — Local-first processing
ADR-003 — Supported operating systems
ADR-004 — Vision framework
ADR-005 — Gaze estimation strategy
```

These ADR files are not created as part of this documentation task.
