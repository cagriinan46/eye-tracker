"""Vendor-neutral data and lifecycle boundaries for the Vision layer."""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CameraFrame:
    """One captured image with immutable metadata and an opaque in-memory payload.

    ``timestamp_ns`` is the monotonic capture time, suitable for elapsed-time
    measurements. The payload is owned by the concrete Vision implementation;
    this contract neither copies nor interprets its pixel representation.
    """

    payload: object
    width: int
    height: int
    timestamp_ns: int

    def __post_init__(self) -> None:
        if self.payload is None:
            raise ValueError("frame payload must be available")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("frame dimensions must be positive")
        if self.timestamp_ns < 0:
            raise ValueError("frame timestamp must be non-negative")


@dataclass(frozen=True, slots=True)
class NormalizedPoint:
    """An image-normalized point; out-of-frame estimates are not clipped."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("normalized point coordinates must be finite")


@dataclass(frozen=True, slots=True)
class LandmarkObservation:
    """One face's ordered landmarks, or ``None`` when unavailable.

    Landmark topology and index meanings belong to a concrete Vision adapter,
    not this shared contract. An empty tuple is invalid so it cannot be
    confused with an unavailable observation.
    """

    timestamp_ns: int
    landmarks: tuple[NormalizedPoint, ...] | None

    def __post_init__(self) -> None:
        if self.timestamp_ns < 0:
            raise ValueError("observation timestamp must be non-negative")
        if self.landmarks is not None and not isinstance(self.landmarks, tuple):
            raise TypeError("landmarks must be an immutable tuple")
        if self.landmarks is not None and not self.landmarks:
            raise ValueError("available landmarks must not be empty")


class FrameSource(Protocol):
    """Synchronous frame source owned by its caller.

    Call ``open`` before ``read`` and always call ``close`` in a ``finally``
    block. ``read`` returns ``None`` when no frame is available.
    """

    def open(self) -> None: ...

    def read(self) -> CameraFrame | None: ...

    def close(self) -> None: ...


class LandmarkExtractor(Protocol):
    """Extract normalized face geometry from a frame within the Vision layer."""

    def extract(self, frame: CameraFrame) -> LandmarkObservation: ...
