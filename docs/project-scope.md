# Project Scope

## 1. Project Overview

This project aims to develop an adaptive assistive computing system that enables individuals with severe upper-limb motor impairments to interact with a computer without relying on a traditional mouse or keyboard.

The core interaction method will be gaze-based computer control using a standard camera. Additional voluntary signals such as intentional eye gestures, head movements, and potentially voice input may be used as alternative interaction methods depending on the user's physical capabilities.

The system will also include a small hardware integration that allows the user to control the height or position of a chair or assistive seating mechanism through the same accessible interface.

The long-term goal is to evolve the project from a basic gaze-controlled computer interface into an adaptive multimodal accessibility platform suitable for both the university graduation project and a potential TEKNOFEST participation.

---

## 2. Target Users

The primary target users are individuals who:

* have severe difficulty using their hands or upper limbs,
* cannot efficiently operate a traditional mouse and keyboard,
* retain sufficient visual ability to interact with a screen,
* can intentionally perform at least one detectable action such as gaze movement, blinking, winking, head movement, or another supported input.

The system must not assume that every user has the same physical capabilities.

Different users may require different interaction methods.

For example:

* one user may use gaze + left wink,
* another may use gaze + head movement,
* another may rely primarily on dwell-based selection,
* another may combine gaze with voice commands.

---

## 3. Core Project Goal

The core goal is to enable a user to perform essential computer interactions without using their hands.

At minimum, the system should eventually support:

* cursor movement through gaze,
* left-click,
* right-click,
* scrolling,
* text entry,
* configurable interaction methods,
* basic user calibration,
* user-specific accessibility profiles.

The project should prioritize usability, reliability, low latency, and reduction of unintended actions.

---

## 4. Adaptive Interaction

A central design principle of the project is adaptability.

Interaction methods must not be permanently hard-coded to a single gesture.

The system should allow actions such as:

* left click,
* right click,
* confirmation,
* cancellation,
* scrolling,
* text selection,

to be mapped to different intentional user inputs.

Possible inputs include:

* gaze,
* left wink,
* right wink,
* intentional long blink,
* dwell,
* head gestures,
* supported facial gestures,
* optional voice input.

The long-term system may evaluate which inputs a user can perform reliably and assist in creating an appropriate interaction profile.

---

## 5. Gaze-Based Computer Control

The first major technical objective is to estimate where the user is looking on the screen using a standard camera.

The gaze subsystem will include:

* face and eye detection,
* eye feature extraction,
* user calibration,
* gaze estimation,
* screen-coordinate mapping,
* gaze stabilization and filtering,
* confidence estimation where applicable.

The initial implementation does not need to achieve pixel-perfect gaze tracking.

The project will first determine experimentally what level of accuracy is achievable with consumer hardware and then adapt the interaction design accordingly.

---

## 6. Intentional Gesture Detection

Natural actions must be distinguished from intentional commands whenever possible.

For example, a normal involuntary blink must not automatically produce a mouse click.

The system should investigate signals such as:

* gesture duration,
* left/right eye distinction,
* gaze stability,
* gesture confidence,
* temporal patterns,
* interaction context.

This subsystem may initially use deterministic thresholds and rules.

Machine learning should only be introduced where it provides a measurable improvement over simpler approaches.

---

## 7. Semantic and Context-Aware Interaction

A later stage of the project may improve gaze-based target selection using information about the graphical user interface.

Instead of treating gaze solely as an exact screen coordinate, the system may use nearby accessible interface elements to infer the intended target.

Example:

Approximate gaze position → nearby interface elements → probable target → corrected selection.

This concept will be investigated after the baseline gaze-control system has been implemented and measured.

---

## 8. Accessible Text Input

The project should eventually provide an accessible text-entry mechanism.

Potential functionality includes:

* Turkish Q keyboard,
* potentially Turkish F keyboard,
* gaze-based key selection,
* dwell or gesture-based key confirmation,
* commonly used phrases,
* word prediction,
* next-word prediction.

Advanced language-model integration is not required for the initial system.

---

## 9. Hardware Integration

The graduation project must include a small hardware component.

The current planned hardware functionality is an accessible chair or seating-position controller.

The user should be able to perform commands such as:

* raise,
* lower,
* stop,

through the same accessible interaction system.

The first hardware implementation should be a safe prototype rather than an immediate modification of a real powered wheelchair.

The design should include appropriate safety mechanisms such as:

* movement limits,
* emergency stop capability,
* fail-safe behavior,
* controlled actuator operation.

The hardware architecture should allow additional assistive devices to be integrated in the future without requiring a redesign of the entire system.

---

## 10. Supported Operating Systems

Official target operating systems:

* macOS
* Windows

Development will primarily take place on macOS.

The architecture should isolate operating-system-specific functionality so that the core gaze, gesture, intent, and accessibility logic remains as platform-independent as reasonably possible.

Linux is not an official target platform for the current project.

---

## 11. Local-First Architecture

