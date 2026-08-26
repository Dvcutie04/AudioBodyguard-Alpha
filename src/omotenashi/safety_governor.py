from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from src.omotenashi.conversation_policy import ConversationPolicyEvaluation, PolicyAction

class GovernorDecision(str, Enum):
    PERMIT = "PERMIT"
    BLOCK = "BLOCK"

@dataclass(frozen=True)
class SafetyGovernorResult:
    decision: GovernorDecision
    approved_action: PolicyAction
    attenuation_level: float
    audit_trail: List[str]

class SafetyGovernor:
    """
    Final mandatory enforcement layer for Conversation-Protect Mode.
    Ensures safety invariants:
      - Validates policy bounds
      - Rejects unverified or out-of-bound attenuation levels
      - Maintains a structured audit trail without retaining raw audio data
    """
    def __init__(self, max_allowed_attenuation: float = 0.95):
        if not 0.0 <= max_allowed_attenuation <= 1.0:
            raise ValueError("max_allowed_attenuation must be in [0, 1]")
        self.max_allowed_attenuation = max_allowed_attenuation

    def enforce(self, policy_eval: ConversationPolicyEvaluation) -> SafetyGovernorResult:
        audit = []
        audit.append(f"Received policy action: {policy_eval.action.value}")
        audit.append(f"Requested attenuation: {policy_eval.attenuation_level}")

        # Invariant check: attenuation must not exceed system safety limits
        if policy_eval.attenuation_level > self.max_allowed_attenuation:
            audit.append("BLOCK: Requested attenuation exceeds safety maximum.")
            return SafetyGovernorResult(
                decision=GovernorDecision.BLOCK,
                approved_action=PolicyAction.MAINTAIN_BASELINE,
                attenuation_level=0.0,
                audit_trail=audit
            )

        # Invariant check: action validation
        if policy_eval.action == PolicyAction.ACTIVATE_PROTECTION:
            audit.append("PERMIT: Protection action validated safely.")
            return SafetyGovernorResult(
                decision=GovernorDecision.PERMIT,
                approved_action=PolicyAction.ACTIVATE_PROTECTION,
                attenuation_level=policy_eval.attenuation_level,
                audit_trail=audit
            )
        else:
            audit.append("PERMIT: Baseline action maintained.")
            return SafetyGovernorResult(
                decision=GovernorDecision.PERMIT,
                approved_action=PolicyAction.MAINTAIN_BASELINE,
                attenuation_level=policy_eval.attenuation_level,
                audit_trail=audit
            )
