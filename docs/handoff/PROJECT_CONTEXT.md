# Project context — whole-product handoff

Snapshot: **2026-10-08, Europe/Istanbul**. Operational state belongs in
[CURRENT_STATE](CURRENT_STATE.md); task history belongs in [WORK_LOG](WORK_LOG.md).
This document summarizes evidence and the approved project, without replacing
[scope](../project-scope.md), [requirements](../requirements.md),
[architecture](../architecture.md), [roadmap](../roadmap.md), or
[accepted ADRs](../decisions/).

## Academic purpose and human team

Çağrı İnan Çamlı and Muhammet Fatih Erdemir are developing a **Konya Technical
University Computer Engineering graduation project**. Graduation Project I is
14 weeks and Project II another 14: **28 weeks total**. The academic deliverable
is a functioning assistive computing prototype with an evidence-based technical
contribution. Isolated experiments or documentation alone do not satisfy the
first-term end-to-end target. The roadmap uses milestones, not invented exact
calendar deadlines for uncertain research.

Çağrı has worked with Codex/ChatGPT. Fatih temporarily continues with Claude
Opus/Claude Code under human supervision while Çağrı is away for roughly 1–2
days. Durable repository records must make subsequent work recoverable without
either agent's chat history.

## Accessibility purpose and full software scope

The platform primarily serves people with severe upper-limb motor limitations
who cannot comfortably use a conventional mouse or keyboard. Users' remaining
eye/head control, fatigue, posture and preferred interaction methods differ.
Approximate gaze alone is insufficient: the system must support intentional
selection, avoid accidental actions, allow adjustment, provide accessible text
entry and fail predictably when tracking or communication is lost.

The approved software scope includes webcam face/eye tracking, session calibration
and approximate gaze estimation; gaze cursor movement; left/right click and
scroll; intentional eye gestures including blink/wink handling with separation
from normal blinking; head gestures where appropriate; dwell as a possible
selection method; configurable gesture/action mappings; adjustable interaction
sensitivity; persistent per-user profiles/settings; an accessible Turkish
on-screen keyboard and measurable text-entry workflow. Interaction metrics,
validation and usability evaluation are deliverables, not optional decoration.
See FR-001–017 and NFRs in [requirements](../requirements.md).

Later approved roadmap areas include semantic/UI-aware target inspection and
selection, Windows support and advanced personalization. Exact semantic methods
are TBD; do not invent an architecture or treat them as delivered. Turkish word
prediction and voice interaction are optional advanced additions, conditional
on a stable core and human approval; initial Turkish text entry does not depend
on prediction. Additional environmental controls are outside current approved
scope unless humans revise it. Machine learning is not required and may be
considered only with a measurable advantage over simpler approaches.

## Mandatory hardware and official operating systems

The **safe assistive chair/seating prototype is mandatory** for Graduation
Project I. Expected concepts are `CHAIR_UP`, `CHAIR_DOWN`, and `CHAIR_STOP`, with
isolated software-to-controller communication, movement limits, controlled
failure/communication-loss behavior, and an independent physical emergency stop
when actuators move. Uncertain state must prefer no movement. Software stop
logic cannot be the sole physical safety mechanism. Prototype testing must
begin in controlled conditions under human-approved safety design.

No chair actuator/controller/emergency-stop implementation is delivered.
Control of an actual commercial powered wheelchair is **not approved**; see
SAFE-001–005 in [requirements](../requirements.md) and [hardware scope](../project-scope.md).

Development and historical human tests are on **macOS**. Official product
targets are **macOS and Windows**; Linux is not an official target. Ubuntu CI
does not establish Linux product support. Windows input/accessibility integration
and validation remain future work. [ADR-002](../decisions/ADR-002-target-platforms.md).

## Approved architecture and governance

```text
Camera → Vision → Gaze / Gestures → Intent → Actions → Platform / Hardware
```

Vision owns acquisition, detected landmarks and vendor-neutral geometry. Gaze
owns calibration/mapping/estimation. Gesture detection describes physical
signals and timing; Intent decides whether those imply a deliberate command;
Actions describes execution requests; platform adapters implement OS-specific
execution. Hardware communication/control is separate from desktop execution
and must not depend on gaze internals. The application coordinates components.
Vision/gaze/gesture modules must never directly click, scroll or move actuators;
Intent must remain independent of macOS/Windows APIs.

