"""Stage B1 calibration availability/conditioning only; no outcome evaluation."""

import json
from pathlib import Path

import numpy as np

from experiments.raw_geometry_gaze_diagnostic.geometry import FACE_ANCHOR_INDICES

from . import representations as rep
from .calibration import fit_candidates, parse_presentations

DEVELOPMENT_CAPTURE = (
    Path(__file__).resolve().parents[2] / ".venv/raw-geometry-gaze-cagri-geometry-1.json"
)
_IDENTITY = {
    "protocol_name": "raw_geometry_gaze_diagnostic",
    "protocol_version": 1,
    "geometry_schema_version": 1,
    "session": "geometry-1",
    "session_role": "development",
}


class _Reader:
    def __init__(self, stream):
        self.stream = stream
        self.pending = ""

    def read(self):
        if self.pending:
            value, self.pending = self.pending, ""
            return value
        value = self.stream.read(1)
        if not value:
            raise ValueError("incomplete calibration JSON prefix")
        # Capture json.dump uses ensure_ascii=True. Decode one byte only, never
        # let a text wrapper prefetch/decode the following validation section.
        return value.decode("ascii") if isinstance(value, bytes) else value

    def nonspace(self):
        char = self.read()
        while char.isspace():
            char = self.read()
        return char


def _value(reader, first, retain=True):
    """Lexically skip unneeded fields; decode only identity and calibration."""
    output = [first] if retain else []
    quoted, escaped = first == '"', False
    stack = [first] if first in "[{" else []
    if not quoted and not stack:
        while True:
            char = reader.read()
            if char.isspace() or char in ",}":
                reader.pending = char
                return "".join(output)
            if retain:
                output.append(char)
    while True:
        char = reader.read()
        if retain:
            output.append(char)
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
                if not stack:
                    return "".join(output)
        elif char == '"':
            quoted = True
        elif char in "[{":
            stack.append(char)
        elif char in "]}":
            if not stack or (stack.pop(), char) not in (("[", "]"), ("{", "}")):
                raise ValueError("malformed calibration JSON prefix")
            if not stack:
                return "".join(output)


def read_calibration_prefix(stream):
    """Stop immediately after calibration array; never read/parse trailing trials."""
    reader, identity = _Reader(stream), {}
    if reader.nonspace() != "{":
        raise ValueError("capture must be a JSON object")
    while True:
        char = reader.nonspace()
        if char != '"':
            raise ValueError("calibration array absent or invalid object key")
        key = json.loads(_value(reader, char))
        if reader.nonspace() != ":":
            raise ValueError("invalid object key separator")
        if key in ("trials", "validation_presentations"):
            raise ValueError("validation encountered before calibration; refusing to read")
        if key == "calibration_presentations":
            if identity != _IDENTITY:
                raise ValueError("only geometry-1 development identity is permitted")
            first = reader.nonspace()
            if first != "[":
                raise ValueError("calibration presentations must be an array")
            return parse_presentations(json.loads(_value(reader, first)))
        if key in _IDENTITY:
            if key in identity:
                raise ValueError("duplicate identity field")
            identity[key] = json.loads(_value(reader, reader.nonspace()))
        else:
            _value(reader, reader.nonspace(), retain=False)
        if reader.nonspace() != ",":
            raise ValueError("calibration array absent or invalid field separator")


def load_development_calibration(path=None):
    """Single allowlisted local path; reject holdout and symlinks before open."""
    path = DEVELOPMENT_CAPTURE if path is None else Path(path)
    expected = DEVELOPMENT_CAPTURE.absolute()
    # Reject other paths lexically, before resolve() can stat a holdout path.
    if path.absolute() != expected:
        raise ValueError("Stage B1 permits only the fixed development capture path")
    if path.is_symlink() or path.resolve() != expected:
        raise ValueError("Stage B1 permits only the fixed development capture path")
    with path.open("rb", buffering=0) as stream:
        return read_calibration_prefix(stream)


def calibration_sanity(presentations):
    """No residuals, accuracy, rankings, validation fields or metrics."""
    fits = fit_candidates(presentations)
    records = [
        s["raw_geometry"]
        for p in presentations
        for s in p.samples
        if s["feature_status"] == "usable"
    ]
    summary = {
        "session": "geometry-1",
        "fields_consumed": ["identity", "calibration_presentations"],
        "calibration_presentations": len(presentations),
        "candidates": {},
    }
    for name, fit in fits.items():
        conditions = []
        for record in records:
            try:
                if name == "R1":
                    current = rep.points_xyz(record, FACE_ANCHOR_INDICES)
                    if rep.fit_similarity(current, fit.reference) is not None:
                        conditions.append(float(np.linalg.cond(current - current.mean(axis=0))))
                elif name == "R2":
                    for side in ("left", "right"):
                        current = rep.local_eye(record, side).contour
                        if rep.fit_affine(current, fit.reference[side]) is not None:
                            design = np.column_stack((current, np.ones(16)))
                            conditions.append(float(np.linalg.cond(design)))
            except (KeyError, TypeError, ValueError, FloatingPointError, np.linalg.LinAlgError):
                continue
        summary["candidates"][name] = {
            "mapping_evaluable": fit.mapping is not None,
            "unavailable_reason": fit.unavailable_reason,
            "usable_calibration_samples_per_presentation": list(fit.usable_counts),
            "conditioning_range": [min(conditions), max(conditions)] if conditions else None,
        }
    return summary


def main():
    # No arbitrary capture argument or outcome-evaluation switch exists in B1.
    print(json.dumps(calibration_sanity(load_development_calibration()), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
