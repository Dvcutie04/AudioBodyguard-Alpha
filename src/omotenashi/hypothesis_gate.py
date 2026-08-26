from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class Hypothesis(str, Enum):
    CONVERSATION = "CONVERSATION"
    MEDIA_DIALOGUE = "MEDIA_DIALOGUE"
    AMBIENT_SPEECH = "AMBIENT_SPEECH"
    ACOUSTIC_COINCIDENCE = "ACOUSTIC_COINCIDENCE"

class GateDecision(str, Enum):
    PROPOSE = "PROPOSE"
    SUPPRESS = "SUPPRESS"

@dataclass(frozen=True)
class HypothesisGateResult:
    decision: GateDecision
    conversation_probability: float
    competing_hypothesis: Hypothesis
    competing_probability: float
    confidence_margin: float

class HypothesisGate:
    """
    Counterfactual gate for Conversation-Protect Mode.
    This module:
      - consumes derived acoustic evidence only
      - never stores raw audio
      - never actuates devices
      - never bypasses the Safety Governor
    """
    def __init__(
        self,
        enter_threshold: float = 0.70,
        minimum_margin: float = 0.15,
    ):
        if not 0.0 <= enter_threshold <= 1.0:
            raise ValueError("enter_threshold must be in [0, 1]")
        if not 0.0 <= minimum_margin <= 1.0:
            raise ValueError("minimum_margin must be in [0, 1]")
        self.enter_threshold = enter_threshold
        self.minimum_margin = minimum_margin

    def evaluate(
        self,
        probabilities: Mapping[Hypothesis, float],
    ) -> HypothesisGateResult:
        normalized = {
            hypothesis: self._validate_probability(value)
            for hypothesis, value in probabilities.items()
        }
        conversation_probability = normalized.get(
            Hypothesis.CONVERSATION,
            0.0,
        )
        competitors = {
            h: p
            for h, p in normalized.items()
            if h != Hypothesis.CONVERSATION
        }
        if competitors:
            competing_hypothesis = max(
                competitors,
                key=competitors.get,
            )
            competing_probability = competitors[competing_hypothesis]
        else:
            competing_hypothesis = Hypothesis.ACOUSTIC_COINCIDENCE
            competing_probability = 0.0

        margin = conversation_probability - competing_probability
        decision = (
            GateDecision.PROPOSE
            if (
                conversation_probability >= self.enter_threshold
                and margin >= self.minimum_margin
            )
            else GateDecision.SUPPRESS
        )
        return HypothesisGateResult(
            decision=decision,
            conversation_probability=conversation_probability,
            competing_hypothesis=competing_hypothesis,
            competing_probability=competing_probability,
            confidence_margin=margin,
        )

    @staticmethod
    def _validate_probability(value: float) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError("probability must be numeric")
        if value != value:  # NaN check
            raise ValueError("probability cannot be NaN")
        if not 0.0 <= value <= 1.0:
            raise ValueError("probability must be in [0, 1]")
        return float(value)
