# Stage B2 — one-shot evaluation aborted during serialization

**Stage B2 is incomplete. No R1/R2 PROMISING/FAIL outcome is available.**
The first authorized computation on geometry-2 was attempted exactly once. Both
sessions' aggregate calculations returned, but JSON serialization failed before
any aggregate file was written or outcome value was printed. The process exited
and the in-memory result was lost. The holdout must not be described as unopened
or as still untouched after this attempt.

## Immutable source and merge provenance

- Frozen definitions: `c4ad261b63fcce3b3998ce8335f8d81fa2118b32`.
- Evaluator sealed before outcome computation:
  `14843fd0e43f4e7f7e661b74498c32414452d84d`.
- PR #70 merged at `2026-10-07T17:54:37Z`, squash commit
  `d175b4ce37eb11ede33ff75342af9b36ddd83d75`.
- The original freeze is **not an ancestor of main** because of squash merging.
  Its complete tree and merged main tree were verified byte-identical. Nineteen
  frozen and transitive source files passed byte-for-byte verification against
  the original commit before the attempt.
- Exactly R0/R1/R2 were implemented. Production, frozen formulas, landmarks,
  coordinate scaling, references, transforms, availability, aggregation, mapping,
  windows, metrics, gates and original representation tests were not changed.
- No evaluator code changed after the attempt. No retry, tuning, replacement,
  parameter search, further collection or live interaction followed it.

## Exact capture identity and integrity

| Capture | Role before first evaluation | SHA-256 | Bytes |
| --- | --- | --- | --- |
| geometry-1 | Development | c7f64d5e5e6a305b689c3488f20ef1a4a4932f797c265496b1df5be7dd97ae25 | 42114167 |
| geometry-2 | Untouched final holdout | cce93847ba928413a5571e92fb94318783a2661edb32770d181ce128042f9409 | 42100225 |

Both captures passed protocol `raw_geometry_gaze_diagnostic` version 1, geometry
schema 1, participant/session/role identity, complete nine calibration plus
27 validation presentations with the frozen schedule/windows, raw frame identity
and geometry consistency, numerical reconstruction of logged usable R0 features,
and reconstruction of each session's fresh calibration-only production map.
Both inputs passed integrity before any candidate outcome computation.

| Integrity-only coverage | geometry-1 | geometry-2 |
| --- | --- | --- |
| Calibration raw geometry frames | 296 | 296 |
| Validation raw geometry frames | 2261 | 2259 |
| Complete XYZ frames | 2557 | 2555 |
| Missing geometry attempts | 0 | 0 |
| Partial XY / partial Z / missing Z frames | 0 / 0 / 0 | 0 / 0 / 0 |
| Logged usable R0 validation observations | 2261 | 2259 |
| Logged unavailable R0 validation observations | 0 | 0 |
| Failed camera reads | 0 | 0 |
| No-face observations over full acquisition | 0 | 1 |

These are capture integrity/availability facts, not candidate outcome metrics.
Both input SHA-256 hashes and byte sizes were independently checked unchanged
after the failed attempt. Neither capture was modified or committed.

## Failure and diagnostic evidence

The attempt failed at `evaluate.py:392`, calling `serialize(result)` at line 314:

```text
TypeError: Object of type bool is not JSON serializable
```

