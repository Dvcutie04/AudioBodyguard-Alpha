from __future__ import annotations
import hashlib
import math
from dataclasses import dataclass
from typing import Any, Tuple
import numpy as np

@dataclass(frozen=True)
class QuantumFeatureVector:
    values: Tuple[float, ...]
    schema_version: str
    normalization_version: str = "v1"
    source_window_ns: int = 0
    feature_hash: str = ""

class AcousticQuantumFeatureMapper:
    def __init__(self, expected_dim: int = 8):
        self.expected_dim = expected_dim

    def transform(self, raw_features: Any, source_window_ns: int = 0) -> QuantumFeatureVector:
        arr = np.asarray(raw_features, dtype=np.float64)
        if arr.ndim != 1 or len(arr) != self.expected_dim:
            raise ValueError(f"expected {self.expected_dim} features, got shape {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("feature vector contains non-finite values")
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        if std == 0.0:
            z = np.zeros_like(arr)
        else:
            z = (arr - mean) / std
        q = np.tanh(z)
        values = tuple(float(v) for v in q)
        if not all(math.isfinite(v) and -1.0 <= v <= 1.0 for v in values):
            raise ValueError("quantum feature vector outside [-1,1]")
        feature_hash = hashlib.sha256(np.asarray(values, dtype=np.float64).tobytes()).hexdigest()
        return QuantumFeatureVector(values=values, schema_version="AQSS-QFM-1.1", source_window_ns=source_window_ns, feature_hash=feature_hash)
