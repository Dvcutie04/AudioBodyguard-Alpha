import numpy as np
from dataclasses import dataclass


@dataclass
class HardCaseSet:
    features: np.ndarray
    y_true: np.ndarray
    confidence: np.ndarray
    indices: np.ndarray
    sample_ratio: float


class HardCaseExtractor:
    def __init__(self, lo_bound: float = 0.40, hi_bound: float = 0.90):
        self.lo_bound = lo_bound
        self.hi_bound = hi_bound

    def extract_ambiguous(
        self,
        features: np.ndarray,
        y_true: np.ndarray,
        probs: np.ndarray,
    ) -> HardCaseSet:
        probs = np.asarray(probs)

        if len(y_true) != len(features) or len(y_true) != len(probs):
            raise ValueError(
                "features, y_true, and probs must have equal length"
            )

        if probs.ndim > 1:
            conf = np.max(probs, axis=1)
        else:
            conf = np.abs(probs - 0.5) * 2.0

        mask = (conf >= self.lo_bound) & (conf <= self.hi_bound)
        idxs = np.where(mask)[0]

        ratio = float(len(idxs) / len(y_true)) if len(y_true) else 0.0

        return HardCaseSet(
            features=features[idxs],
            y_true=y_true[idxs],
            confidence=conf[idxs],
            indices=idxs,
            sample_ratio=ratio,
        )
