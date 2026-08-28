from dataclasses import dataclass
from typing import Dict, Any
from .canonical import compute_digest, canonicalize

@dataclass(frozen=True)
class SignedCapabilityLease:
    device_id: str
    capability_digest: str
    firmware_identity: str
    protocol_version: str
    issued_at: float
    expires_at: float
    nonce: str
    issuer_id: str
    signature: str

    def to_dict(self) -> Dict[str, Any]:
        """Returns the dictionary representation explicitly omitting the signature."""
        return {
            "device_id": self.device_id,
            "capability_digest": self.capability_digest,
            "firmware_identity": self.firmware_identity,
            "protocol_version": self.protocol_version,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "issuer_id": self.issuer_id
        }
        
    @property
    def payload_digest(self) -> str:
        """Returns the SHA-256 digest of the canonical lease, used to bind Intents."""
        return compute_digest(self.to_dict())
        
    @property
    def canonical_bytes(self) -> bytes:
        """Returns the canonical byte sequence for verification."""
        return canonicalize(self.to_dict())
