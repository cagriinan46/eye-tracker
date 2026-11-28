"""Head-pointer candidate signals computed from one Face Landmarker result (Issue #156).

Every candidate returns a raw 2D value per frame; a per-axis calibration line later
maps it to the screen, so scale and sign do not matter here.
"""

from math import atan2, degrees, isfinite, sqrt

CANDIDATES = ("NOSE", "ANGLES", "RAY")
NOSE_TIP = 1  # MediaPipe Face Mesh nose-tip landmark
MIN_FORWARD_Z = 0.2  # |z| of the unit forward axis; rejects near-parallel rays


def _finite(*values: float) -> bool:
    return all(isinstance(v, (int, float)) and isfinite(v) for v in values)


def nose_signal(landmarks) -> tuple[float, float] | None:
    """Image-normalized nose-tip position; moves with head translation and rotation."""
    if landmarks is None or len(landmarks) <= NOSE_TIP:
        return None
    point = landmarks[NOSE_TIP]
    x, y = point[0], point[1]
    return (float(x), float(y)) if _finite(x, y) else None


def _rotation(matrix) -> list[list[float]] | None:
    try:
        r = [[float(matrix[row][column]) for column in range(4)] for row in range(3)]
    except (TypeError, IndexError, ValueError):
        return None
    return r if all(_finite(*row) for row in r) else None


def angle_signal(matrix) -> tuple[float, float] | None:
    """(yaw, pitch) in degrees with the Issue #77/#84 Euler convention."""
    r = _rotation(matrix)
    if r is None:
        return None
    pitch = degrees(atan2(r[2][1], r[2][2]))
    yaw = degrees(atan2(-r[2][0], sqrt(r[0][0] ** 2 + r[1][0] ** 2)))
    return (yaw, pitch)


def ray_signal(matrix) -> tuple[float, float] | None:
    """Where the head's forward (+z, nose) axis meets the camera plane z = 0.

    The facial transformation matrix maps the canonical face (cm) into camera space,
    so its third rotation column is the face's forward axis and its fourth column the
    head position. Combines head position and rotation, unlike ANGLES or NOSE.
    """
    r = _rotation(matrix)
    if r is None:
        return None
    forward = (r[0][2], r[1][2], r[2][2])
    origin = (r[0][3], r[1][3], r[2][3])
    # Robust to the z sign convention: the axis must point toward the plane.
    if abs(forward[2]) < MIN_FORWARD_Z or origin[2] * forward[2] >= 0:
        return None
    s = -origin[2] / forward[2]
    return (origin[0] + s * forward[0], origin[1] + s * forward[1])


def candidate_signals(landmarks, matrix) -> dict[str, tuple[float, float] | None]:
    return {
        "NOSE": nose_signal(landmarks),
        "ANGLES": angle_signal(matrix),
        "RAY": ray_signal(matrix),
    }
