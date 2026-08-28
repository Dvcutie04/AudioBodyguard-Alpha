from dataclasses import dataclass
from typing import Dict, Any
from .canonical import canonicalize

@dataclass(frozen=True)
class SignedActionIntent:
    intent_id: str
    device_id: str
    operation: str
    parameters: Dict[str, Any]
    issuer_id: str
    policy_digest: str
    capability_lease_digest: str
    created_at: float
    expires_at: float
    nonce: str
    transaction_id: str
    protocol_version: str
    signature: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Returns the dictionary representation explicitly omitting the signature."""
        return {
            "intent_id": self.intent_id,
            "device_id": self.device_id,
            "operation": self.operation,
            "parameters": self.parameters,
            "issuer_id": self.issuer_id,
            "policy_digest": self.policy_digest,
            "capability_lease_digest": self.capability_lease_digest,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "transaction_id": self.transaction_id,
            "protocol_version": self.protocol_version
        }
        
    @property
    def canonical_bytes(self) -> bytes:
        """Returns the canonical byte sequence for verification."""
        return canonicalize(self.to_dict())
