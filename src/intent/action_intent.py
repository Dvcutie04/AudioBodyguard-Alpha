from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ActionIntent:
    intent_id: str
    intent_type: str
    target_device_id: str
    target_delta: Dict[str, Any]
    triggering_hypothesis_id: str
    triggering_lineage_digest: str
    policy_context: Dict[str, Any]
