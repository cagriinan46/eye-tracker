# Cross-application semantic discovery audit — 2026-10-22

Measured on macOS at `f5cd165`, after PR #120. This audit uses representative
daily tasks to prioritize shared discovery work; it does not restrict semantic
gaze to an application allowlist or assume all users need the same applications.
No camera, human gaze test, clicks, typing, calculations or setting changes were
performed. Applications were brought to the foreground for read-only discovery.

## Method

Five production-path scans per context, followed by one separate supplemental
inventory of actions advertised by unsupported roles. Production role, geometry,
hit-test, completeness and timing limits were unchanged. Exception tracing adds
overhead, so timings are diagnostic observations, not performance benchmarks.

Finder displayed a newly created folder containing a sample text file and folder;
TextEdit opened that sample file. Calculator and System Settings used their current
windows. Normal Chrome used its current page; no navigation or profile changes.
A separate owned Chrome process used a disposable profile, the repository's local
control fixture, and the already documented full-accessibility startup flag.

The final fixture run stopped when foreground focus changed, preserving the user's
chosen application. Its four completed scans are included; the planned fifth scan,
supplemental inventory and context-switch check were not performed. Overall:
**29 production-path scans plus 5 supplemental inventories, 34 total**.
The owned test Chrome was terminated. Other apps and temporary test files were
preserved. No UI labels, page content, coordinates or personal paths are published.

## What worked, and what that does not establish

| Context | Complete production scans | Targets per complete scan | Interpretation |
| --- | --- | --- | --- |
| Finder test folder | 5/5 | 8 | Four buttons and four radio buttons; file/folder opening not supported by this count |
| System Settings current pane | 0/5 | None published | Invalid native child reference aborts the scan |
| TextEdit sample document | 5/5 | 3 | Three buttons; text area is outside current target roles, so this is not editing support |
| Calculator current window | 5/5 | 55 | 54 buttons and one checkbox; a strong next candidate for a later human targeting test |
| Normal Chrome current page | 5/5 | 21 | Buttons/popup controls; web press controls still lack the required capability signal |
| Prepared Chrome local fixture | 4/4 completed | 15 | Browser/window controls plus the five expected fixture controls; final checks interrupted |

Supplemental inventories for the first five contexts had the same aggregate
status/count as their preceding scans. Inventory reads are **not** additional
independent production-path trials or proof that an unsupported role is visible,
enabled, safe to select or meaningful for a particular user task.

Zero published preview-only targets were observed. In System Settings, unknown-
enabled controls no longer cause the earlier immediate rejection, but later
failure still discards the entire snapshot. This audit therefore does not establish
successful end-to-end unknown-enabled highlighting in that app.

## Reproducible blocker: System Settings

All five production scans failed with `AXRole` read error `-25202`. The same
role-level ancestry was recorded each time:

```text
AXWindow → AXGroup → AXSplitGroup → AXGroup → AXScrollArea
         → AXOutline → AXRow → AXCell → unread child
```

The local macOS SDK's `AXError.h` identifies `-25202` as an invalid AX element
reference. The matching ancestry narrows the affected subtree; it does not prove
that the same native object recurred, that its lifetime expired, or that it is
invisible. Forty-one `AXRow` nodes and forty-one `AXCell` nodes were visited in the
supplemental inventory.

This is different from both absent enabled-state metadata and startup messaging
error `-25204`. Five independent scans did not recover, so a generic "sleep and
retry" is not yet a justified remedy. Do not silently skip the invalid node:
its role, geometry and possible descendants are unknown, making the neighborhood
incomplete under the current contract.

Next investigation: instrument bounded parent/child enumeration and compare fresh
references while maintaining the same foreground window. Determine whether the
application supplies a stale child, whether an alternate complete enumeration is
available, or whether the contract needs a separately reviewed change. A successful
fix must preserve whole-snapshot rejection when completeness cannot be established.

## Shared coverage gaps

