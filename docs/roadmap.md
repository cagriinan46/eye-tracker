# Project Roadmap

## Roadmap Purpose

This roadmap describes the major engineering phases of the 28-week graduation project. Each phase identifies the major problem being addressed, the expected outcome, and the criteria for moving forward.

The roadmap remains intentionally high-level. Detailed implementation work will be represented later as GitHub Issues.

## Overall Academic Timeline

* Graduation Project I: 14 weeks
* Graduation Project II: 14 weeks
* Total: 28 weeks

The project will use milestone-oriented development rather than assuming that uncertain research tasks will always fit exact estimates. Phases may overlap or take longer depending on experimental results, so this roadmap does not rigidly assign every phase to exact calendar weeks.

---

## Bootstrap Phase — Project Foundation

**Primary period:** Before feature implementation

### Goal

Prepare the repository, documentation, collaboration workflow, and engineering foundation before feature implementation begins.

### Includes

* project scope,
* requirements,
* architecture,
* initial Architecture Decision Records,
* roadmap,
* coding-agent instructions,
* GitHub issue and pull-request workflow,
* minimal CI,
* repository structure.

### Exit Criteria

* governing project documentation exists,
* collaboration rules are defined,
* `main` is protected from uncontrolled development,
* the team is ready to create the first technical-validation issues.

Feature implementation is not part of this phase.

---

## Phase 0 — Technical Validation

**Primary term:** Graduation Project I

### Goal

Determine whether usable gaze-related signals can be extracted from standard consumer camera hardware and identify the main technical limitations early.

### Focus

* camera acquisition,
* face and eye tracking experiments,
* usable eye/face feature extraction,
* initial calibration experiments,
* approximate gaze estimation,
* basic experimental logging,
* baseline measurements.

This phase is intentionally experimental. The team should prefer small prototypes and measurements over building a polished application.

### Key Questions

* Can the user's gaze direction be estimated reliably enough for the project?
* How stable is the signal?
* How much does head movement affect estimation?
* What level of calibration is required?
* What failure modes appear under realistic lighting and positioning?
* Is direct pointer control viable, or will coarse gaze plus target correction be necessary?

### Exit Criteria

The team has quantitative evidence about the feasibility and limitations of the baseline gaze approach and enough information to choose the next implementation direction.

Major technical choices discovered during this phase should later be recorded through ADRs.

---

## Phase 1 — Gaze Control Core

**Primary term:** Graduation Project I

### Goal

Turn the successful technical experiments into a reusable baseline gaze-control subsystem.

### Expected Capabilities

* reusable camera/vision pipeline,
* calibration workflow,
* gaze estimation,
* screen-coordinate mapping,
* basic gaze stabilization,
* cursor movement,
* graceful handling of tracking loss.

### Exit Criteria

A user can complete a defined cursor-targeting experiment using gaze input, and the team can measure accuracy, latency, and failure behavior.

---

## Phase 2 — Gesture and Intent Interaction

**Primary term:** Graduation Project I

### Goal

Enable intentional computer actions without traditional mouse input.

### Expected Capabilities

* supported eye gestures,
* supported head gestures where appropriate,
* timing/confidence information,
* distinction between detected physical signals and intended commands,
* left click,
* right click,
* scrolling or equivalent accessible navigation.

The system must not treat every detected blink as a command.

### Exit Criteria

A user can perform core pointer actions using gaze plus at least one intentional interaction mechanism with measurable unintended-activation behavior.

---

## Phase 3 — Adaptive Interaction and User Profiles

**Primary term:** Graduation Project I

### Goal

Allow interaction methods to adapt to different user capabilities.

### Expected Capabilities

* configurable input-to-action mappings,
* persistent user profiles,
* user-specific calibration/settings,
* configurable thresholds or sensitivity where appropriate,
* ability for different users to use different supported interaction methods.

### Exit Criteria

At least two distinct interaction configurations can be demonstrated without changing application source code.

Examples:

```text
User A:
gaze + wink

User B:
gaze + head gesture or dwell
```

---

## Phase 4 — Accessible Text Input

**Primary term:** Graduation Project I

### Goal

Allow the user to enter text without a physical keyboard.

### Expected Capabilities

* accessible on-screen keyboard,
* Turkish character support,
* integration with gaze and supported selection mechanisms,
* basic usability measurements.

Advanced word prediction is not required for the initial implementation.

### Exit Criteria

A user can enter a defined Turkish text sample without using a physical keyboard, and text-entry performance can be measured.

---

## Phase 5 — Assistive Hardware Integration

**Primary term:** Graduation Project I

### Goal

Integrate the required physical chair/seating prototype into the same accessible interaction model.

### Expected Capabilities

* software-to-hardware communication,
* raise command,
* lower command,
* stop command,
* movement limits,
* controlled failure handling,
* independent physical emergency-stop capability where actuator movement is involved.

Development should begin with a safe prototype rather than modifying safety-critical commercial mobility equipment.

