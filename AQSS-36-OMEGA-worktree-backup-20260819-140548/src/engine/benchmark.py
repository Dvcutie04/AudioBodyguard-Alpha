import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

@dataclass
class MetricPolicy:
    weight_latency: float = 0.10
    weight_shots: float = 0.05
    fpr_max: float = 0.05
    fnr_max: float = 0.05
    latency_ceiling_ms: float = 50.0
    shot_budget: int = 2048

    def weight_quality(self) -> float:
        w = 1.0 - (self.weight_latency + self.weight_shots)
        return max(0.0, w)

@dataclass
class EvalRating:
    winner: str
    classical_composite: float
    quantum_composite: float
    composite_delta: float
    accuracy_delta_ci: Tuple[float, float]
    fpr_delta_ci: Tuple[float, float]
    brier_delta_ci: Tuple[float, float]
    rejected_reason: Optional[str] = None

class BenchmarkHarness:
    def __init__(self, nboots: int = 1000):
        self.nbootstraps = nboots

    def _calc_metrics(self, ytrue, ypred):
        return {}
