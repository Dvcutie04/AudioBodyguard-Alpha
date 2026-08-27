from typing import Tuple, Dict, Any
from src.intent.action_intent import ActionIntent


class SafetyGovernor:
    """
    Evaluates proposed ActionIntents against system safety invariants.
    Answers: 'Even if the hypothesis is credible, is this specific action safe?'
    """

    def __init__(self, max_allowed_db_drop: float = 12.0):
        self.max_allowed_db_drop = max_allowed_db_drop

    def evaluate_intent(self, intent: ActionIntent) -> Tuple[bool, str]:
        if intent.intent_type == "REDUCE_TV_VOLUME":
            proposed_drop = abs(intent.target_delta.get("volume_db", 0.0))
            if proposed_drop > self.max_allowed_db_drop:
                return False, "SAFETY_REJECTED_EXCESSIVE_DELTA"
            
            return True, "SAFETY_PASSED"

        return False, "SAFETY_REJECTED_UNKNOWN_INTENT"
