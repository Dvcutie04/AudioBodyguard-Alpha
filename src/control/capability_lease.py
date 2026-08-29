"""Capability lease definition and validation logic."""

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional, Set


@dataclass
class CapabilityLease:
    """Represents a time-bound, cryptographically signed authorization lease."""

    device_id: str
    lease_id: str = ""
    subject_id: str = ""
    object_id: str = ""
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    authorization_digest: str = ""
    firmware_identity: str = ""
    protocol_version: str = "1.0"
    issued_at: float = 0.0
    expires_at: float = 0.0
    max_clock_skew_ms: int = 2000
    nonce: str = ""
    capability_digest: str = ""
    issuer: str = ""

    def is_valid_at(self, current_time: float) -> bool:
        """Check if the lease is valid at the given timestamp."""
        skew_sec = self.max_clock_skew_ms / 1000.0
        return (self.issued_at - skew_sec) <= current_time <= (self.expires_at + skew_sec)


@dataclass
class SignedCapabilityLease:
    """Represents a capability lease bundled with cryptographic signature metadata."""

    lease: CapabilityLease
    signature: str = ""
    signer_key_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
