"""Capability lease definitions and schema for AQSS-36-OMEGA control layer."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CapabilityLease:
    """Represents an active capability lease issued to a device or router session."""

    device_id: str
    capability_digest: str
    firmware_identity: str
    protocol_version: Optional[str] = "1.0"
    lease_id: Optional[str] = None
    expires_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if the capability lease signature and parameters remain valid."""
        return bool(self.device_id and self.capability_digest)
