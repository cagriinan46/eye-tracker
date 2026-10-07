"""Deterministic synthetic geometry; never load a participant holdout capture."""

import copy
import io
import json
from pathlib import Path

import numpy as np
import pytest

from experiments.gaze_representation_benchmark import analysis, calibration
from experiments.gaze_representation_benchmark import representations as rep
from experiments.raw_geometry_gaze_diagnostic.geometry import (
    EYES,
    FACE_ANCHOR_INDICES,
    reconstruct_r0,
)
from experiments.raw_geometry_gaze_diagnostic.protocol import CALIBRATION_TARGETS


def geometry(horizontal=0.6, vertical=0.1):
    """Hand-defined full-rank face and elliptical eyes in 1000x500 pixels."""
    points = {}
    for k, index in enumerate(FACE_ANCHOR_INDICES):
        points[str(index)] = {
            "x": 0.2 + (k % 3) * 0.15,
            "y": 0.2 + (k // 3) * 0.15,
            "z": (k % 5) * 0.017,
        }
    for side, cx in (("left", 650), ("right", 350)):
        eye = EYES[side]
        for k, index in enumerate(eye["contour"]):
            angle = 2 * np.pi * k / 16
            points[str(index)] = {
                "x": (cx + 40 * np.cos(angle)) / 1000,
                "y": (250 + 12 * np.sin(angle)) / 500,
                "z": -0.03,
            }
        for key, xy in (
            ("corner_a", (cx - 40, 250)),
            ("corner_b", (cx + 40, 250)),
            ("upper_lid", (cx, 238)),
            ("lower_lid", (cx, 262)),
        ):
            points[str(eye[key])] = {"x": xy[0] / 1000, "y": xy[1] / 500, "z": -0.03}
        for index, offset in zip(eye["iris_ring"], ((-2, 0), (0, -2), (2, 0), (0, 2)), strict=True):
            points[str(index)] = {
                "x": (cx - 40 + 80 * horizontal + offset[0]) / 1000,
                "y": (250 + 80 * vertical + offset[1]) / 500,
                "z": -0.03,
            }
    return {"camera_resolution": [1000, 500], "landmarks": points}


def presentations():
    output = []
    for order, target in enumerate(CALIBRATION_TARGETS, 1):
        samples = []
        for _ in range(5):
            g = geometry(target.x, (target.y - 0.5) * 0.2)
            samples.append(
                {
                    "phase": "calibration",
                    "presentation_order": order,
                    "feature_status": "usable",
                    "raw_geometry": g,
                    "camera_resolution": [1000, 500],
                    "geometry_error": None,
                    "horizontal_feature": target.x,
                    "vertical_feature": (target.y - 0.5) * 0.2,
                }
            )
        output.append(
            {
                "order": order,
                "target_id": target.name,
                "target_x": target.x,
                "target_y": target.y,
                "samples": samples,
            }
        )
    return calibration.parse_presentations(output)


def transform_3d(g, scale, rotation, translation):
    result = copy.deepcopy(g)
    for point in result["landmarks"].values():
        xyz = np.array([point["x"] * 1000, point["y"] * 500, point["z"] * 1000])
        x, y, z = scale * (rotation @ xyz) + translation
        point.update(x=x / 1000, y=y / 500, z=z / 1000)
    return result


def test_r0_exact_production_equivalence():
    g = geometry()
    result = rep.r0(g)
    assert result.binocular == reconstruct_r0(g)
    assert result.binocular.horizontal == pytest.approx(0.6)
    assert result.binocular.vertical == pytest.approx(0.1)


def test_pseudo_pixel_xyz_aspect_ratio_and_width_scaled_depth():
    g = geometry()
    g["landmarks"]["6"] = {"x": 0.3, "y": 0.4, "z": -0.2}
    np.testing.assert_array_equal(rep.points_xyz(g, (6,)), [[300, 200, -200]])


def test_calibration_face_component_medians():
    a, b, c = geometry(), geometry(), geometry()
    for g, xyz in zip((a, b, c), ((1, 9, 4), (3, 2, 8), (2, 4, 6)), strict=True):
        g["landmarks"]["6"].update(x=xyz[0] / 1000, y=xyz[1] / 500, z=xyz[2] / 1000)
    reference = rep.face_reference([a, b, c])
    np.testing.assert_array_equal(reference[0], [2, 4, 6])


def test_similarity_identity_and_known_motion_recovery():
    reference = rep.points_xyz(geometry(), FACE_ANCHOR_INDICES)
    identity = rep.fit_similarity(reference, reference)
    np.testing.assert_allclose(identity.apply(reference), reference, atol=1e-10)
    rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])
    current = 2.5 * (reference @ rotation.T) + [30, -45, 70]
    fitted = rep.fit_similarity(current, reference)
    assert fitted.scale == pytest.approx(0.4)
    np.testing.assert_allclose(fitted.rotation, rotation.T, atol=1e-12)
    np.testing.assert_allclose(fitted.apply(current), reference, atol=1e-10)


