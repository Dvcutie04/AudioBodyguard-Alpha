"""
AQSS-36-OMEGA
Physical Truth Runtime — Core Contracts
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from hashlib import sha256
from typing import Mapping, Optional, Any

# ---------------------------------------------------------------------------
# Contract infrastructure
# ---------------------------------------------------------------------------
class ContractViolation(ValueError):
    """Raised when a Physical Truth contract violates an invariant."""

def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)

def canonical_digest(*parts: object) -> str:
    """
    Produce a deterministic SHA-256 digest over contract material.
    """
    material = "|".join(repr(part) for part in parts)
    return sha256(material.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class DeviceType(Enum):
    TV = auto()
    AUDIO = auto()
    LIGHT = auto()
    CLIMATE = auto()
    SWITCH = auto()
    MEDIA_PLAYER = auto()
    GENERIC = auto()

class TransactionState(Enum):
    PENDING = auto()
    LEASE_VALIDATED = auto()
    SIMULATED = auto()
    PRECHECK_PASSED = auto()
    EXECUTING = auto()
    COMMITTED = auto()
    OBSERVING = auto()
    RECONCILING = auto()
    VERIFIED = auto()
    ROLLED_BACK = auto()
    RECOVERY_REQUIRED = auto()
    UNKNOWN_PHYSICAL_STATE = auto()
    PHYSICAL_DIVERGENCE = auto()

class PreconditionStatus(Enum):
    MATCH = auto()
    UNAVAILABLE = auto()
    MALFORMED = auto()
    STALE = auto()
    DRIFT = auto()

class ActuationStatus(Enum):
    EXECUTED = auto()
    DUPLICATE_ABSORBED = auto()
    ROLLED_BACK = auto()

class VerificationStatus(Enum):
    VERIFIED = auto()
    PRECONDITION_DRIFT = auto()
    STATE_EPOCH_MISMATCH = auto()
    LEASE_EXPIRED = auto()
    LEASE_NOT_YET_VALID = auto()
    CLOCK_SKEW_EXCEEDED = auto()
    UNCERTAINTY_EXCEEDED = auto()
    PHYSICAL_DIVERGENCE = auto()
    UNKNOWN_PHYSICAL_STATE = auto()
    DEVICE_MISMATCH = auto()
    OBSERVATION_STALE = auto()
    RECOVERY_REQUIRED = auto()

# ---------------------------------------------------------------------------
# Physical device state
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DeviceState:
    power: bool = False
    volume: float = 0.0
    input_source: str = "HDMI_1"
    payload: Optional[Mapping[str, object]] = None
    muted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.power, bool):
            raise ContractViolation("power must be bool")
        if self.volume < 0:
            raise ContractViolation("volume cannot be negative")
        if not self.input_source:
            raise ContractViolation("DeviceState requires input_source")
        if not isinstance(self.muted, bool):
            raise ContractViolation("muted must be bool")

    @property
    def state_digest(self) -> str:
        return canonical_digest(
            "DEVICE_STATE",
            self.power,
            self.volume,
            self.input_source,
            self.muted,
            self.payload,
        )

# ---------------------------------------------------------------------------
# Authorized action
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AuthorizedActionIntent:
    intent_id: str
    device_id: str
    operation: str
    target_state: DeviceState
    expected_pre_state: DeviceState
    authorization_digest: str
    deadline_at: float

    def __post_init__(self) -> None:
        if not self.intent_id:
            raise ContractViolation("intent_id required")
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not self.operation:
            raise ContractViolation("operation required")
        if not self.authorization_digest:
            raise ContractViolation("authorization_digest required")
        if self.deadline_at <= 0:
            raise ContractViolation("deadline_at must be strictly positive")

# ---------------------------------------------------------------------------
# Device identity and capabilities
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    device_type: DeviceType | str
    vendor: str
    model: str
    firmware_version: str

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not self.device_type:
            raise ContractViolation("device_type required")
        if not self.vendor:
            raise ContractViolation("vendor required")
        if not self.model:
            raise ContractViolation("model required")
        if not self.firmware_version:
            raise ContractViolation("firmware_version required")

@dataclass(frozen=True)
class DeviceCapabilities:
    device_id: str
    capabilities: frozenset[str]

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not isinstance(self.capabilities, frozenset):
            raise ContractViolation("capabilities must be a frozenset")

# ---------------------------------------------------------------------------
# Actuation receipt
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ActuationReceipt:
    receipt_id: str
    action_id: str
    device_id: str
    intent_digest: str
    status: ActuationStatus
    timestamp: datetime
    transaction_digest: str
    capability_digest: str
    pre_state_digest: str
    post_state_digest: str
    physical_state_digest: str
    executed_at: datetime

    def __post_init__(self) -> None:
        if not self.receipt_id:
            raise ContractViolation("receipt_id required")
        if not self.action_id:
            raise ContractViolation("action_id required")
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not self.intent_digest:
            raise ContractViolation("intent_digest required")
        if not self.transaction_digest:
            raise ContractViolation("transaction_digest required")
        if not self.capability_digest:
            raise ContractViolation("capability_digest required")
        if not self.pre_state_digest:
            raise ContractViolation("pre_state_digest required")
        if not self.post_state_digest:
            raise ContractViolation("post_state_digest required")
        if not self.physical_state_digest:
            raise ContractViolation("physical_state_digest required")
        if not isinstance(self.status, ActuationStatus):
            raise ContractViolation("status must be an ActuationStatus")
        if self.timestamp.tzinfo is None:
            raise ContractViolation("timestamp must be timezone-aware")
        if self.executed_at.tzinfo is None:
            raise ContractViolation("executed_at must be timezone-aware")
        if self.executed_at > self.timestamp:
            raise ContractViolation("executed_at cannot be later than receipt timestamp")

    @property
    def receipt_digest(self) -> str:
        return canonical_digest(
            "ACTUATION_RECEIPT",
            self.receipt_id,
            self.action_id,
            self.device_id,
            self.intent_digest,
            self.status.name,
            self.timestamp.isoformat(),
            self.transaction_digest,
            self.capability_digest,
            self.pre_state_digest,
            self.post_state_digest,
            self.physical_state_digest,
            self.executed_at.isoformat(),
        )

# ---------------------------------------------------------------------------
# Epistemic state representations
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PredictedState:
    device_id: str
    state: Mapping[str, object]
    model_id: str
    model_version: str
    confidence: float
    generated_at: datetime = field(default_factory=utc_now)
    world_epoch_reference: int = 0

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ContractViolation("PredictedState requires device_id")
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractViolation("confidence must be within [0.0, 1.0]")
        if self.world_epoch_reference < 0:
            raise ContractViolation("world_epoch_reference cannot be negative")

    @property
    def epistemic_class(self) -> str:
        return "PREDICTED"

@dataclass(frozen=True)
class ObservedState:
    device_id: str
    state: Mapping[str, object]
    observer_id: str
    observation_id: str
    observed_at: datetime
    world_epoch: int
    measurement_digest: str
    uncertainty: float

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ContractViolation("ObservedState requires device_id")
        if not self.observer_id:
            raise ContractViolation("ObservedState requires observer_id")
        if not self.observation_id:
            raise ContractViolation("ObservedState requires observation_id")
        if self.world_epoch < 0:
            raise ContractViolation("world_epoch cannot be negative")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ContractViolation("uncertainty must be within [0.0, 1.0]")
        if not self.measurement_digest:
            raise ContractViolation("ObservedState requires measurement_digest")

    @property
    def epistemic_class(self) -> str:
        return "OBSERVED"

@dataclass(frozen=True)
class CommittedState:
    device_id: str
    transaction_id: str
    requested_state: Mapping[str, object]
    authorized_epoch: int
    committed_at: datetime
    command_digest: str
    authorization_digest: str

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ContractViolation("CommittedState requires device_id")
        if not self.transaction_id:
            raise ContractViolation("CommittedState requires transaction_id")
        if self.authorized_epoch < 0:
            raise ContractViolation("authorized_epoch cannot be negative")
        if not self.command_digest:
            raise ContractViolation("CommittedState requires command_digest")
        if not self.authorization_digest:
            raise ContractViolation("CommittedState requires authorization_digest")

    @property
    def epistemic_class(self) -> str:
        return "COMMITTED"

@dataclass(frozen=True)
class ReconciledState:
    device_id: str
    transaction_id: str
    committed_state: CommittedState
    observed_state: ObservedState
    verified: bool
    divergence: bool
    reconciled_at: datetime = field(default_factory=utc_now)
    reconciliation_digest: str = ""

    def __post_init__(self) -> None:
        # Require observed_state to have epistemic_class == 'OBSERVED'
        if not hasattr(self.observed_state, "observer_id") or getattr(self.observed_state, "epistemic_class", "") != "OBSERVED":
            raise AttributeError("observed_state must be an ObservedState instance")
        if not isinstance(self.committed_state, CommittedState):
            raise ContractViolation("committed_state must be a CommittedState")
        if self.committed_state.device_id != self.device_id:
            raise ContractViolation("CommittedState device mismatch")
        if self.observed_state.device_id != self.device_id:
            raise ContractViolation("ObservedState device mismatch")
        if self.committed_state.transaction_id != self.transaction_id:
            raise ContractViolation("Transaction ID mismatch")
        if self.verified and self.divergence:
            raise ContractViolation("A divergent state cannot be verified")

    @property
    def epistemic_class(self) -> str:
        return "RECONCILED"

# ---------------------------------------------------------------------------
# Capability lease
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CapabilityLease:
    device_id: str
    lease_id: str = "lease_default"
    subject_id: str = "subj_default"
    capabilities: frozenset[str] = field(default_factory=frozenset)
    valid_from: Optional[datetime] = None
    expires_at: Optional[Any] = None
    authorized_epoch: int = 0
    max_world_state_age_ms: int = 5000
    max_clock_skew_ms: int = 1000
    nonce: str = "nonce_default"
    lease_digest: str = ""
    capability_digest: str = ""
    firmware_identity: str = ""
    protocol_version: str = ""
    issued_at: Optional[Any] = None
    issuer: str = ""

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ContractViolation("device_id required")

    def is_temporally_valid(self, now: Optional[datetime] = None) -> bool:
        if self.valid_from and isinstance(self.expires_at, datetime):
            now = now or utc_now()
            return self.valid_from <= now < self.expires_at
        return True

    def permits(self, capability: str) -> bool:
        return capability in self.capabilities

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    transaction_id: str
    authorized_epoch: int
    observed_epoch: Optional[int]
    uncertainty_total: float
    uncertainty_limit: float
    verified_at: datetime = field(default_factory=utc_now)
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.status == VerificationStatus.VERIFIED

@dataclass(frozen=True)
class PhysicalCommitCertificate:
    certificate_id: str
    transaction_id: str
    device_id: str
    intent_digest: str
    authorization_digest: str
    capability_lease_digest: str
    pre_state_digest: str
    simulation_digest: str
    authorized_epoch: int
    command_digest: str
    execution_timestamp: datetime
    observed_state_digest: Optional[str]
    verification: VerificationResult
    provenance_parent: Optional[str]
    certificate_digest: str = ""
    signer_id: Optional[str] = None
    signature: Optional[str] = None

    @property
    def physically_verified(self) -> bool:
        return self.verification.status == VerificationStatus.VERIFIED

def verify_epoch_lock(
    authorized_epoch: int,
    observed_epoch: int,
) -> VerificationResult:
    if authorized_epoch != observed_epoch:
        return VerificationResult(
            status=VerificationStatus.STATE_EPOCH_MISMATCH,
            transaction_id="UNKNOWN",
            authorized_epoch=authorized_epoch,
            observed_epoch=observed_epoch,
            uncertainty_total=1.0,
            uncertainty_limit=0.0,
            reason="Authorized physical epoch differs from observed physical epoch.",
        )
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        transaction_id="UNKNOWN",
        authorized_epoch=authorized_epoch,
        observed_epoch=observed_epoch,
        uncertainty_total=0.0,
        uncertainty_limit=0.0,
        reason="Physical state epoch lock satisfied.",
    )
