import time
import uuid
from typing import List, Dict, Any
from src.device_fabric.event_log import FabricEvent


class CryptographicLineageManager:
    """
    Maintains an append-only, cryptographically verifiable ledger of all physical state transitions.
    Provides absolute auditability for Phase 2.5's Physical Truth Invariant.
    """
    def __init__(self):
        # In-memory chain for now; in a full deployment, this flushes to a secure data store
        self._chain: List[FabricEvent] = []
        self._genesis_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    def get_last_hash(self) -> str:
        if not self._chain:
            return self._genesis_hash
        return self._chain[-1].event_hash or self._genesis_hash

    def record_event(self, tx_id: str, event_type: str, payload: Dict[str, Any]) -> FabricEvent:
        """
        Seals a new event and appends it to the cryptographic chain.
        """
        prev_hash = self.get_last_hash()
        
        event = FabricEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            tx_id=tx_id,
            event_type=event_type,
            payload=payload,
            previous_hash=prev_hash
        )
        
        event.event_hash = event.compute_hash()
        self._chain.append(event)
        
        return event

    def verify_chain_integrity(self) -> bool:
        """
        Validates the entire cryptographic chain. Returns False if any event payload, 
        timestamp, or linkage was tampered with.
        """
        if not self._chain:
            return True
            
        expected_prev = self._genesis_hash
        
        for event in self._chain:
            # 1. Verify linkage (does this event correctly point to the previous one?)
            if event.previous_hash != expected_prev:
                return False
            
            # 2. Verify computational integrity (was the payload altered?)
            computed = event.compute_hash()
            if event.event_hash != computed:
                return False
                
            expected_prev = event.event_hash
            
        return True
        
    def get_history(self) -> List[FabricEvent]:
        return self._chain.copy()
