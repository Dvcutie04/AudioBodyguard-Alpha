from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ActuationReceipt:
    action_id: str
    device_id: str
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    triggering_hypothesis_id: str
    policy_decision: str
    safety_decision: str
    source_lineage_digest: str
    timestamp_ns: int
