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
    target: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    epoch: int = 0
    expires_at: float = field(default_factory=lambda: time.time() + 60.0)
    signature: Optional[str] = None
    authorization_digest: Optional[str] = None

    def is_expired(self) -> bool:
        """Checks if the intent authorization has surpassed its expiration timestamp."""
        return time.time() > self.expires_at

    def verify_signature(self, secret_key: bytes) -> bool:
        """Verifies the HMAC signature of the authorized intent."""
        if not self.signature:
            return False
        
        payload = f"{self.intent_id}:{self.target}:{self.action}:{self.epoch}:{self.expires_at}".encode()
        expected_sig = hmac.new(secret_key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)


# Class alias to maintain full compatibility across ActionDispatcher and firewall tests
AuthorizedIntent = SignedActionIntent
