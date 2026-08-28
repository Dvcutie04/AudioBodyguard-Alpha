"""
Authorized Intent Module

Defines signed action intent structures and authorization payloads passing
from the Safety Governor to the Physical Commit Layer / Action Dispatcher.
"""

import time
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class SignedActionIntent:
    intent_id: str
    device_id: str = "default_device"
    operation: str = "NOOP"
    issuer_id: str = "governor_v1"
    parameters: Dict[str, Any] = field(default_factory=dict)
    epoch: int = 0
    expires_at: float = field(default_factory=lambda: time.time() + 60.0)
    created_at: float = field(default_factory=time.time)
    nonce: str = "00000000"
    transaction_id: str = "tx_0000"
    protocol_version: str = "1.0"
    policy_digest: str = ""
    capability_lease_digest: str = ""
    signature: Optional[str] = None
    authorization_digest: Optional[str] = None

    # Compatibility aliases for legacy or lightweight integration code
    target: str = field(init=False)
    action: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "target", self.device_id)
        object.__setattr__(self, "action", self.operation)

    @property
    def canonical_bytes(self) -> bytes:
        """Returns the canonical payload string for cryptographic HMAC verification."""
        payload = (
            f"{self.intent_id}:{self.device_id}:{self.operation}:{self.epoch}:"
            f"{self.expires_at}:{self.nonce}:{self.transaction_id}"
        )
        return payload.encode("utf-8")

    def is_expired(self) -> bool:
        """Checks if the intent authorization has surpassed its expiration timestamp."""
        return time.time() > self.expires_at

    def verify_signature(self, secret_key: bytes) -> bool:
        """Verifies the HMAC signature of the authorized intent."""
        if not self.signature:
            return False
        
        expected_sig = hmac.new(secret_key, self.canonical_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)


# Class alias to maintain full compatibility across ActionDispatcher and firewall tests
AuthorizedIntent = SignedActionIntent
