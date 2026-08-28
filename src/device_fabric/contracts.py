@dataclass(frozen=True)
class CapabilityLease:
    """Represents a capability lease granting temporary access to device operations."""
    lease_id: str
    subject_id: str
    device_id: str
    capabilities: frozenset[str]
    valid_from: datetime
    expires_at: datetime
    authorized_epoch: int
    max_world_state_age_ms: int
    max_clock_skew_ms: int
    nonce: str
    lease_digest: str

    def __post_init__(self) -> None:
        if not self.lease_id:
            raise ContractViolation("lease_id required")
        if not self.subject_id:
            raise ContractViolation("subject_id required")
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not self.capabilities:
            raise ContractViolation("capabilities cannot be empty")
        if self.expires_at <= self.valid_from:
            raise ContractViolation("expires_at must be after valid_from")
        if not self.nonce:
            raise ContractViolation("nonce required")
