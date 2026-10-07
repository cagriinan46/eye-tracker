"""Single frozen formulation per family. No target, timing or mapping inputs."""

from dataclasses import dataclass
from math import isfinite

import numpy as np

from experiments.raw_geometry_gaze_diagnostic.geometry import EYES, FACE_ANCHOR_INDICES
from eye_tracker.vision.contracts import NormalizedPoint
from eye_tracker.vision.eye_features import (
    EyeFeatures,
    EyeGeometry,
    extract_binocular_features,
    extract_eye_features,
)

REPRESENTATIONS = ("R0", "R1", "R2")
EYE_INDICES = tuple(sorted({i for e in EYES.values() for i in e["contour"] + e["iris_ring"]}))
_MIN_SPAN = 1e-6  # Production pixel guard; local references use unit-coordinate geometry.


@dataclass(frozen=True)
class Features:
    left: EyeFeatures | None
    right: EyeFeatures | None
    binocular: EyeFeatures | None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class Similarity:
    scale: float
    rotation: np.ndarray
    translation: np.ndarray

    def apply(self, points):
        return self.scale * (points @ self.rotation.T) + self.translation


@dataclass(frozen=True)
class Affine:
    coefficients: np.ndarray  # [x,y,1] @ coefficients; shape (3,2).

    def apply(self, points):
        return np.column_stack((points, np.ones(len(points)))) @ self.coefficients


@dataclass(frozen=True)
class LocalEye:
    contour: np.ndarray
    iris: np.ndarray


def _dimensions(record):
    width, height = record["camera_resolution"]
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (width, height)):
        raise ValueError("positive integer frame dimensions required")
    return width, height


def _points(record, indices, axes):
    points = record["landmarks"]
    values = [[points[str(index)][axis] for axis in axes] for index in indices]
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
        for row in values
        for v in row
    ):
        raise ValueError("missing/nonfinite required geometry")
    return np.array(values, dtype=np.float64)


def points_xyz(record, indices):
    """Pseudo-pixels: X=x*width, Y=y*height, Z=z*width; not metric 3D."""
    width, height = _dimensions(record)
    result = _points(record, indices, "xyz") * [width, height, width]
    if not np.isfinite(result).all():
        raise ValueError("nonfinite pseudo-pixels")
    return result


def _eye(points, side):
    eye = EYES[side]

    def point(index):
        return NormalizedPoint(*points[index])

    return EyeGeometry(
        contour=tuple(point(i) for i in eye["contour"]),
        iris_ring=tuple(point(i) for i in eye["iris_ring"]),
        corner_a=point(eye["corner_a"]),
        corner_b=point(eye["corner_b"]),
        upper_lid=point(eye["upper_lid"]),
        lower_lid=point(eye["lower_lid"]),
    )


def _features(eyes, width=1, height=1):
    monocular = []
    for eye in eyes:
        try:
            feature = extract_eye_features(eye, width, height) if eye else None
            if feature is not None and not all(
                isfinite(v) for v in (feature.horizontal, feature.vertical)
            ):
                feature = None
        except (ValueError, OverflowError, FloatingPointError):
            feature = None
        monocular.append(feature)
    valid_eyes = [eye if feature else None for eye, feature in zip(eyes, monocular, strict=True)]
    try:
        binocular = extract_binocular_features(*valid_eyes, width, height)
        if binocular is not None and not all(
            isfinite(v) for v in (binocular.horizontal, binocular.vertical)
        ):
            binocular = None
    except (ValueError, OverflowError, FloatingPointError):
        binocular = None
    return Features(*monocular, binocular, None if binocular else "unavailable eye geometry")


def r0(record):
    """Production equations/guards/aggregation on original normalized XY."""
    try:
        width, height = _dimensions(record)
        eyes = []
        for side, eye in EYES.items():
            try:
                indices = eye["contour"] + eye["iris_ring"]
                values = _points(record, indices, "xy")
                eyes.append(_eye(dict(zip(indices, values, strict=True)), side))
            except (KeyError, TypeError, ValueError):
                eyes.append(None)
        return _features(eyes, width, height)
    except (KeyError, TypeError, ValueError, OverflowError):
        return Features(None, None, None, "missing/nonfinite R0 geometry")


def face_reference(records):
    """Per-anchor component medians over complete usable calibration frames."""
    arrays = []
    for record in records:
        try:
            points_xyz(record, EYE_INDICES)  # R1 requires all production eye XYZ too.
            anchors = points_xyz(record, FACE_ANCHOR_INDICES)
            if r0(record).binocular is not None:
                arrays.append(anchors)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return np.median(arrays, axis=0) if arrays else None