def test_similarity_never_reflects():
    reference = rep.points_xyz(geometry(), FACE_ANCHOR_INDICES)
    reflected = reference * [-1, 1, 1]
    fitted = rep.fit_similarity(reflected, reference)
    assert np.linalg.det(fitted.rotation) == pytest.approx(1)
    assert np.linalg.norm(fitted.apply(reflected) - reference) > 1


def test_r1_transformed_geometry_recovers_baseline_features():
    g = geometry()
    reference = rep.face_reference([g])
    rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.0]])
    moved = transform_3d(g, 1.7, rotation, [20, -30, 40])
    result = rep.r1(moved, reference)
    assert result.binocular.horizontal == pytest.approx(0.6)
    assert result.binocular.vertical == pytest.approx(0.1)


@pytest.mark.parametrize("index", [6, 474, 386])
def test_r1_missing_z_is_unavailable_without_fallback(index):
    g = geometry()
    reference = rep.face_reference([g])
    g["landmarks"][str(index)]["z"] = None
    assert rep.r0(g).binocular is not None
    assert rep.r1(g, reference).binocular is None


def test_r1_degenerate_anchors_and_missing_reference():
    g = geometry()
    reference = rep.face_reference([g])
    for index in FACE_ANCHOR_INDICES:
        g["landmarks"][str(index)] = {"x": 0.5, "y": 0.5, "z": 0.1}
    assert rep.r1(g, reference).binocular is None
    assert rep.r1(geometry(), None).binocular is None
    assert rep.fit_similarity(np.ones((12, 3)), reference) is None


def test_r1_svd_failure_and_nonfinite_transform(monkeypatch):
    g = geometry()
    reference = rep.face_reference([g])

    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError("synthetic failure")

    monkeypatch.setattr(np.linalg, "svd", fail)
    assert rep.r1(g, reference).binocular is None


def test_local_corner_centering_and_span():
    local = rep.local_eye(geometry(), "left")
    indices = EYES["left"]["contour"]
    np.testing.assert_allclose(local.contour[indices.index(263)], [-0.5, 0], atol=1e-12)
    np.testing.assert_allclose(local.contour[indices.index(362)], [0.5, 0], atol=1e-12)
    np.testing.assert_allclose(np.mean(local.iris, axis=0), [0.1, 0.1], atol=1e-12)


def test_reference_contour_component_medians():
    gs = [geometry() for _ in range(3)]
    index = EYES["left"]["contour"][0]
    for g, xy in zip(gs, ((660, 254), (650, 258), (654, 256)), strict=True):
        g["landmarks"][str(index)].update(x=xy[0] / 1000, y=xy[1] / 500)
    refs = rep.contour_references(gs)
    np.testing.assert_allclose(refs["left"][0], [0.05, 0.075], atol=1e-12)


def test_affine_identity_and_known_recovery():
    contour = rep.local_eye(geometry(), "left").contour
    fitted = rep.fit_affine(contour, contour)
    np.testing.assert_allclose(fitted.apply(contour), contour, atol=1e-12)
    linear = np.array([[1.2, 0.3], [-0.1, 0.8]])
    destination = contour @ linear.T + [0.04, -0.03]
    fitted = rep.fit_affine(contour, destination)
    np.testing.assert_allclose(fitted.apply(contour), destination, atol=1e-12)
    np.testing.assert_allclose(fitted.apply(np.array([[0.1, 0.1]])), [[0.19, 0.04]], atol=1e-12)


