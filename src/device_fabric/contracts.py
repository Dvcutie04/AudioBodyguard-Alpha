from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, List, Optional, Set, Union
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
def _timestamp(value: Any) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    return float(value)
class ContractViolation(Exception):
    """Raised when a Physical Truth contract violates an invariant."""
class EpochLockError(Exception):
    """Raised when authorized and observed physical epochs diverge."""
class LeaseExpiredError(Exception):
    """Raised when a capability lease is temporally invalid."""
class ActuationStatus(Enum):
    PENDING = auto()
    EXECUTING = auto()
    EXECUTED = auto()
    DUPLICATE_ABSORBED = auto()
    COMMITTED = auto()
    REJECTED = auto()
    ROLLED_BACK = auto()
    FAILED = auto()
class DeviceType(Enum):
    TV = "tv"
    SMART_HOME = "smart_home"
    AUDIO = "audio"
    GENERIC = "generic"
class VerificationStatus(Enum):
    PENDING = auto()
    VERIFIED = auto()
    FAILED = auto()
    FAILED_VERIFICATION = auto()
    STATE_EPOCH_MISMATCH = auto()
    PRECONDITION_DRIFT = auto()
    LEASE_EXPIRED = auto()
    LEASE_NOT_YET_VALID = auto()
    CLOCK_SKEW_EXCEEDED = auto()
    UNCERTAINTY_EXCEEDED = auto()
    PHYSICAL_DIVERGENCE = auto()
    UNKNOWN_PHYSICAL_STATE = auto()
    DEVICE_MISMATCH = auto()
    OBSERVATION_STALE = auto()
    RECOVERY_REQUIRED = auto()
class PreconditionStatus(Enum):
    MATCH = auto()
    MISMATCH = auto()
    UNAVAILABLE = auto()
    MALFORMED = auto()
    STALE = auto()
    DRIFT = auto()
class TransactionState(Enum):
    PENDING = auto()
    PRECONDITION_CHECK = auto()
    LEASE_VALIDATED = auto()
    SIMULATED = auto()
    PRECHECK_PASSED = auto()
    EXECUTING = auto()
    EXECUTED = auto()
    VERIFYING = auto()
    OBSERVING = auto()
    RECONCILING = auto()
    VERIFIED = auto()
    COMMITTED = auto()
    FAILED_CAPABILITY = auto()
    FAILED_PRECONDITION = auto()
    FAILED_EXECUTION = auto()
    FAILED_VERIFICATION = auto()
    ROLLED_BACK = auto()
    RECOVERY_REQUIRED = auto()
    UNKNOWN_PHYSICAL_STATE = auto()
    PHYSICAL_DIVERGENCE = auto()
@dataclass
class VerificationResult:
    status: VerificationStatus = VerificationStatus.PENDING
    transaction_id: str = ""
    authorized_epoch: int = 0
    observed_epoch: Optional[int] = None
    uncertainty_total: float = 0.0
    uncertainty_limit: float = 0.1
    details: str = ""
    verified: bool = False
    allowed: bool = False
    verified_at: datetime = field(default_factory=utc_now)
    def __post_init__(self) -> None:
        if self.authorized_epoch < 0:
            raise ContractViolation(
                "authorized_epoch cannot be negative"
            )
        if self.observed_epoch is not None and self.observed_epoch < 0:
            raise ContractViolation(
                "observed_epoch cannot be negative"
            )
        if not 0.0 <= self.uncertainty_total <= 1.0:
            raise ContractViolation(
                "uncertainty_total must be within [0.0, 1.0]"
            )
        if not 0.0 <= self.uncertainty_limit <= 1.0:
            raise ContractViolation(
                "uncertainty_limit must be within [0.0, 1.0]"
            )
    @property
    def success(self) -> bool:
        return self.status == VerificationStatus.VERIFIED
    @property
    def reason(self) -> str:
        return self.details
@dataclass
class DeviceIdentity:
    device_id: str = ""
    device_type: DeviceType = DeviceType.GENERIC
    name: str = ""
    vendor: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    hardware_revision: Optional[str] = None
    def __post_init__(self) -> None:
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not self.name:
            self.name = self.device_id
        if not self.vendor and self.manufacturer:
            self.vendor = self.manufacturer
        if not self.manufacturer and self.vendor:
            self.manufacturer = self.vendor
@dataclass
class DeviceState:
    power: bool = False
    volume: Union[int, float] = 0
    muted: bool = False
    input_source: str = ""
    channel: Union[str, int] = ""
    custom_state: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if float(self.volume) < 0:
            raise ContractViolation("volume cannot be negative")
    @property
    def state_digest(self) -> str:
        data = {
            "power": self.power,
            "volume": float(self.volume),
            "muted": self.muted,
            "input_source": self.input_source,
            "channel": self.channel,
            "custom_state": self.custom_state,
            "payload": self.payload,
        }
        material = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()
