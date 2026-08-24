import math
from typing import Dict, Any

class ThreatEvaluator:
    def __init__(self, safety_governor, prior: float = 0.1):
        self.safety_governor = safety_governor
        self.prior = prior
    def update_bayesian_probability(self, likelihood: float, evidence: float) -> float:
        if evidence == 0:
            return self.prior
        posterior = (likelihood * self.prior) / evidence
        return max(0.0, min(1.0, posterior))
    def assess_acoustic_spike(self, decibel_level: float, frequency_profile: str) -> Dict[str, Any]:
        likelihood = min(1.0, decibel_level / 120.0)
        evidence = 0.5
        p_current = self.update_bayesian_probability(likelihood, evidence)
        state = self.safety_governor.pm.current_state
        evaluation = self.safety_governor.evaluate_action("alert", p_current, decibel_level)
        return {"p_threat": p_current, "evaluation": evaluation, "profile": frequency_profile}
