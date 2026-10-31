# Desktop interface implementation plan

Goal: implement the owner's October 31 request for a simple, modern, usable desktop demo with sidebar navigation, restrained motion and color themes.

The owner delegated visual decisions and requested implementation today. Extend the existing lavender identity and Python/pywebview UI; no framework migration or new runtime dependency. The sidebar offers home, calibration preparation, practice, settings and help. Calibration and trials retain their full-window geometry. Color settings change appearance only; camera and calibration remain deliberate actions. Themes: lavender, sunflower, sage. Default: dark lavender. System reduced motion is respected, with an additional explicit reduction setting.

## Tasks
- [x] Add regression tests for preference persistence, corrupt/invalid data and write failures that must not interrupt calibration.
- [x] Implement a small preferences module and bridge command; atomically save only validated appearance settings under ~/.eye-tracker/desktop-preferences.json.
- [x] Refine HTML/CSS and navigation in app.js; retain protocol actions and all live measurement acknowledgement/region handling. Preparatory tabs are accessible before the camera starts. Add genuine empty, loading, error and ready states.
- [x] Exercise page navigation, themes, keyboard/reduced motion, loading/error recovery and real bridge in a native window with camera off; visually inspect normal and minimum supported sizes.
- [x] Run desktop/full tests, Ruff and whitespace checks. Document limits, commit and push the feature branch, open a PR for human review.

## Review focus
Theme changes must not reset calibration. Settings write failures preserve the prior state. Calibration and selection targets never animate or move with hover. Tabs must not interrupt a running measurement unexpectedly. Disconnected bridge must explain recovery; browser preview must never invent camera data or results.

No new OS control, profile management, model switching, gaze algorithm, hardware or calibration protocol. Initial setup navigation remains pointer/keyboard operated; hands-free shell navigation is not claimed.

## Verification outcome
- Issue #141; branch `feature/desktop-interface`, based on merged PR #140 (`785404c`).
- 880 tests passed in the prepared full test environment; Ruff lint/format passed (348 Python files). Desktop subset: 47 passed.
- Native camera-off check passed on 1280×800 and 960×640 windows; initial small-window CTA overflow corrected and confirmed. Five tabs, all three themes with restart persistence, reduced motion, synthetic camera loading/error, ready/home/practice and pause checked.
- Independent review found a minor rapid-preference state race; local preference state and poll generations now prevent stale snapshot restoration. No blocking finding.
- Initial full-suite attempt in the GUI-only environment: 864 passed, 16 SVR-related failures due to absent sklearn. Full suite then passed using the existing full environment; no packages installed. Repository-local .venv executable links are stale and were not modified.
- Static design scanner warnings: preview image has no source while deliberately hidden with camera off; scanner cannot see injected stylesheet and reports default 16px headings. Actual native captures verified styled heading hierarchy and no broken image.
- Native check uses synthetic states for flow validation, not human accuracy evidence. No camera capture in this task. Human calibration/selection and Windows remain unverified for this presentation update.

## Explicit owner feedback superseding the initial scope above

The owner requested simpler copy/sidebar, fast camera preview and measured eye
close-ups, research-style calibration indicators with theme colors, five short
checks, and web-like controls instead of four shapes. The owner subsequently
explicitly authorized showing the real system cursor in that local demo. These
requests supersede the initial no-OS-actions/stimulus-color constraints: movement
only is enabled on focused macOS demo screens; no OS clicks. Same PR142, issue141.

Implementation: bounded latest capture plus separate preview IPC; registered web
scenario with target-size records; nonblocking gated native cursor presentation.
Read-only review identified an AppKit lock-wait risk; a failing regression test
reproduced it, then nonblocking sampling and deferred pause fixed it. Native camera
preview and synthetic interaction/measurement checks are recorded separately from
human selection accuracy, which still needs a participant session.

Follow-up verification: 888 tests passed, Ruff lint/format passed (354 files),
JavaScript syntax and whitespace checks passed. Native UI test covers all eight
control regions and actual local form/tab behaviors, themed calibration counters
and center dot. Native cursor mapping verified expected and actual(756,312) in a
1280x772 logical viewport; no OS clicks. Initial synchronous cursor assertion ran
before WindowServer applied focus/movement; event-loop-delayed verification passed.
976 historical numeric predictions replayed exactly (fit/raw/filter max error0).
Live camera timing: native UI22.13FPS vs camera22.43FPS; independent camera-only
23.09FPS despite requested30FPS. Human web-selection accuracy remains unmeasured.
