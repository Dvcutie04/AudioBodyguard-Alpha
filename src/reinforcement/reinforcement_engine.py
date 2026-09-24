from dataclasses import dataclass
from src.reinforcement.feedback_event import FeedbackEvent

@dataclass(frozen=True)
class ReinforcementProposal:
    event_id: str
    policy_version: int
    target: str
    delta: float
    confidence: float
    reason: str

class ConfidenceWeightedReinforcementEngine:
    def __init__(self, alpha: float = 2.0):
        self.alpha = alpha

    def compute_proposal(self, event: FeedbackEvent) -> ReinforcementProposal:
        if event.feedback_type == "UNSURE":
            return ReinforcementProposal(
                event_id=event.event_id,
                policy_version=event.policy_version,
                target="alert_preference",
                delta=0.0,
                confidence=event.action_confidence,
                reason="Unsure feedback yields zero delta"
            )
        
        error_direction = 1.0 if event.feedback_type == "AGREE" else -1.0
        w_feedback = abs(event.rating) if event.rating != 0.0 else 1.0
        w_confidence = event.action_confidence
        w_recency = 1.0
        w_reliability = 1.0
        
        total_weight = w_feedback * w_confidence * w_recency * w_reliability
        delta = self.alpha * total_weight * error_direction
        
        return ReinforcementProposal(
            event_id=event.event_id,
            policy_version=event.policy_version,
            target="alert_preference",
            delta=delta,
            confidence=w_confidence,
            reason=f"Processed {event.feedback_type} with weight {total_weight:.3f}"
        )
