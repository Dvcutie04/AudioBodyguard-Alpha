from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional
from src.omotenashi.hypothesis_gate import HypothesisGateResult, GateDecision

class PolicyAction(str, Enum):
    MAINTAIN_BASELINE = "MAINTAIN_BASELINE"
    ACTIVATE_PROTECTION = "ACTIVATE_PROTECTION"

@dataclass(frozen=True)
class ConversationPolicyEvaluation:
    action: PolicyAction
    attenuation_level: float
    reason: str

class ConversationPolicy:
    """
    Translates hypothesis gate decisions into safe conversation protection policies.
    Enforces structural boundaries:
      - consumes gate results only
      - issues policy states, never direct hardware/device actuation
      - defaults to safe baseline (no protection/baseline filtering) on uncertainty
    """
    def __init__(
        self,
        default_attenuation: float = 0.0,
        protected_attenuation: float = 0.85,
    ):
        if not 0.0 <= default_attenuation <= 1.0:
            raise ValueError("default_attenuation must be in [0, 1]")
        if not 0.0 <= protected_attenuation <= 1.0:
            raise ValueError("protected_attenuation must be in [0, 1]")
        
        self.default_attenuation = default_attenuation
        self.protected_attenuation = protected_attenuation

    def evaluate(
        self,
        gate_result: HypothesisGateResult,
    ) -> ConversationPolicyEvaluation:
        if gate_result.decision == GateDecision.PROPOSE:
            return ConversationPolicyEvaluation(
                action=PolicyAction.ACTIVATE_PROTECTION,
                attenuation_level=self.protected_attenuation,
                reason=f"Conversation proposed with confidence margin {gate_result.confidence_margin:.2f}"
            )
        else:
            return ConversationPolicyEvaluation(
                action=PolicyAction.MAINTAIN_BASELINE,
                attenuation_level=self.default_attenuation,
                reason=f"Gate suppressed conversation (competitor: {gate_result.competing_hypothesis.value})"
            )
