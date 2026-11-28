"""Gain around the screen centre plus recentring, on top of a #156 mapping."""

from dataclasses import dataclass

from experiments.head_pointer.pointer import Mapping


@dataclass
class GainedPointer:
    """Normalized screen point = 0.5 + gain * (mapping - 0.5) + offset, per axis.

    ``recentre`` shifts the offset so that the current head signal lands on the
    screen centre; it does not change the gain.
    """

    mapping: Mapping
    gain: float = 1.0
    offset: tuple[float, float] = (0.0, 0.0)

    def __call__(self, signal: tuple[float, float]) -> tuple[float, float]:
        mapped = self.mapping(signal)
        return tuple(
            0.5 + self.gain * (m - 0.5) + o for m, o in zip(mapped, self.offset, strict=True)
        )

    def recentre(self, signal: tuple[float, float]) -> None:
        current = self(signal)
        self.offset = tuple(o - (c - 0.5) for o, c in zip(self.offset, current, strict=True))
