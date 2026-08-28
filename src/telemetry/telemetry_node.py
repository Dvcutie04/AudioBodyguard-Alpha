"""
Distributed Edge Telemetry Node Ingestion Layer

Handles signed sensory observation ingests from distributed acoustic nodes.
Ensures telemetry integrity prior to state lattice fusion.
"""

import time
import json
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class SensorObservation:
    node_id: str
    timestamp: float
    ambient_db: float
    frequency_spectrum: Dict[str, float] = field(default_factory=dict)
    epoch: int = 0
    nonce: str = "00000000"
    signature: Optional[str] = None

    @property
    def canonical_bytes(self) -> bytes:
        """Returns deterministic canonical payload string for telemetry signing."""
        spectrum_str = json.dumps(self.frequency_spectrum, sort_keys=True, separators=(',', ':'))
        payload = (
            f"{self.node_id}:{self.timestamp:.4f}:{self.ambient_db:.2f}:"
            f"{spectrum_str}:{self.epoch}:{self.nonce}"
        )
        return payload.encode("utf-8")

    def sign_observation(self, secret_key: bytes) -> None:
        """Signs the sensory observation with node secret key."""
        self.signature = hmac.new(secret_key, self.canonical_bytes, hashlib.sha256).hexdigest()

    def verify_integrity(self, secret_key: bytes, max_skew_seconds: float = 5.0) -> bool:
        """Validates signature and checks for clock drift / replay attacks."""
        if not self.signature:
            return False
        
        # Check timestamp skew against system clock
        if abs(time.time() - self.timestamp) > max_skew_seconds:
            return False
            
        expected_sig = hmac.new(secret_key, self.canonical_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)
