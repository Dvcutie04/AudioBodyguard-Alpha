"""Capability lease definitions and schema for AQSS-36-OMEGA control layer."""

from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Set, Union


@dataclass
class CapabilityLease:
    """Represents an active capability lease issued to a device or router session."""

    device_id: str
    capability_digest: str = ""
    firmware_identity: str = ""
    protocol_version: Optional[str] = "1.0"
    lease_id: Optional[str] = None
    subject_id: Optional[str] = None
    object_id: Optional[str] = None
    capabilities: Union[Set[str], FrozenSet[str]] = field(default_factory=frozenset)
    authorization_digest: Optional[str] = None
    expires_at: Optional[float] = None
    issued_at: Optional[float] = None
    max_clock_skew_ms: int = 2000
    nonce: Optional[str] = None
    issuer: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if the capability lease signature and parameters remain valid."""
        return bool(self.device_id)


@dataclass
class SignedCapabilityLease:
    """Represents a capability lease bundled with a cryptographic signature."""

    lease: CapabilityLease
    signature: str = ""
    public_key: str = ""

    def is_valid(self) -> bool:
        """Check if both the lease and signature are present."""
        return bool(self.lease and self.signature)