`ratio()` can retain a NumPy float64 from feature transfer statistics. Comparing
that value with the frozen threshold can create a NumPy boolean (for example,
criterion 2's `transfer_ratio <= 0.75`), which the standard JSON encoder rejects.
A standalone synthetic expression `numpy.float64(0.5) <= 0.75` followed by
`json.dumps({"pass": value}, allow_nan=False)` reproduced the exact exception.
This diagnostic did not read participant data or repeat any outcome calculation.

The synthetic end-to-end captures had zero baseline transfer, exercising the
undefined-denominator branch and returning a built-in Python False. Primitive
gate tests used Python floats. Thus the tests did not exercise serialization of
a NumPy boolean arising from a nonzero normalized-transfer comparison. This is
an evaluator serialization defect, not evidence that any representation passed
or failed its scientific gate.

The ignored one-shot marker remains at
`.venv/stage-b2-one-shot-evaluation.json`, with `status: "started"`, sealed evaluator
commit and input hashes. It was not deleted or reset. The runner refuses rerun
when this marker or output files exist. No reconstruction/re-evaluation was
performed to recover the lost metrics. No serialization patch was applied after
the attempt.

## DEVELOPMENT RESULT — geometry-1

The descriptive outcome calculation completed in memory, but no numerical
outcome aggregate survived serialization. Per-presentation/target/row/column
feature medians, separation/direction/ordering, MAD/IQR, transfer, block/half
drift, calibration predictions/residuals/gains, screen residual/error summaries,
per-eye candidate availability and common-frame metrics cannot be reported.
The capture-integrity facts above are the only retained session measurements.
No candidate ranking or development-based redesign occurred.

## UNTOUCHED HOLDOUT RESULT — geometry-2

This was the first authorized holdout computation. Its numerical aggregate was
not persisted. No candidate outcomes were displayed, ranked, selected or used to
alter any formula, map, parameter, window, metric, threshold or availability rule.
The final holdout is now considered consumed by this failed attempt; it must not
be silently reclassified as untouched for another evaluation.

| Representation | Primary x MAE | Primary y MAE | Normalized vertical transfer | Vertical ordering | Candidate/common-frame coverage |
| --- | --- | --- | --- | --- | --- |
| R0 | Not retained | Not retained | Not retained | Not retained | Logged native R0: 2259/2259; shared coverage not retained |
| R1 | Not retained | Not retained | Not retained | Not retained | Not retained |
| R2 | Not retained | Not retained | Not retained | Not retained | Not retained |

The fixed evaluation used primary [0,3), secondary [0.8,3), and the fixed 1.5 s
half boundary. Each session's references and binocular/monocular independent
linear maps were constructed from that session's nine calibration presentations
only. Common-frame analysis used the original fixed maps without rebuilding
references or fitting validation labels. These are implementation/provenance
facts, not substitute numerical results.

## Frozen five-part gate — no decision can be issued

The following frozen thresholds remain unchanged. No unavailable value is counted
as a pass, and no partial-PROMISING class or substitute candidate is introduced.
Native and exact common-frame component values were intended to be explicit;
neither numerical view was retained.

| Criterion | R1 value | R1 pass/fail | R2 value | R2 pass/fail |
| --- | --- | --- | --- | --- |
| 1: primary y-MAE candidate/R0 <= 0.80 | Not retained | Cannot determine | Not retained | Cannot determine |
| 2: normalized vertical-transfer ratio candidate/R0 <= 0.75 | Not retained | Cannot determine | Not retained | Cannot determine |
| 3: lose none of R0-correct vertical ordering checks | Not retained | Cannot determine | Not retained | Cannot determine |
| 4: primary x-MAE candidate/R0 <= 1.15 | Not retained | Cannot determine | Not retained | Cannot determine |
| 5: no target leakage, validation fit, future-frame dependence or post-holdout tuning | Source/provenance supports true | PASS (provenance only) | Source/provenance supports true | PASS (provenance only) |

**R1 overall: unavailable; no PROMISING/FAIL claim.**

**R2 overall: unavailable; no PROMISING/FAIL claim.**

Missing persisted results do not justify calling the preregistered alternatives
scientifically successful or failed. No production replacement is justified.

## Machine-readable failure record, checks and limitations

[results_summary.json](results_summary.json) contains only freeze/evaluator
provenance, capture hashes/sizes and integrity aggregates, exception/diagnostic
facts, check results, zero retries and null outcome metrics/decisions. It is a
failure record, **not** the requested completed numerical benchmark summary.
It contains no raw participant samples, geometry, frames or facial imagery.

Before the attempt, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`,
`git diff --check` passed, and the full pytest suite passed **445 tests**, including
23 synthetic evaluator tests. A filesystem audit guard prohibited opening both
real participant captures during tests. Independent source review also completed
before the attempt; it did not access real captures. Passing synthetic checks did
not establish successful real-capture serialization.

The requested final numerical report, candidate decisions and complete aggregate
outcome summary remain unresolved. Recovery would require another computation
because the original process and its in-memory aggregates are gone. Such a retry
is outside the current one-shot authorization. This task stopped without
re-evaluation or post-holdout changes to the evaluator or frozen representations.