Core interaction is **local-first** and must work offline. Do not add Internet
services to camera, gaze, gesture, intent, computer-control or hardware-control
paths; do not upload raw imagery or face/iris geometry. Derived local numerical
data remain potentially sensitive. Logs in historical MediaPipe runs mention
`portable_clearcut_uploader` failed-send attempts; payload and outbound behavior
remain unknown. No harness upload path and local inference do not prove the
third-party library never attempted telemetry. Investigate only in a separately
approved task. [ADR-001](../decisions/ADR-001-local-first-processing.md),
[drift evidence](../../experiments/vertical_drift_diagnostics/RESULTS.md).

[ADR-003](../decisions/ADR-003-modular-architecture.md) governs separation;
[ADR-004](../decisions/ADR-004-python-runtime-and-quality-tooling.md) establishes
Python 3.12, venv/pip, pytest, Ruff and minimal GitHub Actions. Camera libraries
belong to the first Vision adapter, not an irreversible framework decision.
Unresolved architectural TBDs remain human decisions. [AGENTS](../../AGENTS.md)
and [CONTRIBUTING](../../CONTRIBUTING.md) govern issues, focused branches, tests
and human-reviewed merges. Claude's task approval boundaries are in
[CLAUDE.md](../../CLAUDE.md).

## Complete roadmap, phases 0–11

The table summarizes [the authoritative roadmap](../roadmap.md); it does not
create a second roadmap or assign new priorities.

| Phase | Approved outcome | State at this handoff |
| --- | --- | --- |
| Bootstrap | Scope, requirements, architecture, ADRs, workflow, CI | Established |
| 0 — Technical validation | Quantify camera, landmarks, signal and mapping feasibility | Exit gate met to enter Phase 1; limitations retained |
| 1 — Gaze control core | Reusable pipeline, calibration, mapping, stabilization, cursor, tracking-loss handling; targeting/latency evidence | Production pipeline slice implemented; exit incomplete |
| 2 — Gesture and intent | Intentional eye/head inputs; left/right click and scrolling; unintended-activation evidence | Planned; complete interaction system absent |
| 3 — Adaptive interaction / profiles | Persistent profiles, mappings, calibration/settings, sensitivity; two configurations without source edits | Planned |
| 4 — Accessible text input | Turkish keyboard, integrated selection, measured text entry | Planned |
| 5 — Assistive hardware | Safe raise/lower/stop prototype, communications, limits, physical emergency stop | Planned, safety design requires humans |
| 6 — Robustness | Measured accuracy/stability, recovery, latency and usability improvements over first-term baseline | Future term; no arbitrary optimization method selected |
| 7 — Semantic/UI-aware gaze | Compare accessible-target assistance against coordinate-only selection | Future, exact method TBD |
| 8 — Windows support | Windows adapters/input/accessibility/runtime tests, shared core | Future; no Windows delivery claim |
| 9 — Advanced personalization | Measurable individual adaptation beyond initial profiles | Future; ML conditional, not prescribed |
| 10 — Validation/evaluation | Reproducible accuracy, success, false activation, time, text, latency, robustness and hardware evidence | Historical technical studies exist; full-system/target-user evaluation absent |
| 11 — Productization / TEKNOFEST | Reliable installation/demo/recovery, documentation, hardware presentation and measured contribution | Future; optional features cannot delay core |

**Project I target:** working macOS end-to-end gaze interaction, intentional
control, configurable mappings, calibration/profiles, Turkish text entry, safe
hardware control and baseline measurements. **Project II target:** improve that
functional prototype into a robust, validated, cross-platform demonstration,
including UI-aware investigation, advanced personalization and evaluation.
Target-user/expert feedback needs appropriate approval and any required
institutional/ethical procedures; current developer captures are not a clinical
or accessibility-user study.

## Actual production implementation on verified main

Main at handoff start: `d175b4ce37eb11ede33ff75342af9b36ddd83d75`.
The only substantive production packages are Vision, Gaze and App. The proposed
architecture tree in docs is a future structure, not proof those modules exist.

