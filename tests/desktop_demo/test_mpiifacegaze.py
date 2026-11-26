import numpy as np

from experiments.desktop_demo.protocol import Session
from experiments.desktop_demo.runtime import DesktopAPI


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