def test_r2_affine_moves_iris_with_contour_and_uses_fixed_reference():
    g = geometry()
    refs = rep.contour_references([g])
    moved = copy.deepcopy(g)
    for side in EYES:
        for index in EYES[side]["contour"] + EYES[side]["iris_ring"]:
            point = moved["landmarks"][str(index)]
            x, y = np.array([[1.2, 0.3], [-0.1, 0.8]]) @ [point["x"] * 1000, point["y"] * 500]
            point.update(x=(x + 25) / 1000, y=(y - 17) / 500)
    result = rep.r2(moved, refs)
    assert result.binocular.horizontal == pytest.approx(0.6)
    assert result.binocular.vertical == pytest.approx(0.1)


def test_affine_full_rank_and_finite_requirement():
    contour = rep.local_eye(geometry(), "left").contour
    assert rep.fit_affine(np.ones((16, 2)), contour) is None
    assert rep.fit_affine(contour, np.ones((16, 2))) is None
    broken = contour.copy()
    broken[0, 0] = np.nan
    assert rep.fit_affine(broken, contour) is None


def test_r2_missing_eye_and_zero_span_preserve_monocular():
    g = geometry()
    refs = rep.contour_references([g])
    g["landmarks"]["33"] = None
    result = rep.r2(g, refs)
    assert result.left is not None and result.right is None and result.binocular is None
    g = geometry()
    g["landmarks"]["362"] = g["landmarks"]["263"].copy()
    assert rep.r2(g, refs).binocular is None
    assert rep.r2(geometry(), None).binocular is None


def test_r2_binocular_arithmetic_mean():
    g = geometry()
    refs = rep.contour_references([g])
    for index in EYES["right"]["iris_ring"]:
        g["landmarks"][str(index)]["x"] += 0.016
        g["landmarks"][str(index)]["y"] += 0.016
    result = rep.r2(g, refs)
    assert result.left.horizontal == pytest.approx(0.6)
    assert result.right.horizontal == pytest.approx(0.8)
    assert result.binocular.horizontal == pytest.approx(0.7)
    assert result.binocular.vertical == pytest.approx(0.15)


def test_candidates_fit_calibration_only_and_reject_validation_phase():
    ps = presentations()
    fits = calibration.fit_candidates(ps)
    assert tuple(fits) == ("R0", "R1", "R2")
    for fit in fits.values():
        assert fit.mapping is not None
        np.testing.assert_allclose(fit.mapping.predict(0.5, 0), [0.5, 0.5], atol=1e-10)
    invalid = copy.deepcopy(ps[0].samples[0])
    invalid["phase"] = "validation"
    with pytest.raises(ValueError, match="calibration"):
        calibration.CalibrationPresentation(
            ps[0].target_id, ps[0].target_x, ps[0].target_y, (invalid,)
        )
    with pytest.raises(TypeError):
        calibration.fit_candidates({"calibration_presentations": [], "trials": []})


def test_missing_calibration_target_does_not_fit_partial_mapping():
    ps = list(presentations())
    ps[0] = calibration.CalibrationPresentation(ps[0].target_id, ps[0].target_x, ps[0].target_y, ())
    assert all(fit.mapping is None for fit in calibration.fit_candidates(tuple(ps)).values())


def test_no_depth_keeps_r0_r2_evaluable_but_not_r1():
    ps = presentations()
    for p in ps:
        for sample in p.samples:
            for point in sample["raw_geometry"]["landmarks"].values():
                point["z"] = None
    fits = calibration.fit_candidates(ps)
    assert fits["R0"].mapping is not None and fits["R2"].mapping is not None
    assert fits["R1"].mapping is None