| Source | Actual behavior and boundary |
| --- | --- |
| [vision/contracts.py](../../src/eye_tracker/vision/contracts.py) | Vendor-neutral frame/landmark contracts and source/extractor protocols, timestamps and finite XY |
| [vision/camera.py](../../src/eye_tracker/vision/camera.py) | OpenCV camera source with injected camera index, dimensions/timestamps and explicit open/read/close behavior |
| [vision/face_tracker.py](../../src/eye_tracker/vision/face_tracker.py) | Local MediaPipe Face Landmarker model, VIDEO mode, monotonic detector timestamps, vendor-neutral XY; missing/malformed face explicit |
| [vision/eye_topology.py](../../src/eye_tracker/vision/eye_topology.py) | Detector topology translated into two 16-point contours, four-point iris rings, corners and lid references |
| [vision/eye_features.py](../../src/eye_tracker/vision/eye_features.py) | Pixel-scaled eye geometry, iris ring mean, eye-box horizontal and corner-local-axis vertical; both valid eyes averaged, degeneracy rejected |
| [gaze/calibration.py](../../src/eye_tracker/gaze/calibration.py) | Per-presentation feature medians and session-local per-axis OLS `IndependentLinearMapping`; x from h, y from v |
| [gaze/estimator.py](../../src/eye_tracker/gaze/estimator.py) | Applies an already-fit mapping, finite unclipped estimates or explicit unavailability; no internal fitting/filtering |
| [app/gaze_pipeline.py](../../src/eye_tracker/app/gaze_pipeline.py) | One-frame composition of the above, with caller-owned resource lifecycle; no OS actions |
| [validation/real_calibration.py](../../validation/real_calibration.py) | Validation-only guided camera/target harness: nine calibration, sixteen held-out presentations, production path without Experiment 006 blink gate |

For an eye, let I be the four-ring-point mean, C the corner midpoint, s the
corner span, and n the corner-perpendicular unit vector oriented toward the
lower lid. Production h is `(I_x-min(contour_x))/(max(contour_x)-min(contour_x))`;
v is `((I-C)·n)/s`. Binocular output averages two valid eyes. These are numerical
features, not screen coordinates or ground-truth physical gaze. Mapping uses
`x=a_x h+b_x`, `y=a_y v+b_y`, fitted from that session's calibration only. No
clipping, production temporal filter, eye-opening correction or experimental
blink gate is added.

**IMPLEMENTED IN PRODUCTION** means these reusable components, not a delivered
interactive product. **EXPERIMENTALLY IMPLEMENTED** includes camera study UIs,
target/dwell harnesses, alternative filters/maps/representations and diagnostics.
**VALIDATED** applies only to the named protocol/run and its measured outcomes.
There is no production OS cursor adapter, complete gesture/intent/action system,
accessible keyboard, persistent-profile system, safe chair prototype or proven
Windows interaction. **PLANNED**, **BLOCKED**, and **HUMAN DECISION REQUIRED**
must remain distinct from implementation and validation.

## Chronological experiment evidence

These are published historical measurements, read from repository results and
PR evidence during handoff. No capture was parsed or evaluated for this document.
The dates below follow merged work, not an invented detailed capture diary.
Normalized screen errors must not be confused with physical display pixels.

