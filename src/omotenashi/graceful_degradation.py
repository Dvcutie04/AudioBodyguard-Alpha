import math
from dataclasses import dataclass

@dataclass
class ActionVerdict:
    material_state: str
    confidence: float
    action_type: str
    requires_confirmation: bool

class TrustGradient:
    def __init__(self):
        # Display-only confidence bands. They convey no execution authority.
        self.threshold_stone = 0.90
        self.threshold_bamboo = 0.70
        self.threshold_silk = 0.40
        
    def evaluate_confidence(self, confidence_score: float) -> ActionVerdict:
        if type(confidence_score) not in (int, float) or not math.isfinite(confidence_score) or not 0 <= confidence_score <= 1:
            raise ValueError("invalid confidence")
        if confidence_score >= self.threshold_stone:
            band = "high_confidence"
        elif confidence_score >= self.threshold_bamboo:
            band = "moderate_confidence"
        elif confidence_score >= self.threshold_silk:
            band = "low_confidence"
        else:
            return ActionVerdict("insufficient_evidence", confidence_score, "do_not_act", False)
        return ActionVerdict(band, confidence_score, "propose_for_review", True)

if __name__ == '__main__':
    gradient = TrustGradient()
    # Simulate a 0.85 confidence proposal; no command is issued.
    verdict = gradient.evaluate_confidence(0.85)
    print(f"Omotenashi Trust Verdict: {verdict.material_state} - {verdict.action_type}")
