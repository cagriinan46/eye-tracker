---
name: Experiment
about: Investigate an uncertain technical question through measurement
title: '[Experiment] '
labels: ''
assignees: ''
---

## Question

What technical question are we trying to answer?

## Hypothesis

What do we currently expect to happen?

A hypothesis is allowed to be wrong.

## Why This Matters

Explain what future engineering decision depends on this result.

## Experiment Setup

Describe the planned setup at a high level.

Do not invent implementation details that have not yet been approved.

## Measurements

Define what should be measured.

Examples may include:

- accuracy,
- latency,
- frame rate,
- gaze error,
- false activations,
- stability.

Do not invent target thresholds unless they have already been approved.

## Acceptance / Completion Criteria

The experiment is complete when:

- [ ] the planned experiment was executed,
- [ ] relevant measurements were recorded,
- [ ] limitations or failures were documented,
- [ ] a conclusion was written.

An experiment does NOT need to confirm the hypothesis to be considered successful.

## Result

Fill this section after running the experiment.

## Conclusion

State what was learned and what engineering decision, if any, should follow.

If the result implies a major architectural decision, do not silently implement it. Escalate it for human review and potential ADR creation.
