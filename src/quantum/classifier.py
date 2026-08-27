import math
from typing import Dict


class TwoQubitAnalyticalClassifier:
    """
    Simulates a 2-qubit probability output for spectral/SPL state mapping.
    Maps acoustic parameters to 4 quantum measurement state probabilities: |00>, |01>, |10>, |11>.
    """

    def predict_probabilities(
        self, spl_normalized: float, spectral_flatness: float, theta_bias: float = 0.0
    ) -> Dict[str, float]:
        # Clamp inputs to valid [0, 1] bounds
        spl = max(0.0, min(1.0, spl_normalized))
        flatness = max(0.0, min(1.0, spectral_flatness))
        bias = max(0.0, min(1.0, theta_bias))

        # Compute deterministic state amplitudes based on physical inputs
        alpha = math.cos((spl + bias) * math.pi / 4.0)
        beta = math.sin((flatness + bias) * math.pi / 4.0)

        # Unnormalized weights
        w00 = (alpha**2) * (1.0 - spl)
        w01 = (alpha**2) * spl
        w10 = (beta**2) * (1.0 - flatness)
        w11 = (beta**2) * flatness

        total = w00 + w01 + w10 + w11

        # Fallback to equal superposition if energy sums to 0
        if total <= 0:
            return {"00": 0.25, "01": 0.25, "10": 0.25, "11": 0.25}

        # Return strictly normalized probabilities
        return {
            "00": round(w00 / total, 6),
            "01": round(w01 / total, 6),
            "10": round(w10 / total, 6),
            "11": round(w11 / total, 6),
        }
