"""Numerical camera/eye diagnostics only. No frame/landmark serialization."""

import numpy as np

# Names follow MGazeNet input slots, not anatomical left/right.
EYES = {
    "left": (33, 133, 159, 145, (469, 470, 471, 472)),
    "right": (362, 263, 386, 374, (474, 475, 476, 477)),
}


def eye_signal(points, indices, rectangle=None):
    if points is None:
        return None
    p = np.asarray(points, float)
    a, b, u, lower, ring = indices
    if p.ndim != 2 or p.shape[1] < 2 or len(p) <= max(a, b, u, lower, *ring):
        return None
    p = p[:, :2]
    if not np.isfinite(p[[a, b, u, lower, *ring]]).all():
        return None
    axis = p[b] - p[a]
    width = np.linalg.norm(axis)
    if width < 1e-6:
        return None
    horizontal = axis / width
    vertical = np.array([-horizontal[1], horizontal[0]])
    if np.dot(p[lower] - p[u], vertical) < 0:
        vertical = -vertical
    iris = p[list(ring)].mean(0)
    midpoint = (p[a] + p[b]) / 2
    delta = iris - midpoint
    result = dict(
        iris_u=float(np.dot(delta, horizontal) / width),
        iris_v=float(np.dot(delta, vertical) / width),
        lid_gap_ratio=float(np.dot(p[lower] - p[u], vertical) / width),
        eye_width_px=float(width),
        iris_center_px=iris.tolist(),
    )
    if rectangle is not None:
        rect = np.asarray(rectangle, float)
        if rect.shape == (4,) and np.isfinite(rect).all() and min(rect[2:]) > 0:
            x, y, w, h = rect
            xs = p[list(ring), 0]
            ys = p[list(ring), 1]
            margin = float(
                min(np.min(xs - x), np.min(x + w - xs), np.min(ys - y), np.min(y + h - ys))
            )
            result.update(min_iris_crop_margin_px=margin, iris_ring_inside_crop=bool(margin >= 0))
    return result


def image_signal(bgr):
    if bgr.ndim != 3 or bgr.shape[2] != 3 or min(bgr.shape[:2]) < 2:
        return None
    gray = bgr.astype(float).mean(2)
    gradient = np.r_[np.diff(gray, axis=0).ravel(), np.diff(gray, axis=1).ravel()]
    return dict(
        mean_intensity=float(gray.mean()),
        intensity_std=float(gray.std()),
        bright_fraction=float(np.mean(gray >= 245)),
        gradient_rms=float(np.sqrt(np.mean(gradient**2))),
    )
