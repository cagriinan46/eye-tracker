"""2D non-eye face alignment and eye geometry in image/face coordinates."""

from math import atan2, cos, hypot, isfinite, sin, sqrt
from statistics import median

from experiments.eye_geometry_decomposition_study.geometry import geometry_metrics

# Installed MediaPipe 0.10.35 FaceLandmarksConnections: six NOSE path points
# and four bilateral FACE_OVAL path points. No eye, iris, lid, brow, or lip points.
FACE_ANCHOR_INDICES = (6, 197, 195, 5, 4, 1, 127, 234, 454, 356)
FACE_REFERENCE_METHOD = "calibration_median_pixel_anchors_to_2d_similarity_v1"
EYE_POINTS = ("corner_a", "corner_b", "iris_center", "upper_lid", "lower_lid")


def _pair(point: object) -> tuple[float, float]:
    if (
        not isinstance(point, (list, tuple))
        or len(point) != 2
        or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in point
        )
    ):
        raise ValueError("face reference point must be a finite x/y pair")
    return float(point[0]), float(point[1])


def anchor_record(observation) -> list[list[float]]:
    """Take only the fixed non-eye points from an already extracted observation."""
    landmarks = observation.landmarks
    if landmarks is None or len(landmarks) <= max(FACE_ANCHOR_INDICES):
        raise ValueError("required non-eye face landmarks are unavailable")
    return [[landmarks[index].x, landmarks[index].y] for index in FACE_ANCHOR_INDICES]


def calibration_template(rows: list[dict], width: int, height: int) -> list[list[float]]:
    """One median pixel point per index, using only natural calibration rows."""
    calibration = [r for r in rows if r["phase"] == "calibration" and r["status"] == "usable"]
    if not calibration:
        raise ValueError("usable calibration anchors are required")
    if any(len(r["face_anchors"]) != len(FACE_ANCHOR_INDICES) for r in calibration):
        raise ValueError("incomplete calibration anchor set")
    return [
        [
            median(_pair(row["face_anchors"][index])[0] * width for row in calibration),
            median(_pair(row["face_anchors"][index])[1] * height for row in calibration),
        ]
        for index in range(len(FACE_ANCHOR_INDICES))
    ]


def fit_similarity(
    anchors: list[list[float]], template_px: list[list[float]], width: int, height: int
) -> dict[str, float]:
    """Least-squares orientation-preserving current-pixels -> template-pixels fit."""
    if width <= 0 or height <= 0 or len(anchors) != len(template_px) or len(anchors) < 3:
        raise ValueError("similarity fit requires matching nondegenerate anchor sets")
    source = [(x * width, y * height) for point in anchors for x, y in [_pair(point)]]
    target = [_pair(point) for point in template_px]
    n = len(source)
    sx, sy = sum(x for x, _ in source) / n, sum(y for _, y in source) / n
    tx, ty = sum(x for x, _ in target) / n, sum(y for _, y in target) / n
    centered = [(x - sx, y - sy) for x, y in source]
    desired = [(x - tx, y - ty) for x, y in target]
    a = sum(x * u + y * v for (x, y), (u, v) in zip(centered, desired, strict=True))
    b = sum(x * v - y * u for (x, y), (u, v) in zip(centered, desired, strict=True))
    denominator = sum(x * x + y * y for x, y in centered)
    if denominator <= 1e-9 or hypot(a, b) <= 1e-9:
        raise ValueError("degenerate non-eye face alignment")
    scale = hypot(a, b) / denominator
    angle = atan2(b, a)
    c, s = cos(angle), sin(angle)
    shift_x = tx - scale * (c * sx - s * sy)
    shift_y = ty - scale * (s * sx + c * sy)
    error = sum(
        (scale * (c * x - s * y) + shift_x - u) ** 2 + (scale * (s * x + c * y) + shift_y - v) ** 2
        for (x, y), (u, v) in zip(source, target, strict=True)
    )
    return {
        "scale": scale,
        "rotation_rad": angle,
        "translation_x_px": shift_x,
        "translation_y_px": shift_y,
        "rms_px": sqrt(error / n),
    }


def apply_similarity(point: list[float], transform: dict, width: int, height: int) -> list[float]:
    """Return normalized image coordinates after a pixel-space similarity fit."""
    x, y = _pair(point)
    x, y = x * width, y * height
    scale = transform["scale"]
    c, s = cos(transform["rotation_rad"]), sin(transform["rotation_rad"])
    return [
        (scale * (c * x - s * y) + transform["translation_x_px"]) / width,
        (scale * (s * x + c * y) + transform["translation_y_px"]) / height,
    ]


def eye_summary(points: dict, width: int, height: int) -> dict:
    """Five named points plus the exact local-axis geometry, in one coordinate frame."""
    p = {name: _pair(points[name]) for name in EYE_POINTS}
    a = (p["corner_a"][0] * width, p["corner_a"][1] * height)
    b = (p["corner_b"][0] * width, p["corner_b"][1] * height)
    i = (p["iris_center"][0] * width, p["iris_center"][1] * height)
    u = (p["upper_lid"][0] * width, p["upper_lid"][1] * height)
    lower = (p["lower_lid"][0] * width, p["lower_lid"][1] * height)
    dx, dy = b[0] - a[0], b[1] - a[1]
    span = hypot(dx, dy)
    if span <= 1e-6:
        raise ValueError("degenerate eye corner span")
    normal = [-dy / span, dx / span]
    lid_projection = (lower[0] - u[0]) * normal[0] + (lower[1] - u[1]) * normal[1]
    if lid_projection < 0:
        normal = [-normal[0], -normal[1]]
        lid_projection = -lid_projection
    if lid_projection <= 1e-6:
        raise ValueError("degenerate lid projection")
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    lid_mid = ((u[0] + lower[0]) / 2, (u[1] + lower[1]) / 2)
    vertical = ((i[0] - mid[0]) * normal[0] + (i[1] - mid[1]) * normal[1]) / span
    return {
        **{name: list(p[name]) for name in EYE_POINTS},
        "corner_midpoint": [mid[0] / width, mid[1] / height],
        "corner_span_px": span,
        "corner_angle_rad": atan2(dy, dx),
        "lid_midpoint": [lid_mid[0] / width, lid_mid[1] / height],
        "eye_opening": hypot(lower[0] - u[0], lower[1] - u[1]) / span,
        "vertical": vertical,
        "iris_local_parallel": ((i[0] - mid[0]) * dx + (i[1] - mid[1]) * dy) / (span * span),
        "iris_local_vertical": vertical,
    }


def enrich_usable_rows(
    rows: list[dict], template_px: list[list[float]], width: int, height: int
) -> None:
    """Attach transform and matched eye records to every usable saved sample."""
    for row in rows:
        if row["status"] != "usable":
            continue
        transform = fit_similarity(row["face_anchors"], template_px, width, height)
        image = {}
        face = {}
        for side in ("left", "right"):
            geometry = row["geometry"][side]
            image[side] = eye_summary(geometry, width, height)
            face[side] = eye_summary(
                {
                    name: apply_similarity(geometry[name], transform, width, height)
                    for name in EYE_POINTS
                },
                width,
                height,
            )
            original = geometry_metrics(geometry, width, height)
            if abs(image[side]["vertical"] - original["vertical"]) > 1e-10:
                raise ValueError("image eye geometry disagrees with production feature")
            if abs(face[side]["vertical"] - original["vertical"]) > 1e-10:
                raise ValueError("face alignment changed similarity-invariant eye feature")
        row["face_alignment"] = transform
        row["image_eye_geometry"] = image
        row["face_normalized_geometry"] = face
