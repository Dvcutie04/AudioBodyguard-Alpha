from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass(frozen=True)
class DecisionEnvelope:
    node_id: str = "node_1"
    sequence_id: int = 0
    trust_epoch: int = 1
    decision_state: str = "REDUCED_CONFIDENCE"
    effective_trust: float = 1.0
    trust_reason_codes: tuple = ()
    evidence_digest: str = "0"
    version: int = 2
    raw_threat: float = 0.0
    spatial_confidence: float = 1.0
    sensor_age: float = 0.0
    persistence_counter: int = 0
    posterior_before: float = 0.0
    posterior_after: float = 0.0
    sensor_quality: float = 1.0
    timestamp: float = 0.0
