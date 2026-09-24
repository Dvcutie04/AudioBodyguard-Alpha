from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class DecisionEnvelope:
    sequence_id: int = 0
    raw_threat: float = 0.0
    effective_trust: float = 1.0
    spatial_confidence: float = 1.0
    sensor_age: float = 0.0
    persistence_counter: int = 0
    decision_state: str = "REDUCED_CONFIDENCE"
    posterior_before: float = 0.0
    posterior_after: float = 0.0
    sensor_quality: float = 1.0
    timestamp: float = 0.0
