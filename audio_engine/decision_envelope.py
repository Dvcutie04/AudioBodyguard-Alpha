from dataclasses import dataclass, field
import time

@dataclass(frozen=True)
class DecisionEnvelope:
    node_id: str
    sequence_id: int
    trust_epoch: int
    decision_state: str
    effective_trust: float
    trust_reason_codes: tuple[str, ...]
    evidence_digest: str
    version: int = 2
    timestamp_ns: int = field(default_factory=time.time_ns)
