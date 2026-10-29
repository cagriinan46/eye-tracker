# Desktop target-selection demo — implementation proposal

Status: visual concept, functional scope and Python + pywebview approved; framework decision merged in #135.

## Decision for the human team
Use pywebview for this desktop presentation prototype, with local HTML/CSS/JavaScript and the existing Python3.12 MGazeNet pipeline. This choice is recorded in docs/architecture.md by #135. Packaging remains TBD. Alternative: PySide6/QML, requiring a separate implementation of the approved visual layout. Recommend pywebview to reuse the visual concept and keep Python inference. macOS uses WKWebView; Windows requires a supported Edge WebView2 runtime. Windows execution must not be claimed verified without Windows testing. Installer/signing/distribution strategy remains unresolved and outside the first runnable prototype.

## Approved outcome
One native desktop window: preparation with camera preview, fresh calibration, independent short validation, four large target selection, and real session results. Dark purple/lavender styling matches the reviewed HTML. No OS clicks or hardware movement. Camera remains off until explicitly started. User-facing states include camera unavailable, tracking lost, loading, paused, calibration timeout, retry and close.

## Proposed implementation boundaries
- app/desktop_demo: lifecycle and narrow Python/UI bridge; packaged local UI assets; no remote page navigation.
- gaze adapter: reuse frozen upstream MGazeNet and current13-point/45-frame Ridge0.1 calibration behavior without deploying failed head corrections. Keep dependency optional and preserve existing runner.
- intent: reuse existing dwell machinery where compatible; explicitly reset on tracking loss, stale samples, target change, pause, focus loss and layout change. Initial dwell1.2seconds is a demo setting, not an accuracy claim.
- evaluation: record intended target, selected target, correct/incorrect/timeout, active elapsed duration and modality. Real-eye and synthetic/mouse checks must never share a reported success rate. No raw images saved.
- coordinate handling: calibrate against measured drawable viewport, not guessed desktop pixels. Invalidate calibration on geometry change; preserve valid mapping across preparation/target layouts. Hide distracting prediction feedback during calibration and validation.

## Work sequence
1. Inspect remote open PRs and unmerged work; synchronize main; create isolated feature branch. Record the authorized task as a focused issue and link it in the PR. Preserve experiment logs/environments.
2. Write tests for session transitions, dwell interruption, stale samples, layout invalidation and metrics denominators; implement pure session logic first.
3. Add optional desktop window and local assets with mocked observations; verify preparation, calibration target flow, pause/retry, failure/close lifecycle without camera.
4. Connect current model/real camera adapter; keep startup responsive, bounded frame delivery and orderly resource release. Validate all commands and serialize transitions across bridge threads.
5. Run relevant tests, Ruff and native window smoke check; inspect actual rendered screens. Real gaze validation follows a user-paced camera session and is reported separately.
6. Review diff, commit, push feature branch and open PR; human merge only. Provide branch/commit/check results and Windows/packaging limits.

## Completion evidence
Runnable native macOS window, actual fresh calibration connected to gaze-driven four-target selection, persisted numeric results, automatic checks and a repeatable launcher. Do not equate a browser mockup or a mouse-mode test with working eye control. Include source and model provenance in measurement records.

## Execution ledger

- Framework approved by user and merged in #135. Task #136; feature/desktop-target-demo starts from faca904.
- Ruling: keep MGazeNet desktop integration in experiments/desktop_demo, with reusable region dwell in intent. This is an explicitly labeled presentation prototype, not replacement of production gaze contracts.
- Ruling: Python bridge, camera/inference worker and serialized state access; browser rendering acknowledgements precede target sampling. Resize/move invalidates calibration; blur pauses selection and interrupts calibration.
- [x] Pure region dwell and measured session protocol, tests.
- [x] Local model adapter and desktop lifecycle, error/cleanup tests.
- [x] Approved UI connected to real state, mock preview explicitly separate.
- [x] Native smoke, all tests/checks and independent review. Commit/push/PR tracked in GitHub.

Validation: native macOS cold start and synthetic UI protocol check passed without camera; fresh independent reviewer checked whole branch and verified fixes. Real participant accuracy and Windows runtime remain untested.

Final checks:856 tests passed; repository-wide Ruff lint/format and diff whitespace checks passed. Native window confirmed at1280x772 drawable pixels; four target rectangles fit and render acknowledgement works. GUI detector findings for missing preview src and flat typography were checked against the native rendering (camera-off placeholder; real34px heading). No camera opened during verification.
