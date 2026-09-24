import json
import hashlib
from dataclasses import dataclass


@dataclass
class SignedCapabilityLease:
    device_id: str
    capability_digest: str
    firmware_identity: str
    protocol_version: str
    issued_at: float
    expires_at: float
    nonce: str
    issuer_id: str
    signature: str = ""

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "device_id": self.device_id,
            "capability_digest": self.capability_digest,
            "firmware_identity": self.firmware_identity,
            "protocol_version": self.protocol_version,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "issuer_id": self.issuer_id,
        }
        return json.dumps(payload, sort_keys=True).encode("utf-8")

    @property
    def payload_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()
