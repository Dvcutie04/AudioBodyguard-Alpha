"""Capability lease definition and validation logic."""

from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Set


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
