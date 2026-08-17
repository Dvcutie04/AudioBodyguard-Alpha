import json
from dataclasses import dataclass

@dataclass
class ActionVerdict:
    material_state: str
    confidence: float
    action_type: str
    requires_confirmation: bool

class TrustGradient:
    def __init__(self):
        # Thresholds defined by the 2030 Omotenashi vision
        self.threshold_stone = 0.90   # Certain -> act silently
        self.threshold_bamboo = 0.70  # Moderately certain -> act gently
        self.threshold_silk = 0.40    # Uncertain -> ask
        
    def evaluate_confidence(self, confidence_score: float) -> ActionVerdict:
        if confidence_score >= self.threshold_stone:
            return ActionVerdict("Stone", confidence_score, "silent_execution", False)
        elif confidence_score >= self.threshold_bamboo:
            return ActionVerdict("Bamboo", confidence_score, "gentle_execution", False)
        elif confidence_score >= self.threshold_silk:
            return ActionVerdict("Silk", confidence_score, "prompt_user", True)
        else:
            return ActionVerdict("Hard_Stop", confidence_score, "do_not_act", True)

if __name__ == '__main__':
    gradient = TrustGradient()
    # Simulate a 0.85 confidence signal (should be Bamboo)
    verdict = gradient.evaluate_confidence(0.85)
    print(f"Omotenashi Trust Verdict: {verdict.material_state} - {verdict.action_type}")
