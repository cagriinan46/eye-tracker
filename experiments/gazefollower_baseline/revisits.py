"""Opt-in three-pass collection; unchanged total samples and no model fitting."""

import numpy as np


def revisit_plan(points):
    points = np.asarray(points, dtype=float)
    if points.shape != (13, 2) or not np.isfinite(points).all():
        raise ValueError("Expected 13 finite calibration locations")
    if (points < 0).any() or (points > 1).any() or len(np.unique(points, axis=0)) != 13:
        raise ValueError("Expected distinct normalized calibration locations")
    visits = [dict(visit=0, target_id=None, target=(0.5, 0.5), **{"pass": 0}, samples=45)]
    for round_index, offset in enumerate((0, 4, 8), 1):
        for index in list(range(offset, 13)) + list(range(offset)):
            visits.append(
                dict(
                    visit=len(visits),
                    target_id=index + 1,
                    target=tuple(points[index]),
                    **{"pass": round_index},
                    samples=15,
                )
            )
    return visits


def collect_revisits(plan, *, begin, observe, poll, clock, record):
    """Collect 45 samples/location in three visits; callbacks own UI and capture.

    observe returns (eligible 258-vector or None, monotonic capture timestamp).
    begin displays the target before the settling clock starts. Exceptions propagate
    to the runner's existing camera cleanup. Warm-up samples are discarded.
    """
    features = [[] for _ in range(13)]
    labels = [[] for _ in range(13)]
    for visit in plan:
        begin(visit)
        onset = clock()
        accepted = 0
        full_at = None
        while True:
            poll()
            now = clock()
            if full_at is not None and now - full_at >= 0.5:
                break
            if now - onset > 15:
                raise RuntimeError("Calibration visit timed out: insufficient usable eye frames")
            vector, captured_at = observe()
            if captured_at - onset > 15:
                raise RuntimeError("Calibration visit timed out: insufficient usable eye frames")
            if full_at is not None or captured_at - onset < 1.5 or vector is None:
                continue
            vector = np.asarray(vector, dtype=np.float32)
            if vector.shape != (258,) or not np.isfinite(vector).all():
                continue
            target_id = visit["target_id"]
            if target_id is not None:
                index = target_id - 1
                record(
                    dict(
                        visit=visit["visit"],
                        target_id=target_id,
                        **{"pass": visit["pass"]},
                        sample_index=len(features[index]),
                        captured_monotonic_s=captured_at,
                    )
                )
                features[index].append(vector.copy())
                labels[index].append(visit["target"])
            accepted += 1
            if accepted == visit["samples"]:
                full_at = clock()
    result = np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.float32)
    if result[0].shape != (13, 45, 258) or result[1].shape != (13, 45, 2):
        raise RuntimeError("Incomplete revisited calibration")
    return result