@dataclass
class ObservedState:
    device_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    observation_id: str = ""
    observer_id: str = ""
    timestamp: Optional[datetime] = None
    observed_epoch: int = 0
    measurement_digest: str = ""
    uncertainty: float = 0.0
    epistemic_class: str = "OBSERVED"
    def __post_init__(self) -> None:
        if self.observed_epoch < 0:
            raise ContractViolation(
                "observed_epoch cannot be negative"
            )
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ContractViolation(
                "uncertainty must be within [0.0, 1.0]"
            )
@dataclass
class PredictedState:
    device_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    subject_id: str = ""
    object_id: str = ""
    confidence: float = 0.9
    timestamp: Optional[datetime] = None
    authorized_epoch: int = 0
    epistemic_class: str = "PREDICTED"
    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractViolation(
                "confidence must be within [0.0, 1.0]"
            )
        if self.authorized_epoch < 0:
            raise ContractViolation(
                "authorized_epoch cannot be negative"
            )
@dataclass
class CommittedState:
    device_id: str = ""
    transaction_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    authorized_epoch: int = 0
    timestamp: Optional[datetime] = None
    command_digest: str = ""
    authorization_digest: str = ""
    epistemic_class: str = "COMMITTED"
    def __post_init__(self) -> None:
        if self.authorized_epoch < 0:
            raise ContractViolation(
                "authorized_epoch cannot be negative"
            )
@dataclass
class ReconciledState:
    device_id: str = ""
    transaction_id: str = ""
    committed: Optional[CommittedState] = None
    observed: Optional[ObservedState] = None
    verified: bool = False
    divergence: bool = False
    def __post_init__(self) -> None:
        if self.committed is not None:
            if not isinstance(self.committed, CommittedState):
                raise ContractViolation(
                    "committed must be CommittedState"
                )
            if (
                self.device_id
                and self.committed.device_id
                and self.committed.device_id != self.device_id
            ):
                raise ContractViolation(
                    "CommittedState device mismatch"
                )
        if self.observed is not None:
            if not isinstance(self.observed, ObservedState):
                raise ContractViolation(
                    "observed must be ObservedState"
                )
            if (
                self.device_id
                and self.observed.device_id
                and self.observed.device_id != self.device_id
            ):
                raise ContractViolation(
                    "ObservedState device mismatch"
                )
        if self.verified and self.divergence:
            raise ContractViolation(
                "divergent state cannot be verified"
            )
@dataclass
class DeviceCapabilities:
    device_id: str = ""
    capabilities: Union[
        Set[str],
        List[str],
        FrozenSet[str]
    ] = field(default_factory=set)
    supported_actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
@dataclass
class CapabilityLease:
    lease_id: str = ""
    subject_id: str = ""
    object_id: str = ""
    device_id: str = ""
    capabilities: Union[
        FrozenSet[str],
        Set[str],
        List[str]
    ] = field(default_factory=frozenset)
    granted_actions: List[str] = field(default_factory=list)
    valid_from: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    expiration_timestamp: float = 0.0
    authorized_epoch: int = 0
    max_world_state_age_ms: int = 0
    max_clock_skew_ms: int = 0
    nonce: str = ""
    capability_digest: str = ""
    firmware_identity: str = ""
    authorization_digest: str = ""
    def __post_init__(self) -> None:
        if not self.lease_id:
            raise ContractViolation("lease_id required")
        if not self.nonce or not self.nonce.strip():
            raise ContractViolation(
                "Lease requires nonce for replay protection"
            )
        if self.authorized_epoch < 0:
            raise ContractViolation(
                "authorized_epoch cannot be negative"
            )
        if self.max_world_state_age_ms < 0:
            raise ContractViolation(
                "max_world_state_age_ms cannot be negative"
            )
        if self.max_clock_skew_ms < 0:
            raise ContractViolation(
                "max_clock_skew_ms cannot be negative"
            )
        if (
            self.valid_from is not None
            and self.expires_at is not None
            and self.expires_at <= self.valid_from
        ):
            raise ContractViolation(
                "expires_at must be later than valid_from"
            )
    def permits(self, action: str) -> bool:
        return (
            action in self.capabilities
            or action in self.granted_actions
        )
    def is_temporally_valid(
        self,
        now: Optional[datetime] = None,
    ) -> bool:
        current = now or utc_now()
        if self.valid_from is not None:
            if current < self.valid_from:
                return False
        if self.expires_at is not None:
            if current >= self.expires_at:
                return False
        if self.expiration_timestamp:
            if current.timestamp() >= self.expiration_timestamp:
                return False
        return True
    def is_valid(
        self,
        current_time: Optional[float] = None,
    ) -> bool:
        now = (
            current_time
            if current_time is not None
            else time.time()
        )
        if self.valid_from is not None:
            if _timestamp(self.valid_from) > now:
                return False
        if self.expires_at is not None:
            if _timestamp(self.expires_at) <= now:
                return False
        if self.expiration_timestamp:
            if self.expiration_timestamp <= now:
                return False
        return True
    @property
    def lease_digest(self) -> str:
        data = {
            "lease_id": self.lease_id,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "device_id": self.device_id,
            "capabilities": sorted(
                str(x) for x in self.capabilities
            ),
            "granted_actions": sorted(
                str(x) for x in self.granted_actions
            ),
            "authorized_epoch": self.authorized_epoch,
            "nonce": self.nonce,
        }
        material = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            material.encode("utf-8")
        ).hexdigest()
