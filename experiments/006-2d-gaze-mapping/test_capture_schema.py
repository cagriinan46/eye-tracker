"""Regression check for the experiment's derived numerical CSV output."""

import csv
import importlib.util
from pathlib import Path


def test_face_present_sample_writes_all_derived_fields(tmp_path, monkeypatch):
    script_dir = Path(__file__).parent
    monkeypatch.syspath_prepend(str(script_dir))
    spec = importlib.util.spec_from_file_location(
        "gaze_mapping_experiment", script_dir / "gaze_mapping_experiment.py"
    )
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)

    row = {
        "timestamp_s": 1.5,
        "phase": "validation",
        "presentation_index": 10,
        "target_id": "V-1",
        "trial_number": 1,
        "target_x": 0.35,
        "target_y": 0.35,
        "face_detected": 1,
        "geometry_valid": 1,
        "horizontal_feature": 0.52,
        "vertical_feature": -0.04,
        "left_horizontal": 0.51,
        "right_horizontal": 0.53,
        "left_vertical_local_axis": -0.03,
        "right_vertical_local_axis": -0.05,
        "eyeBlinkLeft": 0.1,
        "eyeBlinkRight": 0.2,
        "binocular_blink": 0.15,
        "binocular_eye_opening": 0.09,
        "head_center_y": 0.5,
        "camera_width": 1920,
        "camera_height": 1080,
        "window_width": 1200,
        "window_height": 700,
    }
    output = tmp_path / "human-sample.csv"

    experiment.write_rows(output, [row])

    with output.open(newline="", encoding="utf-8") as saved:
        reader = csv.DictReader(saved)
        assert reader.fieldnames == list(row)
        assert list(reader) == [{key: str(value) for key, value in row.items()}]