def _rank(matrix):
    """Fixed float64 SVD numerical rank; no fitted conditioning threshold."""
    return np.linalg.matrix_rank(matrix)


def fit_similarity(current, reference):
    """Proper least-squares 3D similarity current -> reference (column vectors)."""
    try:
        current, reference = np.asarray(current, dtype=float), np.asarray(reference, dtype=float)
        if current.shape != (12, 3) or reference.shape != (12, 3):
            return None
        if not np.isfinite(current).all() or not np.isfinite(reference).all():
            return None
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            mx, my = current.mean(axis=0), reference.mean(axis=0)
            x, y = current - mx, reference - my
            covariance = y.T @ x / len(x)
            if any(_rank(a) != 3 for a in (x, y, covariance)):
                return None
            u, singular, vt = np.linalg.svd(covariance, full_matrices=False)
            d = np.ones(3)
            if np.linalg.det(u @ vt) < 0:
                d[-1] = -1
            rotation = (u * d) @ vt
            variance = np.sum(x * x) / len(x)
            scale = float(np.dot(singular, d) / variance)
            translation = my - scale * (rotation @ mx)
            if (
                scale <= 0
                or not np.isfinite(scale)
                or not np.isfinite(rotation).all()
                or not np.isfinite(translation).all()
                or np.linalg.det(rotation) <= 0
            ):
                return None
            return Similarity(scale, rotation, translation)
    except (TypeError, ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError):
        return None


def r1(record, reference):
    try:
        anchors = points_xyz(record, FACE_ANCHOR_INDICES)
        eyes = points_xyz(record, EYE_INDICES)
        transform = fit_similarity(anchors, reference)
        if transform is None:
            return Features(None, None, None, "unavailable full-rank 3D similarity/reference")
        with np.errstate(over="raise", invalid="raise"):
            aligned = transform.apply(eyes)[:, :2]
        points = dict(zip(EYE_INDICES, aligned, strict=True))
        return _features([_eye(points, side) for side in EYES])
    except (KeyError, TypeError, ValueError, FloatingPointError, OverflowError):
        return Features(None, None, None, "missing/nonfinite required R1 XYZ")


def local_eye(record, side):
    """Current (pixel XY - corner midpoint) / pixel corner span."""
    eye = EYES[side]
    indices = eye["contour"] + eye["iris_ring"]
    width, height = _dimensions(record)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        pixel = _points(record, indices, "xy") * [width, height]
        a, b = (pixel[indices.index(eye[key])] for key in ("corner_a", "corner_b"))
        span = np.linalg.norm(b - a)
        if not np.isfinite(span) or span <= _MIN_SPAN:
            raise ValueError("degenerate corner span")
        local = (pixel - (a + b) / 2) / span
        if not np.isfinite(local).all():
            raise ValueError("nonfinite local eye")
        return LocalEye(local[:16], local[16:])


def contour_references(records):
    records = tuple(records)
    references = {}
    for side in EYES:
        contours = []
        for record in records:
            try:
                if r0(record).binocular is not None:
                    contours.append(local_eye(record, side).contour)
            except (KeyError, TypeError, ValueError, FloatingPointError, OverflowError):
                continue
        references[side] = np.median(contours, axis=0) if contours else None
    return references


def fit_affine(current, reference):
    """One unweighted OLS affine using all 16 correspondences, rcond=None."""
    try:
        current, reference = np.asarray(current, dtype=float), np.asarray(reference, dtype=float)
        if current.shape != (16, 2) or reference.shape != (16, 2):
            return None
        if not np.isfinite(current).all() or not np.isfinite(reference).all():
            return None
        design = np.column_stack((current, np.ones(16)))
        coefficients, _, rank, _ = np.linalg.lstsq(design, reference, rcond=None)
        if rank != 3 or not np.isfinite(coefficients).all() or _rank(coefficients[:2]) != 2:
            return None
        return Affine(coefficients)
    except (TypeError, ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError):
        return None


def r2(record, references):
    eyes = []
    for side, eye in EYES.items():
        try:
            local = local_eye(record, side)
            reference = references[side]
            transform = fit_affine(local.contour, reference)
            if transform is None:
                eyes.append(None)
                continue
            with np.errstate(over="raise", invalid="raise"):
                iris = transform.apply(local.iris)
            points = dict(zip(eye["contour"], reference, strict=True))
            points.update(zip(eye["iris_ring"], iris, strict=True))
            eyes.append(_eye(points, side))
        except (KeyError, TypeError, ValueError, FloatingPointError, OverflowError):
            eyes.append(None)
    return _features(eyes)
