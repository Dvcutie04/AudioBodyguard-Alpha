import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass(frozen=True)
class MitigationProposal:
    proposal_id: str
    source_event_id: str
    predicted_probability: float
    horizon_ms: int
    proposed_action: str
    confidence: float
    expected_benefit: float
    uncertainty: float
    blast_radius: float
    expires_at: float

class ThreatTrajectory:
    def __init__(self, history: Optional[List[float]] = None):
        self.history = list(history) if history is not None else []

    def update(self, probability: float):
        self.history.append(probability)
        if len(self.history) > 10:
            self.history.pop(0)

    def compute_derivatives(self) -> tuple[float, float, float]:
        if not self.history:
            return 0.0, 0.0, 0.0
        p_current = self.history[-1]
        if len(self.history) == 1:
            return p_current, 0.0, 0.0
        
        p_prev = self.history[-2]
        p_dot = p_current - p_prev
        
        p_ddot = 0.0
        if len(self.history) >= 3:
            p_prev2 = self.history[-3]
            p_ddot = p_current - 2.0 * p_prev + p_prev2
            
        return p_current, p_dot, p_ddot

class PredictiveMitigationEngine:
    def __init__(self, max_blast_radius: float = 0.5, evidence_ttl_sec: float = 5.0):
        self.max_blast_radius = max_blast_radius
        self.evidence_ttl_sec = evidence_ttl_sec
        self._processed_events: Dict[str, float] = {}

    def evaluate(
        self,
        envelope: Any,
        trajectory: ThreatTrajectory,
        horizon_ms: int = 1000
    ) -> Optional[MitigationProposal]:
        # Check evidence TTL / staleness
        current_time = time.time()
        if (current_time - envelope.timestamp) > self.evidence_ttl_sec:
            return None

        # Check duplicate event
        if envelope.event_id in self._processed_events:
            return None

        p_current, p_dot, p_ddot = trajectory.compute_derivatives()
        dt = horizon_ms / 1000.0

        # Kinematic extrapolation: P_hat = P + P_dot*dt + 0.5*P_ddot*(dt^2)
        p_hat = p_current + (p_dot * dt) + (0.5 * p_ddot * (dt ** 2))
        p_hat = max(0.0, min(1.0, p_hat))

        # Dynamic uncertainty calculation based on acceleration magnitude and sensor quality
        uncertainty = min(1.0, abs(p_ddot) * 0.5 + (1.0 - envelope.sensor_quality) * 0.3)

        # High uncertainty suppresses aggressive proposal generation
        if p_hat > 0.6 and uncertainty > 0.3:
            proposed_action = "MONITOR"
            blast_radius = 0.1
            expected_benefit = 0.2
        elif p_hat > 0.7:
            proposed_action = "ATTENUATE"
            blast_radius = 0.3
            expected_benefit = 0.8
        elif p_hat > 0.4:
            proposed_action = "WARN"
            blast_radius = 0.2
            expected_benefit = 0.5
        else:
            proposed_action = "NORMAL"
            blast_radius = 0.0
            expected_benefit = 0.0

        if proposed_action == "NORMAL":
            return None

        # Blast radius enforcement
        if blast_radius > self.max_blast_radius:
            raise ValueError("Proposal exceeds permitted maximum blast radius")

        proposal_id = f"prop-{envelope.event_id}-{int(current_time * 1000)}"
        self._processed_events[envelope.event_id] = current_time

        return MitigationProposal(
            proposal_id=proposal_id,
            source_event_id=envelope.event_id,
            predicted_probability=p_hat,
            horizon_ms=horizon_ms,
            proposed_action=proposed_action,
            confidence=max(0.0, 1.0 - uncertainty),
            expected_benefit=expected_benefit,
            uncertainty=uncertainty,
            blast_radius=blast_radius,
            expires_at=current_time + dt
        )
