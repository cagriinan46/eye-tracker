from types import SimpleNamespace

import numpy as np
import pytest

from experiments.desktop_demo.protocol import Session
from experiments.desktop_demo.runtime import DesktopAPI
from experiments.unigaze.desktop_worker import MPIIFaceEngine
from experiments.unigaze.mapping import Ridge


def test_desktop_defaults_to_mpiifacegaze(tmp_path):
    api = DesktopAPI(output=tmp_path)
    assert api.snapshot()["model_name"] == "mpiifacegaze"
    assert DesktopAPI(output=tmp_path, model_name="unigaze").snapshot()["model_name"] == "unigaze"


def test_mpiifacegaze_uses_existing_timed_desktop_protocol():
    session = Session("mpiifacegaze", "web")
    session.phase = "calibration"
    session.onset = 0
    for stamp in np.linspace(1.5, 4, 20):
        session.sample(stamp, [0.1, 0.2], None)
    assert session.index == 0
    session.sample(7.5, None, None)
    assert session.index == 1
    assert session.training[0].shape == (20, 2)
    assert len(session.trial_order) == 12


@pytest.mark.parametrize("variant,sample_count", [("quick", 10), ("standard", 20)])
def test_calibration_session_arrays_fit_in_actual_mpiiface_worker(variant, sample_count):
    session = Session("mpiifacegaze")
    session.start_calibration([1512, 982, 0, 0, 2], variant)
    for index in range(13):
        onset = index * 8
        session.ack(session.token, onset)
        x, y = session.point
        for stamp in np.linspace(1.5, 4.0, sample_count):
            session.sample(onset + stamp, [x, y], None)
        if variant == "standard":
            session.sample(onset + 7.5, None, None)
    assert session.phase == "fitting"
    worker = MPIIFaceEngine.__new__(MPIIFaceEngine)
    worker.mapping = Ridge(standardize=True)
    worker.smoothing = SimpleNamespace(reset=lambda: None)
    features, labels = session.calibration_arrays()
    assert worker.fit(features.tolist(), labels.tolist()) < 0.01
    assert np.allclose(worker.mapping.predict((0.5, 0.5)), (0.5, 0.5), atol=0.01)
    invalid = labels.copy()
    invalid[0] = invalid[-1]
    with pytest.raises(ValueError, match="eşit dağılmalı"):
        worker.fit(features, invalid)