def test_prefix_reader_stops_before_validation_bytes():
    ps = [
        {
            "order": k + 1,
            "target_id": p.target_id,
            "target_x": p.target_x,
            "target_y": p.target_y,
            "samples": list(p.samples),
        }
        for k, p in enumerate(presentations())
    ]
    prefix = json.dumps(
        {
            "protocol_name": "raw_geometry_gaze_diagnostic",
            "protocol_version": 1,
            "geometry_schema_version": 1,
            "session": "geometry-1",
            "session_role": "development",
            "calibration_presentations": ps,
        }
    )[:-1]
    # Invalid JSON suffix deliberately proves no full-file load or trailing parse.
    stream = io.StringIO(prefix + ', "trials": DO_NOT_READ_OR_PARSE')
    loaded = analysis.read_calibration_prefix(stream)
    assert len(loaded) == 9
    assert stream.tell() == len(prefix)


def test_holdout_path_rejected_before_open_and_symlink_rejected(tmp_path, monkeypatch):
    development = tmp_path / "raw-geometry-gaze-cagri-geometry-1.json"
    forbidden = tmp_path / "raw-geometry-gaze-cagri-geometry-2.json"
    monkeypatch.setattr(analysis, "DEVELOPMENT_CAPTURE", development)

    def fail_open(*args, **kwargs):
        pytest.fail("holdout path reached open")

    monkeypatch.setattr(Path, "open", fail_open)
    with pytest.raises(ValueError, match="development"):
        analysis.load_development_calibration(forbidden)
    development.symlink_to(forbidden)
    with pytest.raises(ValueError, match="development"):
        analysis.load_development_calibration(development)


def test_fit_api_has_no_validation_argument():
    with pytest.raises(TypeError):
        calibration.fit_candidates(presentations(), validation=[])


def test_r1_identity_eye_features_and_binocular_aggregation():
    g = geometry()
    ref = rep.face_reference([g])
    for index in EYES["right"]["iris_ring"]:
        g["landmarks"][str(index)]["x"] += 0.016
    result = rep.r1(g, ref)
    assert result.left.horizontal == pytest.approx(0.6)
    assert result.right.horizontal == pytest.approx(0.8)
    assert result.binocular.horizontal == pytest.approx(0.7)
    assert result.binocular.vertical == pytest.approx(0.1)


def test_r2_identity_and_reference_lid_degeneracy():
    g = geometry()
    refs = rep.contour_references([g])
    result = rep.r2(g, refs)
    assert result.binocular.horizontal == pytest.approx(0.6)
    assert result.binocular.vertical == pytest.approx(0.1)
    contour = EYES["left"]["contour"]
    refs["left"][contour.index(386)] = refs["left"][contour.index(374)]
    assert rep.r2(g, refs).binocular is None


def test_r1_planar_anchors_are_not_a_2d_fallback():
    g = geometry()
    ref = rep.face_reference([g])
    for index in FACE_ANCHOR_INDICES:
        g["landmarks"][str(index)]["z"] = 0
    assert rep.r1(g, ref).binocular is None


def test_nonfinite_input_and_transform_are_unavailable(monkeypatch):
    g = geometry()
    ref = rep.face_reference([g])
    g["landmarks"]["6"]["z"] = float("inf")
    assert rep.r1(g, ref).binocular is None
    assert rep.face_reference([g]) is None
    monkeypatch.setattr(
        rep, "fit_similarity", lambda *args: rep.Similarity(float("nan"), np.eye(3), np.zeros(3))
    )
    assert rep.r1(geometry(), ref).binocular is None


def test_affine_solver_failure_is_unavailable(monkeypatch):
    g = geometry()
    refs = rep.contour_references([g])

    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError("synthetic failure")

    monkeypatch.setattr(np.linalg, "lstsq", fail)
    assert rep.r2(g, refs).binocular is None


def test_per_presentation_mapping_uses_robust_medians():
    ps = presentations()
    for p in ps:
        # One outlier among five must not pull the presentation median.
        p.samples[0]["raw_geometry"] = geometry(9, 7)
    fits = calibration.fit_candidates(ps)
    for fit in fits.values():
        assert fit.mapping is not None
        np.testing.assert_allclose(fit.mapping.predict(0.5, 0), [0.5, 0.5], atol=1e-10)


def test_mutated_phase_cannot_bypass_calibration_boundary():
    ps = presentations()
    ps[0].samples[0]["phase"] = "validation"
    with pytest.raises(ValueError, match="calibration"):
        calibration.fit_candidates(ps)


