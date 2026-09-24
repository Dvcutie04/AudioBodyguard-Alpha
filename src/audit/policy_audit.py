import time
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class PolicyAuditRecord:
    decision_id: str
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""
    previous_policy_version: int = 0
    proposed_policy_version: int = 0
    source: str = "system"
    target_field: str = ""
    previous_value: float = 0.0
    proposed_value: float = 0.0
    accepted_value: float = 0.0
    feedback_type: str = ""
    feedback_weight: float = 0.0
    confidence_weight: float = 0.0
    context_weight: float = 0.0
    recency_weight: float = 0.0
    raw_delta: float = 0.0
    bounded_delta: float = 0.0
    hysteresis_result: bool = False
    governor_result: bool = False
    governor_reason: str = ""
    model_version: str = "1.0.0"

class PolicyAuditLedger:
    def __init__(self):
        self._ledger = []
    def record(self, record: PolicyAuditRecord) -> None:
        self._ledger.append(record)
    def export_ledger(self) -> list[Dict[str, Any]]:
        return [r.__dict__ for r in self._ledger]
