import numpy as np

from experiments.comfortable_gaze.live_pair import MODELS, TARGETS, UNIGAZE_POINTS, summarize


def test_scoring_uses_training_only_and_keeps_small_motion_coverage():
    rows = []
    for phase, targets in [
        ("calibration", UNIGAZE_POINTS),
        ("comfortable", TARGETS),
        ("movement", TARGETS),
    ]:
        for x, y in targets:
            for frame in range(12):
                valid = frame != 10
                values = {name: [x, y] for name in MODELS}
                if phase == "movement":
                    values["eth_xgaze"] = [x + 0.2, y]
                rows.append(
                    dict(
                        phase=phase,
                        target=(x, y),
                        stamp=len(rows) * 100_000_000,
                        score=frame >= 8,
                        features=values if valid else None,
                        unigaze_head_rotation=[0, 0, 0],
                        unigaze_face_center=[6 if phase == "movement" else 0, 0, 600],
                    )
                )

    class IdentityStream:
        def update(self, value, timestamp):
            return value, 0

    report = summarize(rows, np.array([1512, 982]), IdentityStream)
    assert report["movement"]["joint_valid"] == 24
    assert report["movement"]["attempted"] == 32
    assert report["comfortable"]["unigaze"]["small_motion_filtered"] is None
    assert report["movement"]["unigaze"]["small_motion_filtered"]["targets"] == 8
    assert report["movement"]["unigaze"]["raw"]["mean_px"] < 5
    assert report["movement"]["eth_xgaze"]["raw"]["mean_px"] > 290