def test_prefix_reader_handles_unselected_nested_metadata_and_escapes():
    ps = [
        {
            "order": k + 1,
            "target_id": p.target_id,
            "target_x": p.target_x,
            "target_y": p.target_y,
            "samples": list(p.samples),
        }
        for k, p in enumerate(presentations())
    ]
    prefix = json.dumps(
        {
            "unselected": {"array": [True, None, {"text": '\\" }] ['}]},
            "protocol_name": "raw_geometry_gaze_diagnostic",
            "protocol_version": 1,
            "geometry_schema_version": 1,
            "session": "geometry-1",
            "session_role": "development",
            "calibration_presentations": ps,
        }
    )[:-1]
    stream = io.StringIO(prefix + ', "trials": DO_NOT_READ')
    assert len(analysis.read_calibration_prefix(stream)) == 9
    assert stream.tell() == len(prefix)


def test_wrong_identity_and_validation_first_rejected_without_array_read():
    stream = io.StringIO('{"session":"geometry-2","calibration_presentations": NEVER_READ')
    with pytest.raises(ValueError, match="development"):
        analysis.read_calibration_prefix(stream)
    assert stream.read() == " NEVER_READ"
    stream = io.StringIO('{"trials": NEVER_READ')
    with pytest.raises(ValueError, match="validation"):
        analysis.read_calibration_prefix(stream)
    assert stream.read() == " NEVER_READ"


def test_calibration_parser_rejects_wrong_order_and_baseline_mismatch():
    data = [
        {
            "order": k + 1,
            "target_id": p.target_id,
            "target_x": p.target_x,
            "target_y": p.target_y,
            "samples": list(p.samples),
        }
        for k, p in enumerate(presentations())
    ]
    data[0]["order"] = 2
    with pytest.raises(ValueError, match="order"):
        calibration.parse_presentations(data)
    data[0]["order"] = 1
    data[0]["samples"][0]["horizontal_feature"] = 999
    with pytest.raises(ValueError, match="reconstruct R0"):
        calibration.parse_presentations(data)


def test_sanity_summary_only_reports_calibration_coverage_and_conditioning():
    summary = analysis.calibration_sanity(presentations())
    assert summary["fields_consumed"] == ["identity", "calibration_presentations"]
    assert tuple(summary["candidates"]) == ("R0", "R1", "R2")
    for candidate in summary["candidates"].values():
        assert set(candidate) == {
            "mapping_evaluable",
            "unavailable_reason",
            "usable_calibration_samples_per_presentation",
            "conditioning_range",
        }
        assert candidate["usable_calibration_samples_per_presentation"] == [5] * 9


def test_holdout_and_alias_rejected_before_filesystem_resolution(tmp_path, monkeypatch):
    development = tmp_path / "raw-geometry-gaze-cagri-geometry-1.json"
    monkeypatch.setattr(analysis, "DEVELOPMENT_CAPTURE", development)

    def fail_resolve(*args, **kwargs):
        pytest.fail("unapproved path reached filesystem resolution")

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    for rejected in (tmp_path / "raw-geometry-gaze-cagri-geometry-2.json", tmp_path / "alias.json"):
        with pytest.raises(ValueError, match="development"):
            analysis.load_development_calibration(rejected)


