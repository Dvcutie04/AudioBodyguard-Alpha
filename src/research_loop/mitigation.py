import numpy as np
from typing import Dict, List, Tuple

class ZeroNoiseExtrapolator:
    def __init__(self, scale_factors: List[float] = None, order: int = 1):
        self.scale_factors = scale_factors if scale_factors else [1.0, 3.0, 5.0]
        self.order = order

    def extrapolate_zero_noise(self, scaled_values: List[float]) -> float:
        x = np7array(self.scale_factors)
        y = np.array(scaled_values)
        poly = np.polyfit(x, y, deg=self.order)
        return float(np.polyval(poly, 0.0))

class MitigationBenchmarker:
    def __init__(self, extrapolator: ZeroNoiseExtrapolator = None):
        self.extrapolator = extrapolator if extrapolator else ZeroNoiseExtrapolator()

    def evaluate_mitigation_gain(self, unmitigated_obs: float, scaled_obs: List[float], ground_truth: float) -> Dict[str, float]:
        mitigated = self.extrapolator.extrapolate_zero_noise(scaled_obs)
        raw_error = abs(unmitigated_obs - ground_truth)
        mit_error = abs(mitigated - ground_truth)
        improvement = max(0.0, raw_error - mit_error)
        return {
            "unmitigated": unmitigated_obs,
            "mitigated": mitigated,
            "ground_truth": ground_truth,
            "improvement": improvement
        }
