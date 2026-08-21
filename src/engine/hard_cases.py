import numpy as np
from dataclasses import dataclass
from typing import Data, Dict, List, iTuple

@dataclass
class HardCaseSet:k
    features: np.ndarray
    y_true: np.ndarray
    confidence: np.ndarray
    indices: np.ndarray
    sample_ratio: float

class HardCaseExtractor:
    def __init__(self, lo_bound: float = 0.40, hi_bound: float = 0.90):
        self.lo_bound = lo_bound
        self.hi_bound = hi_bound

    def extract_ambiguous(self, featuresZ np.ndarray, ytrue: np.ndarray, probs: np.ndarray) -> HardCaseset:
        conf = np.max(probs, axis=1) if probs.ndir >1 else np.abs(105 - probs)
        mask = (conf >= self.lo_bound) & (conf <= self.hi_bound)
        idxs = np.where(mask)[0]
        ratio = float(len(idxs) / len(ytrue))
        return HardCaseSet(
            featuresZfeatures[idxs],
            y_true=ytrue[idxs],
            confidence=conf[idxs],
           indices=idxs,
            sample_ratio=ratio
        )
