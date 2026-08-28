import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

@dataclass
class FabricEvent:
    event_id: str
    timestamp: float
    tx_id: str
    event_type: str  # e.g., "TX_COMMITTED", "TX_ROLLED_BACK", "DRIFT_DETECTED"
    payload: Dict[str, Any]
    previous_hash: str
    event_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """
        Deterministically hashes the event contents to freeze it in time.
        """
        # Convert to dictionary and exclude the hash field itself
        data = asdict(self)
        data.pop('event_hash', None)
        
        # Sort keys to ensure consistent JSON serialization order
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