| Observed role/capability | Contexts | Consequence / next design question |
| --- | --- | --- |
| `AXMenuButton` with `AXPress` | Finder (4), Settings (2 before failure), TextEdit (1), Calculator (1) | Promising shared preview extension; distinguish the menu-opening control from menu-item lifecycle |
| `AXTextField` with `AXPress` | Normal Chrome | Address/search field is not currently eligible despite press metadata; evaluate preview targeting separately from text entry |
| `AXTextField` with `AXConfirm`/`AXShowMenu` | Settings | Do not equate confirm/menu actions with press; focus semantics need their own design |
| `AXTextArea` with `AXShowMenu` | TextEdit | Three found buttons do not make document editing usable; text focus/entry remains separate work |
| `AXImage` with `AXOpen`/`AXShowMenu` | Finder sample file/folder | Opening a file differs from selecting a press target; generic item/open semantics are missing |
| `AXRow` / `AXCell` | Settings and normal Chrome | Row selection is not covered by the five-role press allowlist; do not assume every structural row is actionable |
| `AXSlider` with increment/decrement | Finder | Needs a value-adjustment interaction; cannot be enabled merely by treating it as a button |
| Scroll areas / scrollbars | Multiple contexts | Scrolling is a separate interaction, not established by target discovery |
| `AXStaticText` sometimes advertises press | Finder and Settings | Roles alone are insufficient, but advertising an action alone is also insufficient; requires bounded capability/geometry investigation |
| Menu-bar items | All surveyed apps | Existing closed-menu exclusion and menu lifecycle boundary remain intentional |

Normal Chrome exposed 102 nonzero-area supported web-role nodes rejected for
missing `AXPress` in the last production scan (91 links, 6 buttons, 4 popup controls,
1 checkbox). Those are **visited rejected nodes**, not a visible-control count.
Prepared Chrome fixture success does not demonstrate a normal-profile remedy.

Native action lists can contain custom strings with labels. The diagnostic now
stores only allowlisted standard action constants plus a `custom_action` marker;
initial custom labels were redacted from the local report after inspection.
No page text, titles or values were requested. The five supplemental inventories
must remain distinct from baseline scans because their extra native reads can
introduce additional errors or timing cost.

## Context invalidation

Finder, TextEdit, Calculator and normal Chrome each established a valid discovery
session. Switching to another application invalidated it, and returning did not
revive it. Checks completed in 0.14–0.20 seconds, below the two-second session
lifetime. This verifies session invalidation in those four cases, not instantaneous
outline hiding or every possible window transition.

Settings had no valid starting snapshot, so its invalidation check could not be
evaluated. The fixture check was interrupted. An earlier same-app Finder check
(on `ca2c599`) separately verified that a native window-reference change invalidated
a session while the foreground PID stayed unchanged; it is not repeated here.

## Proposed follow-up order

This is a work queue derived from measurements, **not a roadmap amendment**.
Implementation scope and new interaction contracts remain subject to issue review.

1. **Discovery reliability:** investigate the invalid child in the Settings
   outline/cell subtree, without bypassing completeness. Keep normal Chrome
   accessibility preparation (#116) as a distinct compatibility investigation.
2. **Shared preview coverage:** evaluate press-capable menu-opening buttons and
   text fields across the apps above. Require geometry, visibility, context,
   disabled-state handling, unknown-state tagging and ambiguity regressions.
   Do not implement one resolver per app or add all roles indiscriminately.
3. **Task-level gaps:** design generic file/item selection, text focus and scrolling
   within their appropriate roadmap phases. They cannot be claimed from successful
   button counts; no new activation behavior is authorized by this report.
4. **Later human validation:** once discovery is stable for the chosen tasks,
   compare intended-target selection, wrong targets and abstentions. Calculator
   and the controlled browser fixture provide bounded starting contexts. Gaze
   calibration/camera quality remains an independent unresolved measurement topic.

## Evidence and limits

Local raw aggregate report: `validation/results/broad-discovery-bw6c74xb/report.json`.
Sanitized harness snapshots: `probe.py` and `coverage-base.py` in that directory.
The archived harness references its coverage helper under `/tmp`; it is an
experimental record, not a supported installed runner.

Raw records are intentionally not committed. These are single-device, short-run
observations with current window contents. No full application coverage percentage,
end-to-end task completion, target-user usability, gaze accuracy or Windows-native
compatibility is established. No production source changes were made for this audit.
