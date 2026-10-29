"""Load the unchanged pinned upstream filter without unrelated model dependencies."""

import hashlib
import importlib.util
import sys
import types
from collections import deque

import numpy as np

from .settings import BASELINE_SUPPORT

SOURCE = BASELINE_SUPPORT / "upstream/gazefollower/filter"
PACKAGE = "_local_pinned_gaze_filter"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules.setdefault(PACKAGE, package)
spec = importlib.util.spec_from_file_location(
    PACKAGE + ".HeuristicFilter", SOURCE / "HeuristicFilter.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HeuristicFilter = module.HeuristicFilter
SOURCE_HASHES = {
    name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
    for name in ["Filter.py", "HeuristicFilter.py"]
}


class StreamFilter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.filter = HeuristicFilter(look_ahead=3)
        self.timestamps = deque(maxlen=7)

    def update(self, value, timestamp_ns):
        if value is None or np.asarray(value).shape != (2,) or not np.isfinite(value).all():
            self.reset()
            return None, None
        self.timestamps.append(timestamp_ns)
        result = np.asarray(self.filter.filter_values(value), float)
        lag = 0.0 if len(self.timestamps) < 7 else (timestamp_ns - self.timestamps[-4]) / 1e6
        return result.tolist(), lag
