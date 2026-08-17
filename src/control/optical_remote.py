import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any

from ..omotenashi.graceful_degradation import TrustGradient, ActionVerdict

@dataclass
class ButtonExtraction:
    label: str
    shape: str
    position_x: float
    position_y: float

@dataclass
class RemoteHypothesis: 
    manufacturer_clue: str
    device_category: str
    protocol_type: str  # IR vs Bluetooth vs Wi-Fi
    possible_function: str
    confidence_score: float

class OpticalRemoteMapper:
    def __init__(self):
        self.trust_gradient = TrustGradient()

    def generate_hypothesis(self, buttons: List[ButtonExtraction], ir_emitter_detected: bool) -> RemoteHypothesis:
        unmatched_labels = [b.label.lower() for b in buttons]
        
        if "youtube" in " ".join(unmatched_labels) or "vol_up" in " ".join(unmatched_labels):
            function = "ACOUSTIC_VOLUME_CONTROL"
            confidence = 0.85 if ir_emitter_detected else 0.65
        else:
            function = "UNKNOWN_MEDIA_CONTROL"
            confidence = 0.35

        return RemoteHypothesis(
            manufacturer_clue="Generic_TCP_IR",
            device_category="Media_Player",
            protocol_type="IR" if ir_emitter_detected else "Wi-Fi",
            possible_function=function,
            confidence_score=confidence
        )

    def verify_command(self, hypothesis: RemoteHypothesis) -> Dict[str, Any]:
        verdict = self.trust_gradient.evaluate_confidence(hypothesis.confidence_score)
        return {
            "hypothesis": asdict(hypothesis),
            "trust_verdict": asdict(verdict),
            "execution_status": "Testing Command" if not verdict.requires_confirmation else "Pending User Confirmation"
        }

if __name__ == '__main__':
    mapper = OpticalRemoteMapper()
    sample_buttons = [
        ButtonExtraction("vol_up", "round", 0.1, 0.2),
        ButtonExtraction("vol_down", "round", 0.1, 0.3)
    ]
    
    hypothesis = mapper.generate_hypothesis(sample_buttons, ir_emitter_detected=True)
    result = mapper.verify_command(hypothesis)
    print(json.dumps(result, indent=2))
