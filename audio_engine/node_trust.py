from dataclasses import dataclass, field
from typing import Tuple, List

@dataclass(frozen=True)
class NodeTrust:
    identity: float
    freshness: float
    acoustic_health: float
    spatial_consistency: float
    calibration: float
    tamper_state: float
    temporal_integrity: float
    behavioral_stability: float
    epoch: int

class TrustEvaluator:
    IDENTITY_FLOOR = 0.8
    TAMPER_FLOOR = 0.2
    REPLAY_FLOOR = 0.5

    def __init__(self, current_known_epoch: int = 1):
        self.current_epoch = current_known_epoch

    def evaluate(self, trust: NodeTrust) -> Tuple[str, float, List[str]]:
        reasons = []

        # 1. Trust Epoch Validation
        if trust.epoch < self.current_epoch:
            reasons.append("STALE_EPOCH_REJECTED")
            return "REJECT", 0.0, reasons
        elif trust.epoch > self.current_epoch:
            # Advance epoch state
            self.current_epoch = trust.epoch
            reasons.append("EPOCH_ADVANCED")

        # 2. Hard Gates (Cannot be averaged away)
        if trust.identity < self.IDENTITY_FLOOR:
            reasons.append("IDENTITY_FAILURE")
            return "REJECT", 0.0, reasons
            
        if trust.tamper_state < self.TAMPER_FLOOR:
            reasons.append("TAMPER_DETECTED")
            return "QUARANTINE", 0.0, reasons
            
        if trust.temporal_integrity < self.REPLAY_FLOOR:
            reasons.append(
                "TEMPORAL_INTEGRITY_FAILURE"
            )
            return "REJECT", 0.0, reasons

        # 3. Soft Trust Dimensions (Composite Scoring)
        soft_dimensions = [
            trust.freshness,
            trust.acoustic_health,
            trust.spatial_consistency,
            trust.calibration,
            trust.behavioral_stability
        ]
        
        for dim in soft_dimensions:
            if not (0.0 <= dim <= 1.0):
                reasons.append("INVALID_DIMENSION_BOUNDS")
                return "REJECT", 0.0, reasons

        effective_trust = sum(soft_dimensions) / len(soft_dimensions)
        effective_trust = max(0.0, min(1.0, effective_trust))
        
        if effective_trust < 0.6:
            reasons.append("DEGRADED_PERFORMANCE")
            return "DEGRADED", effective_trust, reasons
            
        reasons.append("TRUST_HEALTHY")
        return "TRUSTED", effective_trust, reasons
