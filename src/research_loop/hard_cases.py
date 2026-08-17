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

    def extract_ambiguous(self, features: np.ndarray, ytrue: np.ndarray, conf: np.ndarray) -> HardCaseSet:
        idxs = np.where((conf >= self.lo_bound) & (conf <= self.hi_bound))[0]
        ratio = len(idxs) / len(conf) if len(conf) > 0 else 0.0
        return HardCaseSet(
            features=features[idxs],
            y_true=ytrue[idxs],
            confidence=conf[idxs],
            indices=idxs,
            sample_ratio=ratio
        )
