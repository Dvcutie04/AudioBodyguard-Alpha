from dataclasses import dataclass, field
import time

@dataclass(frozen=True)
class FeedbackEvent:
    event_id: str
    action_id: str
    timestamp: float = field(default_factory=time.time)
    feedback_type: str = "AGREE"  # AGREE, DISAGREE, UNSURE
    rating: float = 0.0
    reason: str = ""
    threat_probability: float = 0.0
    action_confidence: float = 0.0
    context_id: str = "unknown"
    policy_version: int = 0
    model_version: str = "1.0.0"
    source: str = "user_ui"