### Exit Criteria

The user can control the safe prototype through the accessibility application while hardware safety requirements are satisfied.

---

## Graduation Project I Target

By the end of Graduation Project I, the project should demonstrate an end-to-end prototype including:

* gaze-based computer interaction,
* intentional click/control mechanism,
* configurable interaction mapping,
* user-specific calibration/profile support,
* accessible text input,
* basic assistive hardware control,
* measurable baseline performance,
* working macOS implementation.

Graduation Project I should end with a working system, not only documentation or isolated experiments.

---

## Phase 6 — Accuracy, Reliability, and Robustness

**Primary term:** Graduation Project II

### Goal

Improve the baseline system based on measurements and observed failure cases.

### Possible Areas

* gaze accuracy,
* signal stability,
* calibration reliability,
* false activation reduction,
* tracking recovery,
* interaction latency,
* usability,
* runtime robustness.

Exact optimization methods should be chosen based on measured bottlenecks rather than assumed in advance.

### Exit Criteria

The improved system demonstrates measurable improvement against the Graduation Project I baseline in selected metrics.

---

## Phase 7 — Semantic / UI-Aware Gaze

**Primary term:** Graduation Project II

### Goal

Investigate whether approximate gaze can be combined with accessible UI information to improve target selection.

### Possible Capabilities

* identify accessible UI elements near an estimated gaze point,
* identify actionable targets,
* rank probable intended targets,
* snap or correct gaze selection toward an intended interface element.

The exact implementation is intentionally TBD.

### Exit Criteria

The semantic approach can be experimentally compared against baseline coordinate-only gaze targeting.

If it does not provide meaningful value, it should not be retained solely for feature count.

---

## Phase 8 — Windows Platform Support

**Primary term:** Graduation Project II

### Goal

Extend essential functionality from the primary macOS development environment to Windows.

### Expected Work

* Windows platform adapter,
* input execution,
* accessibility integration where required,
* platform-specific testing,
* packaging/runtime verification.

Core gaze, gesture, and intent modules should not require architectural redesign.

### Exit Criteria

Core supported interaction flows function on both macOS and Windows through the shared core architecture.

---

## Phase 9 — Advanced Personalization

**Primary term:** Graduation Project II

### Goal

Improve adaptation to individual users based on measured capabilities and performance.

### Possible Directions

* improved calibration personalization,
* interaction reliability scoring,
* adaptive gesture parameters,
* recommended input mappings,
* improved intent discrimination.

Machine learning may be considered only where it provides measurable value beyond simpler approaches.

### Exit Criteria

The project can demonstrate that personalization improves at least one meaningful interaction metric or accessibility outcome.

---

## Phase 10 — Validation and Evaluation

**Primary term:** Graduation Project II

### Goal

Produce strong evidence that the system solves the intended accessibility problem.

### Evaluation Areas

* gaze accuracy,
* target-selection success,
* false activations,
* task completion time,
* calibration time,
* text-entry performance,
* latency,
* robustness,
* user-specific configuration,
* hardware interaction.

Where feasible and appropriately approved, expert or target-user feedback should be incorporated.

Any required ethical or institutional procedures for human-participant evaluation must be addressed before such testing.

### Exit Criteria

The project has reproducible evaluation procedures and sufficient evidence to support its technical claims.

---

## Phase 11 — Productization and TEKNOFEST Preparation

**Primary term:** Graduation Project II

### Goal

Transform the validated engineering prototype into a polished competition and graduation demonstration.

### Focus

* reliability,
* user experience,
* installation and setup,
* demo flow,
* hardware presentation,
* documentation,
* system recovery,
* packaging,
* measurable comparison results,
* presentation materials.

Optional advanced features such as voice interaction, word prediction, or additional environmental controls may only be considered if the core system is already stable and validated.

Additional environmental controls remain outside the current approved scope unless the project team explicitly revises that scope.

### Exit Criteria

The project can be demonstrated reliably from setup through real user interaction and can clearly communicate:

* the problem,
* the solution,
* the technical contribution,
* the measurable improvement,
* the accessibility benefit.

---

## Graduation Project II Target

Graduation Project II should evolve the functional prototype from the first term into a validated, robust, cross-platform, competition-quality system.

The second term should prioritize:

1. measurable improvement,
2. reliability,
3. adaptability,
4. validation,
5. product quality,

rather than simply maximizing feature count.

---

## Roadmap Rules

1. Phases define outcomes, not exact implementation tasks.
2. GitHub Issues will be created when a phase is about to begin.
3. Issues should remain small, independently reviewable units of work.
4. Experimental phases may change later implementation plans.
5. Failed experiments are valid engineering outcomes when measured and documented.
6. Major decisions discovered through experimentation should be recorded as ADRs.
7. The roadmap may be revised by the project team when evidence justifies a change.
8. AI coding agents may not autonomously modify the roadmap.
9. Optional features must not delay core accessibility functionality.
10. Stable, measurable functionality has priority over feature quantity.
