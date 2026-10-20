from types import SimpleNamespace

import numpy as np
import pytest


def api():
    from experiments.gazefollower_baseline import repair

    return repair


def test_selects_nearest_training_locations_without_using_validation_features():
    labels = np.repeat(np.array([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]])[:, None], 45, axis=1)
    report = dict(
        trials=[
            dict(trial=i, target_px=p, filtered=dict(mean_error_px=e))
            for i, p, e in [(1, [15, 10], 200), (2, [20, 15], 180), (3, [90, 90], 20)]
        ]
    )
    proposal = api().propose(report, labels, (100, 100))
    assert proposal["problem_trials"] == [1, 2]
    assert proposal["training_indices"] == [0]


def test_replacement_keeps_original_and_unselected_data_intact():
    original = np.zeros((13, 45, 258), dtype=np.float32)
    replacements = {2: np.ones((45, 258), dtype=np.float32)}
    candidate = api().replace_features(original, replacements)
    assert not original.any()
    assert candidate[2].all()
    assert not candidate[0].any()
    assert not np.shares_memory(original, candidate)


def paired_rows(candidate_errors):
    return [
        dict(trial=i, target_px=[0, 0], old_px=[100, 0], candidate_px=[e, 0])
        for i, e in enumerate(candidate_errors, 1)
        for _ in range(30)
    ]


def test_accepts_improvement_on_same_frames_but_rejects_guard_regression():
    accepted = api().decide(paired_rows([70, 70, 95, 95, 95, 95]), [1, 2])
    assert accepted["accept_candidate"]
    rejected = api().decide(paired_rows([10, 10, 120, 80, 80, 80]), [1, 2])
    assert not rejected["accept_candidate"]
    assert rejected["reason"] == "guard_regression"


def test_rejects_missing_targets_and_prediction_failures_instead_of_dropping_them():
    assert not api().decide(paired_rows([50] * 5), [1, 2])["accept_candidate"]
    rows = paired_rows([50] * 6)
    for row in rows[:10]:
        row["candidate_px"] = None
    assert not api().decide(rows, [1, 2])["accept_candidate"]


def test_small_or_problem_region_regression_does_not_replace_model():
    assert not api().decide(paired_rows([99] * 6), [1, 2])["accept_candidate"]
    assert not api().decide(paired_rows([110, 110, 20, 20, 20, 20]), [1, 2])["accept_candidate"]


def execution_fixture(tmp_path, monkeypatch, candidate_x=0.5, failure=None):
    from experiments.gazefollower_baseline.run import write_new

    state = dict(clock=1000.0, collecting=False, fits=[], shown=[])
    monkeypatch.setattr(api().time, "monotonic", lambda: state["clock"])
    monkeypatch.setattr(api().time, "time", lambda: state["clock"])

    class Model:
        def __init__(self, alpha=0.1):
            self.alpha = alpha
            self.weights = np.array([1.0])

        def calibrate(self, features, labels):
            state["fits"].append(features.copy())
            self.weights = np.array([candidate_x])
            return True, 0.0, None

        def predict(self, features, raw):
            return True, [float(self.weights[0]), 0.0]

    class Controller:
        def new_session(self):
            self.feature_vectors = [[] for _ in range(13)]

        def update_position(self):
            self.x = self._current_index / 14
            self.y = 0.25

        def add_cali_feature(self, gaze, face):
            if gaze.status:
                self.feature_vectors[self._current_index - 1].append(gaze.features.copy())
                self._n_frame_added += 1
                if self._n_frame_added == 45:
                    self._current_index += 1

    def draw(target, message):
        state["collecting"] = message.startswith("YENIDEN TOPLAMA")
        if state["collecting"]:
            state["shown"].append(tuple(target))

    def observe():
        state["clock"] += 16 if failure == "timeout" else 0.1
        gaze = SimpleNamespace(
            status=True,
            features=np.full(258, 2 if state["collecting"] else 3),
            raw_gaze_coordinates=[0, 0],
        )
        return None, None, gaze, 1.0, state["clock"]

    def poll():
        if failure == "escape":
            raise InterruptedError("Escape")

    original = Model()
    features = np.ones((13, 45, 258), np.float32)
    labels = np.repeat(np.array([[i / 14, 0.25] for i in range(1, 14)])[:, None, :], 45, axis=1)
    write_new(tmp_path / "original.json", {"preserved": True})
    return dict(
        folder=tmp_path,
        original=original,
        features=features,
        labels=labels,
        proposal=dict(training_indices=[0, 12], problem_trials=[1, 2]),
        targets=[[0, 0]] * 6,
        size=(100, 100),
        controller_factory=Controller,
        observe=observe,
        draw=draw,
        poll=poll,
        wait_ready=lambda render: render(),
        usable=lambda f, g: True,
        write_new=write_new,
    ), state


@pytest.mark.parametrize("candidate_x,accept", [(0.5, True), (1.5, False)])
def test_execute_preserves_original_and_never_fits_comparison_samples(
    tmp_path, monkeypatch, candidate_x, accept
):
    args, state = execution_fixture(tmp_path, monkeypatch, candidate_x)
    chosen, decision = api().execute(**args)
    assert decision["accept_candidate"] == accept
    assert (chosen is args["original"]) == (not accept)
    assert args["original"].weights.tolist() == [1.0]
    assert np.all(args["features"] == 1)
    assert state["shown"] == [(1 / 14, 0.25), (13 / 14, 0.25)]
    assert len(state["fits"]) == 1
    fitted = state["fits"][0].reshape(13, 45, 258)
    assert np.all(fitted[[0, 12]] == 2)
    assert np.all(fitted[1:12] == 1)
    assert not np.any(fitted == 3)
    assert (tmp_path / "repair-1/decision.json").is_file()
    assert (tmp_path / "original.json").read_text() == '{\n  "preserved": true\n}\n'


@pytest.mark.parametrize("failure", ["timeout", "escape"])
def test_execute_records_failed_recollection_without_replacing_original(
    tmp_path, monkeypatch, failure
):
    import json

    args, state = execution_fixture(tmp_path, monkeypatch, failure=failure)
    if failure == "escape":
        with pytest.raises(InterruptedError):
            api().execute(**args)
    else:
        chosen, decision = api().execute(**args)
        assert chosen is args["original"]
        assert decision["reason"] == "collection_timeout"
    assert not state["fits"]
    decision = json.loads((tmp_path / "repair-1/decision.json").read_text())
    assert not decision["accept_candidate"]
    assert args["original"].weights.tolist() == [1.0]
    assert np.all(args["features"] == 1)