def test_loader_never_prefetches_or_decodes_trailing_validation(tmp_path, monkeypatch):
    data = [
        {
            "order": k + 1,
            "target_id": p.target_id,
            "target_x": p.target_x,
            "target_y": p.target_y,
            "samples": list(p.samples),
        }
        for k, p in enumerate(presentations())
    ]
    prefix = json.dumps(
        {
            "protocol_name": "raw_geometry_gaze_diagnostic",
            "protocol_version": 1,
            "geometry_schema_version": 1,
            "session": "geometry-1",
            "session_role": "development",
            "calibration_presentations": data,
        }
    )[:-1].encode()
    development = tmp_path / "raw-geometry-gaze-cagri-geometry-1.json"
    development.write_bytes(prefix + b', "trials":\xffDO_NOT_READ')
    monkeypatch.setattr(analysis, "DEVELOPMENT_CAPTURE", development)
    actual_open = Path.open
    positions = []

    class TrackedStream:
        def __init__(self, raw):
            self.raw = raw

        def __enter__(self):
            return self

        def __exit__(self, *args):
            positions.append(self.raw.tell())
            self.raw.close()

        def read(self, n):
            return self.raw.read(n)

    def tracked_open(path, *args, **kwargs):
        return TrackedStream(actual_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", tracked_open)
    assert len(analysis.load_development_calibration()) == 9
    assert positions == [len(prefix)]


def test_r2_finite_extreme_iris_overflow_is_unavailable_per_eye(monkeypatch):
    g = geometry()
    refs = rep.contour_references([g])
    original_fit = rep.fit_affine

    def extreme_fit(current, reference):
        if reference is refs["left"]:
            return rep.Affine(np.array([[1, 0], [0, 1], [1e308, 0]]))
        return original_fit(current, reference)

    monkeypatch.setattr(rep, "fit_affine", extreme_fit)
    result = rep.r2(g, refs)
    assert result.left is None and result.right is not None
    assert result.binocular is None


def test_candidate_specific_scales_receive_independent_maps():
    ps = presentations()
    for p in ps:
        angle = (p.target_x - 0.5) * 0.7 + (p.target_y - 0.5) * 0.3
        c, s = np.cos(angle), np.sin(angle)
        rotation = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        for sample in p.samples:
            sample["raw_geometry"] = transform_3d(sample["raw_geometry"], 1, rotation, [0, 0, 0])
    fits = calibration.fit_candidates(ps)
    assert fits["R0"].mapping is not None and fits["R1"].mapping is not None
    assert abs(fits["R0"].mapping.x_slope - fits["R1"].mapping.x_slope) > 0.001
    # Independent OLS oracle on each candidate's own presentation medians.
    for fit in fits.values():
        for axis in ("x", "y"):
            feature = "horizontal_feature" if axis == "x" else "vertical_feature"
            fs = np.array([getattr(m, feature) for m in fit.presentation_medians])
            targets = np.array([getattr(m, f"target_{axis}") for m in fit.presentation_medians])
            slope = np.dot(fs - fs.mean(), targets - targets.mean()) / np.dot(
                fs - fs.mean(), fs - fs.mean()
            )
            assert getattr(fit.mapping, f"{axis}_slope") == pytest.approx(slope)
            assert getattr(fit.mapping, f"{axis}_intercept") == pytest.approx(
                targets.mean() - slope * fs.mean()
            )


def test_r2_nonaffine_contour_uses_fixed_reference_extrema_and_basis():
    g = geometry()
    refs = rep.contour_references([g])
    # Move a single upper contour point; this has no exact affine explanation.
    g["landmarks"]["249"]["x"] += 0.04
    g["landmarks"]["249"]["y"] -= 0.07
    contour_ids, ring_ids = EYES["left"]["contour"], EYES["left"]["iris_ring"]

    def local_xy(index):
        p = g["landmarks"][str(index)]
        return [(p["x"] * 1000 - 650) / 80, (p["y"] * 500 - 250) / 80]

    current = np.array([local_xy(i) for i in contour_ids])
    design = np.column_stack((current, np.ones(16)))
    coefficients = np.linalg.lstsq(design, refs["left"], rcond=None)[0]
    iris = np.array([local_xy(i) for i in ring_ids])
    center = (np.column_stack((iris, np.ones(4))) @ coefficients).mean(axis=0)
    # Fixed reference has extrema [-.5,+.5], midpoint [0,0], span 1, basis [0,1].
    expected_h, expected_v = center[0] + 0.5, center[1]
    result = rep.r2(g, refs)
    assert result.left.horizontal == pytest.approx(expected_h)
    assert result.left.vertical == pytest.approx(expected_v)
    transformed_contour = design @ coefficients
    incorrect_current_h = (center[0] - transformed_contour[:, 0].min()) / np.ptp(
        transformed_contour[:, 0]
    )
    assert abs(expected_h - incorrect_current_h) > 0.001
