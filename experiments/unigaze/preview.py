"""Display-only eye crops from the same raw frame as the measured landmarks."""

import base64

import numpy as np


def jpeg_url(cv2, image):
    ok, data = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii") if ok else None


def eye_view(cv2, frame, eyes):
    tiles = []
    for points in eyes or []:
        p = np.asarray(points, float)
        if p.shape != (8, 2) or not np.isfinite(p).all():
            return None
        lo = np.floor(p.min(axis=0) - [12, 12]).astype(int)
        hi = np.ceil(p.max(axis=0) + [12, 12]).astype(int)
        x0, y0 = np.maximum(lo, 0)
        x1, y1 = np.minimum(hi, [frame.shape[1], frame.shape[0]])
        if x1 <= x0 or y1 <= y0:
            return None
        tile = cv2.resize(frame[y0:y1, x0:x1], (180, 90))
        dots = np.rint((p - [x0, y0]) * [180 / (x1 - x0), 90 / (y1 - y0)]).astype(int)
        for dot in dots:
            cv2.circle(tile, tuple(dot), 2, (105, 235, 140), -1)
        tiles.append(tile)
    if len(tiles) != 2:
        return None
    return jpeg_url(cv2, np.concatenate(tiles, axis=1)[:, ::-1])
