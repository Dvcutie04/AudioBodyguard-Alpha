import hashlib
import time
from typing import Optional
from src.inference.hypothesis import HypothesisFrame
from src.intent.action_intent import ActionIntent


class HypothesisGate:
    """
    Evaluates whether a HypothesisFrame is epistemically actionable 
    and converts it into an explicit ActionIntent.
    """

    def __init__(self, min_probability: float = 0.85, min_quality: float = 0.80):
        self.min_probability = min_probability
        self.min_quality = min_quality

    def evaluate(self, hypothesis: HypothesisFrame) -> Optional[ActionIntent]:
        # Enforce epistemic boundary checks
        if (
            hypothesis.hypothesis_probability < self.min_probability
            or hypothesis.evidence_quality < self.min_quality
        ):
            return None

        # Derive intent lineage digest deterministically from hypothesis digest
        intent_lineage = hashlib.sha256(
            f"{hypothesis.source_lineage_digest}:intent_gate".encode("utf-8")
        ).hexdigest()

        if hypothesis.hypothesis_type == "COMMERCIAL_ACTIVE":
            return ActionIntent(
                intent_id=f"intent_{hypothesis.hypothesis_id}",
                intent_type="REDUCE_TV_VOLUME",
                target_device_id="tv_living_room",
                target_delta={"volume_db": -6.0},
                triggering_hypothesis_id=hypothesis.hypothesis_id,
                triggering_lineage_digest=intent_lineage,
                policy_context={"allowed_max_drop_db": 10.0},
            )

        return None