| Period / evidence | Finding | Engineering limit / negative result |
| --- | --- | --- |
| Sep 23: [001 camera](../../experiments/001-camera-baseline/RESULTS.md), [002 landmarks](../../experiments/002-face-landmarks/RESULTS.md) | Tested Mac: 303/303 camera frames at 30.22 FPS; 864/864 face-present landmark frames at 25.07 FPS, 478 landmarks. MediaPipe 0.10.35 worked; 1.0.1 caused initialization SIGABRT on that setup. | Controlled short runs, no universal camera index or long-term portability claim. Local model required. |
| Sep 23: [003 features](../../experiments/003-gaze-features/RESULTS.md) | Horizontal LEFT/CENTER/RIGHT signal separated clearly. Eye-box vertical signal overlapped poorly. | Horizontal direction alone cannot deliver 2D selection. |
| Sep 23: [004 vertical](../../experiments/004-vertical-gaze/RESULTS.md) | Corner-local-axis binocular vertical means ordered UP<CENTER<DOWN across three runs. | Frame distributions overlap; CENTER shifts across sessions. Eye opening associated, glasses/head pose not isolated causes. |
| Sep 23: [005 stabilization](../../experiments/005-vertical-stabilization/RESULTS.md) | Short smoothing and conservative rejection reduced some jumps. | No method consistently improved overlap/repeatability across all runs; natural-opening run worsened. No production filter or blink threshold validated. |
| Sep 23: [006 mapping](../../experiments/006-2d-gaze-mapping/RESULTS.md), [Phase 0 review](../phase-0-exit-review.md) | Reproducible rerun: 3×3 calibration, sixteen distinct held-out trials; linear/affine x/y ordering 21/21. Linear x/y MAE ≈0.0277/0.0699, affine ≈0.0301/0.0721. Phase 0 gate met. | Approximate same-user/same-session mapping, no cursor or pixel-accurate interaction. Earlier CSV export failed and left header-only file; retain rerun identity. Phase 0 review is historical, predating reusable production code. |
| Sep 24–25: production slice and [PR #43](https://github.com/cagriinan46/eye-tracker/pull/43) | Reusable adapters/features/calibration/estimator/pipeline merged. Çağrı validation x/y MAE 0.0519/0.1257, ordering 21/21. | Production-path capture works, but vertical error remains large and no interaction product is delivered. |
| Sep 25: [Fatih's separate PR #43 report](https://github.com/cagriinan46/eye-tracker/pull/43#issuecomment-5831705442) | Independently reported x/y MAE 0.071328/0.117019; x ordering 20/21, y 4/21. Held-out y predictions clustered 0.500–0.518; calibration predictions also near center. | A near-center estimate can have modest MAE without gaze information. Separate participant/run, not pooled with Çağrı; raw file unavailable on this Mac. |
| Sep 29: [collapse](../../experiments/vertical_collapse_diagnostics/RESULTS.md) | Two Çağrı sessions retained vertical ordering 21/21, slopes ≈43.34/43.83. One center-row shift ≈−0.00464 amplified to ≈−0.203 y. | No collapse on these runs; does not explain Fatih's flat output or establish physical cause. |
| Sep 29: [drift](../../experiments/vertical_drift_diagnostics/RESULTS.md), [decomposition](../../experiments/vertical_error_decomposition/RESULTS.md) | Exact CENTER checkpoints exposed both calibration-time fit residual and later feature-driven output change. | Drift was not a universal immediate jump or monotonic trend. Exact additive attribution only for identical targets; no anatomical/head-pose cause identified. |
| Sep 30: [mapping variants](../../experiments/vertical_mapping_evaluation/RESULTS.md), [reverse-order variability](../../experiments/vertical_position_variability/RESULTS.md) | Piecewise row anchors improved calibration residuals but worsened held-out y MAE in both sessions. Repeated identical targets varied materially; some top-row X-associated behavior recurred in reversed order. | Better fit≠better transfer. No general X law, universal correction or causal time explanation. |
| Sep 30–Oct 1: [offset](../../experiments/vertical_offset/RESULTS.md), [fixed CENTER live](../../experiments/fixed_center_live_validation/RESULTS.md) | Offline fixed offsets and two fresh live CENTER-anchor sessions lowered errors; live ordering stayed 17/21 and 20/21. | Experimental bias correction only. Refresh damaged ordering in one replay; repeat variability and cross-user behavior unresolved. No production correction selected. |
| Oct 1: [mapping sensitivity](../../experiments/vertical_mapping_sensitivity/RESULTS.md), [controlled live](../../experiments/vertical_sensitivity_live_study/RESULTS.md), [covariates](../../experiments/vertical_feature_covariates/RESULTS.md) | Compressed calibration spans increase fitted slope and amplify shifts. Three live studies also showed distinct within-session feature movement. Both eyes often moved with the same sign. | Gain and feature variability are different contributors. Eye-opening/head-center associations are descriptive, not a proved mechanism or correction. |
| Oct 3: [corrected eye opening](../../experiments/eye_opening_controlled_study/RESULTS.md), [PR #59](https://github.com/cagriinan46/eye-tracker/pull/59) | Three corrected protocol-v2 sessions preserved narrow<natural<wide opening order; vertical response was nonmonotonic and row-dependent. | First pilot was protocol-invalid; PR59 closed unmerged. Aperture alone cannot support a simple correction. Preserve invalid data separately. |
| Oct 3–4: [eye geometry](../../experiments/eye_geometry_decomposition_study/RESULTS.md), [face reference](../../experiments/face_reference_corner_stability_study/RESULTS.md) | Opening contrasts changed detected corner/reference geometry; calibration-only face alignment retained systematic corner-span changes. | Mathematical decomposition/detected-landmark motion is not anatomical ground truth. 2D fits cannot resolve physical depth/pose/true fixation. No correction selected. |
| Oct 4: [alternative formulas](../../experiments/alternative_vertical_feature_benchmark/RESULTS.md), [lid-reference holdout](../../experiments/lid_reference_vertical_feature_benchmark/RESULTS.md) | Fixed alternatives did not jointly improve discrimination, opening contrasts and repeats. Both predeclared lid formulas failed their six-part holdout rule. | Historical feature search yielded no production winner; smaller variance can erase gaze signal. Those data roles differ from the later geometry-2 holdout. |
| Oct 4: [coarse v1](../../experiments/coarse_gaze_targeting_validation/RESULTS.md) | Natural primary sessions acquired 70/81 regions (86.42%). | Width 0.28, tiny 0.02 gaps and 300 ms dwell were permissive; favorable coarse results do not establish intentional precise selection. Different setup/invalid opening manipulation excluded from primary inference. |
| Oct 4: [intentional v2](../../experiments/intentional_gaze_targeting/RESULTS.md) | Smaller width 0.20, 1 s dwell and nongated cue yielded 20/54 (37.04%) over two valid sessions. Predeclared <60% band locked even with a hypothetical perfect third run; collection stopped. | Inadequate for this stricter geometry. Planned three-session repeatability study incomplete; reset-gated pilot invalid. Not an OS interaction subsystem. |
| Oct 4: [offline v2 solution benchmark](../../experiments/gaze_failure_solution_benchmark/RESULTS.md) | Exact replay of 6,105 predictions/54 outcomes; fixed EMA, median-5, calibration-axis median map and affine map all failed predeclared gates. | No selected filter/map. Early production-success stops censor alternative cases; calibration fit does not establish held-out targeting success. |
| Oct 6: [fixed-window diagnostic](../../experiments/fixed_window_gaze_diagnostic/RESULTS.md) | Complete 54 windows / 4,526 usable predictions. Feature ordering held in all six blocks/row-column checks; transfer shifts and repeated-target ranges remained. Calibration-median y MAE 0.063713/0.078086 already nonzero. | Outcome C: representation transfer **and** independent-linear fit implicated. Prioritize bounded representation normalization investigation before richer static mapping; no physical cause established. |
| Oct 7: [Stage A / PR69](https://github.com/cagriinan46/eye-tracker/pull/69), [preregistration](../../experiments/raw_geometry_gaze_diagnostic/PREREGISTRATION.md) | Same-detector-result raw eye/face XYZ instrumentation; completed geometry-1 development and geometry-2 holdout captures. | Raw geometry remains private/local. Instrumentation is not a new production representation or performance result. |
| Oct 7: [Stage B1 / PR70](https://github.com/cagriinan46/eye-tracker/pull/70) | Exactly R0/R1/R2 implemented and frozen before geometry-2 outcomes. | Synthetic/calibration-only formulation, no candidate success claim. |
| Oct 8 handoff baseline: [Stage B2 / PR71](https://github.com/cagriinan46/eye-tracker/pull/71) | First authorized computation aborted at output serialization; no numerical outcomes retained. Historical CI failure subsequently fixed, actual CI 445 passed. | B2 INCOMPLETE, geometry-2 consumed, no R1/R2 scientific decision. Human recovery decision required. |

The PR #43 comment values were independently checked through GitHub during this
handoff. They remain a human-reported historical session, not a new capture
analysis. [Historical project status](../PROJECT_STATUS.md) preserves more
detailed measurements; each experiment's README/RESULTS governs its protocol,
exclusions and limitations.

## Latest representation work and permanent freeze

Stage A's experiment-owned instrumentation uses the same detector result to save
selected eye contours, iris rings and non-eye face XYZ plus available pose
diagnostics. R0 reconstruction verifies the capture against production. It does
not run a second detector or change production behavior.

Stage B1 froze at **`c4ad261b63fcce3b3998ce8335f8d81fa2118b32`**, squash-merged
through PR70 into main d175b4c. Whole-tree identity was verified at handoff;
original commit identity remains authoritative despite different ancestry.
Read [REPRESENTATION_FREEZE](../../experiments/gaze_representation_benchmark/REPRESENTATION_FREEZE.md)
for exact algorithms, landmarks, numerical tolerances, metrics and availability:

- **R0:** unchanged production pixel-XY feature geometry.
- **R1:** pseudo-pixel XYZ `(xW,yH,zW)`, with component-wise calibration medians
  of exactly twelve non-eye anchors as reference. A deterministic proper 3D
  least-squares similarity (translation, rotation, one scale, no reflection)
  aligns eye geometry; projected XY enters the same production feature equations.
  Relative MediaPipe depth is not metric 3D or physical head-pose truth.
  Missing XYZ/rank degeneracy/SVD/nonfinite failures make it unavailable; no
  production/2D fallback.
- **R2:** per-eye `(p-C)/s` corner-centered/span-normalized XY; corresponding
  sixteen-contour-point calibration medians form a fixed reference. One ordinary
  unweighted full-rank affine least-squares fit maps the current contour to that
  reference; the same affine transforms the iris ring. Features use the fixed
  reference geometry and production equations, then require both valid eyes for
  the production mean. Missing/degenerate/rank-deficient/nonfinite solutions are
  unavailable. This is not either historical lid formula.

Each session/candidate builds references from its own calibration only, then
fits IndependentLinearMapping from nine equally weighted presentation medians
(minimum five usable frames per presentation). No validation fitting, transported
session map, subset fit or feature search. Primary [0,3), secondary [0.8,3), and
1.5 s half diagnostics, feature/screen/transfer/drift/availability/common-frame
metrics and the five geometry-2 gates are immutable. A gate pass would justify
later live validation, not a production replacement. No R3 or post-outcome fix
to scientific definitions is permitted.

Stage B2 evaluator was sealed at **`14843fd0e43f4e7f7e661b74498c32414452d84d`**.
Original failure report commit: **`58a8b860a164fd67c2174978004e22221d5a17d3`**.
Current PR71 head/CI fix: **`b0cb40dbb727eacc0091d5324285200e57dc6490`**.
Its [RESULTS failure report](https://github.com/cagriinan46/eye-tracker/blob/b0cb40dbb727eacc0091d5324285200e57dc6490/experiments/gaze_representation_benchmark/RESULTS.md)
and JSON are on the active unmerged branch, not main. B2's serialization failure
lost outcomes without changing formulas; preserve its one-shot marker and consult
[STAGE_B2_RECOVERY](STAGE_B2_RECOVERY.md) before any proposed recovery.

## Limits, priorities and navigation for engineering

Vertical transfer/accuracy/stability remains a blocker. Most studies are same
participant, short controlled Mac sessions, with no long-term or target-user
usability evidence. Fatih's weak vertical result is a separate unresolved
cross-user observation. Neither correct directional ordering, favorable
calibration fit, lower variance, nor one successful target establishes reliable
pixel-accurate selection. No experiment identifies a physical cause conclusively.

The product still lacks the interaction/profile/keyboard/hardware/Windows
subsystems listed above. Privacy telemetry, institutional evaluation procedures,
and real actuator safety need approved work. Test success alone cannot resolve
these empirical or governance limits. Avoid indefinitely continuing gaze
research without estimating engineering value against the first-term prototype.

For each next task, Claude should propose bounded cost, measurable criteria and
tradeoffs, then obtain Fatih's approval. Çağrı's suggested denser/wider 5×5
near-edge calibration comparison against the existing 3×3 baseline is an
**unapproved future mapping experiment**, not B2 recovery or production strategy.
No direction is selected by this handoff.

Use [DATA_INVENTORY](DATA_INVENTORY.md) for missing/private assets and transfer;
[validation README](../../validation/README.md) for approved environment/protocol
context; [tests](../../tests/) and [CI](../../.github/workflows/ci.yml) for checks;
and [WORK_LOG](WORK_LOG.md) for subsequent changes. Read-only source/document
inspection is sufficient to recover context; do not execute a capture or
evaluation command without an approved task.