@dataclass
class AuthorizedActionIntent:
    intent_id: str = ""
    lease_id: str = ""
    action: str = ""
    device_id: str = ""
    operation: str = ""
    target_state: Optional[DeviceState] = None
    expected_pre_state: Optional[DeviceState] = None
    authorization_digest: str = ""
    deadline_at: float = 0.0
    nonce: str = ""
    capability_lease: Optional[CapabilityLease] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.intent_id:
            raise ContractViolation("intent_id required")
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not self.action and not self.operation:
            raise ContractViolation(
                "action or operation required"
            )
        if self.deadline_at < 0:
            raise ContractViolation(
                "deadline_at cannot be negative"
            )
@dataclass
class ActuationReceipt:
    receipt_id: str = ""
    intent_id: str = ""
    action_id: str = ""
    device_id: str = ""
    intent_digest: str = ""
    status: ActuationStatus = ActuationStatus.COMMITTED
    timestamp: float = field(default_factory=time.time)
    transaction_digest: str = ""
    capability_digest: str = ""
    pre_state_digest: str = ""
    post_state_digest: str = ""
    physical_state_digest: str = ""
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    def __post_init__(self) -> None:
        if self.executed_at is None:
            self.executed_at = datetime.fromtimestamp(
                self.timestamp,
                tz=timezone.utc,
            )
@dataclass
class CommitCertificate:
    transaction_id: str = ""
    lease_digest: str = ""
    timestamp: float = field(default_factory=time.time)
    signature: str = ""
    verification_result: Optional[VerificationResult] = None
    observed_state_digest: Optional[str] = None
@dataclass
class PhysicalCommitCertificate:
    certificate_id: str = ""
    transaction_id: str = ""
    device_id: str = ""
    intent_digest: str = ""
    authorization_digest: str = ""
    capability_lease_digest: str = ""
    pre_state_digest: str = ""
    simulation_digest: str = ""
    authorized_epoch: int = 0
    command_digest: str = ""
    execution_timestamp: Optional[datetime] = None
    observed_state_digest: Optional[str] = None
    verification: Optional[VerificationResult] = None
    provenance_parent: Optional[str] = None
    certificate_digest: str = ""
    signer_id: Optional[str] = None
    signature: Optional[str] = None
    def __post_init__(self) -> None:
        if self.authorized_epoch < 0:
            raise ContractViolation(
                "authorized_epoch cannot be negative"
            )
        if (
            self.verification is not None
            and self.verification.status
            == VerificationStatus.VERIFIED
            and not self.observed_state_digest
        ):
            raise ContractViolation(
                "Verified commit requires observed state digest"
            )
    @property
    def physically_verified(self) -> bool:
        return (
            self.verification is not None
            and self.verification.status
            == VerificationStatus.VERIFIED
        )
def verify_epoch_lock(
    authorized_epoch: int = 0,
    observed_epoch: int = 0,
    *args: Any,
    **kwargs: Any,
) -> VerificationResult:
    if "authorized_epoch" in kwargs:
        authorized_epoch = kwargs["authorized_epoch"]
    if "observed_epoch" in kwargs:
        observed_epoch = kwargs["observed_epoch"]
    if authorized_epoch != observed_epoch:
        return VerificationResult(
            status=VerificationStatus.STATE_EPOCH_MISMATCH,
            authorized_epoch=authorized_epoch,
            observed_epoch=observed_epoch,
            uncertainty_total=1.0,
            uncertainty_limit=0.0,
            details=(
                "Authorized physical epoch differs "
                "from observed physical epoch."
            ),
            verified=False,
            allowed=False,
        )
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        authorized_epoch=authorized_epoch,
        observed_epoch=observed_epoch,
        uncertainty_total=0.0,
        uncertainty_limit=0.0,
        details="Physical state epoch lock satisfied.",
        verified=True,
        allowed=True,
    )