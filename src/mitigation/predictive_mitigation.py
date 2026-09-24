from dataclasses import dataclass

@dataclass(frozen=True)
class BoundedPrediction:
    horizon_ms: int
    probability: float
    lower_bound: float
    upper_bound: float
    uncertainty: float
    source_sequence: int
