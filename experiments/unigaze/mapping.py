"""Research Ridge mapping; independent of inference and camera."""

import numpy as np


class Ridge:
    def __init__(self, standardize=False):
        self.standardize = standardize
        self.weights = None

    def fit(self, x, y):
        x = np.asarray(x, np.float32)
        y = np.asarray(y, np.float32)
        if (
            x.ndim != 2
            or y.shape != (len(x), 2)
            or not len(x)
            or not np.isfinite(x).all()
            or not np.isfinite(y).all()
        ):
            raise ValueError("Invalid training data")
        self.mean = x.mean(0) if self.standardize else np.zeros(x.shape[1])
        self.scale = np.maximum(x.std(0), 1e-4) if self.standardize else np.ones(x.shape[1])
        z = np.c_[np.ones(len(x)), (x - self.mean) / self.scale]
        penalty = np.eye(z.shape[1]) * 0.1
        penalty[0, 0] = 0
        self.weights = np.linalg.solve(z.T @ z + penalty, z.T @ y)
        return self

    def predict(self, x):
        if self.weights is None:
            raise ValueError("Not calibrated")
        x = np.asarray(x, np.float32)
        if x.shape != (len(self.mean),) or not np.isfinite(x).all():
            raise ValueError("Invalid prediction features")
        return np.r_[1.0, (x - self.mean) / self.scale] @ self.weights