Real-time accessibility functions must operate locally on the user's computer.

Core functions must not depend on an Internet connection.

These include:

* camera processing,
* gaze estimation,
* gesture detection,
* intent detection,
* cursor control,
* keyboard control,
* chair control.

Raw camera video, facial images, and biometric data should not be uploaded to external services as part of normal system operation.

Optional telemetry may be considered later, but only for non-sensitive technical metrics and only when clearly justified.

---

## 12. Artificial Intelligence and Machine Learning

AI or machine learning will not be added solely for the purpose of making the project appear more advanced.

They may be used where they provide measurable value.

Potential applications include:

* gaze estimation,
* intentional gesture classification,
* user-specific calibration,
* adaptive interaction mapping,
* intended-target prediction,
* text prediction.

Existing computer-vision models and libraries may be used where appropriate.

Training a large model from scratch is not a project requirement.

---

## 13. Initial Technical Direction

The initial system is expected to use a Python-first development approach.

Potential technologies include:

* Python
* OpenCV
* MediaPipe
* PySide6 / Qt
* platform-specific accessibility APIs
* platform-specific input-control adapters
* ESP32 or a similar microcontroller for the hardware prototype

Technology choices are not permanently fixed by this document and may change through documented architecture decisions.

---

## 14. Development and Collaboration

The project will be developed by two team members using a shared GitHub repository.

Development will follow a feature-branch and pull-request workflow.

The `main` branch should remain stable.

Implementation work should generally follow this process:

GitHub Issue → feature branch → implementation → tests → commit → push → pull request → review → CI → merge.

AI coding agents may:

* implement approved issues,
* create feature branches,
* modify code,
* write tests,
* create commits,
* push feature branches,
* create pull requests.

AI coding agents must not autonomously:

* merge into `main`,
* directly push to `main`,
* change project scope,
* change the approved roadmap,
* make major architectural decisions without review.

---

## 15. CI/CD Scope

CI/CD will be used where it naturally benefits the development process.

The initial pipeline may include:

* linting,
* unit tests,
* automated checks on pull requests.

Later stages may include:

* integration tests,
* macOS builds,
* Windows builds,
* release artifacts.

Cloud infrastructure, Kubernetes, container orchestration, or other infrastructure technologies are not project requirements unless a genuine technical need emerges later.

---

## 16. Graduation Project Scope

The project consists of two academic terms:

* Graduation Project I — 14 weeks
* Graduation Project II — 14 weeks

Total planned development period:

**28 weeks**

Graduation Project I should result in a functional end-to-end prototype rather than only research or design documentation.

The second term should focus on improving:

* accuracy,
* adaptability,
* usability,
* robustness,
* cross-platform support,
* hardware integration,
* evaluation,
* advanced interaction methods.

---

## 17. TEKNOFEST Direction

The graduation project may also be developed toward participation in TEKNOFEST, particularly an accessibility-focused competition such as Engelsiz Yaşam Teknolojileri if the relevant competition structure remains appropriate for the application year.

The TEKNOFEST-oriented version should not simply contain more features.

Priority should be given to:

* a clearly defined user problem,
* meaningful technical contribution,
* working prototype quality,
* measurable improvements,
* user or expert validation,
* safety,
* accessibility,
* demonstrable real-world value.

---

## 18. Measurement and Evaluation

The project should be evaluated quantitatively wherever possible.

Potential metrics include:

* gaze estimation error,
* successful target-selection rate,
* unintended activation rate,
* task completion time,
* calibration time,
* click accuracy,
* text-entry speed,
* inference latency,
* frame processing rate,
* recalibration frequency.

Later versions may compare different interaction approaches.

Example:

* gaze + dwell,
* gaze + fixed gesture,
* adaptive multimodal interaction,
* semantic target selection.

The project's technical contribution should be supported by experimental results rather than feature count alone.

---

## 19. Current Out of Scope

The following areas are currently outside the planned project scope:

* Linux product support,
* full smart-home automation,
* general-purpose AI assistant,
* autonomous computer-use agent,
* accessibility features targeted primarily at hearing impairment,
* accessibility features targeted primarily at complete visual impairment,
* large-scale cloud infrastructure,
* Kubernetes,
* unnecessary microservice architecture,
* training large AI models from scratch,
* medical diagnosis,
* direct modification of safety-critical commercial mobility devices during early development.

These items may only enter the project if the project team explicitly revises the scope.

---

## 20. Guiding Principle

The project is not intended to become a collection of unrelated accessibility features.

Every major feature should support the same central objective:

> Enable a person with severe motor limitations to interact with digital systems and selected elements of their physical environment as independently, reliably, safely, and comfortably as possible.

When evaluating a new feature, the team should ask:

1. Does this solve a meaningful problem for the target user?
2. Can its contribution be measured or validated?
3. Does it strengthen the central project rather than expanding the project unnecessarily?

If not, the feature should normally remain outside the project scope.
