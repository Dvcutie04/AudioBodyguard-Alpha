from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, FrozenSet, Set, Union
from datetime import datetime, timezone
import hashlib
import json


class ActuationStatus(Enum):
    PENDING = auto()
    EXECUTING = auto()
    EXECUTED = auto()
    DUPLICATE_ABSORBED = auto()
    COMMITTED = auto()
    REJECTED = auto()
    FAILED = auto()


class DeviceType(Enum):
    TV = "tv"
    SMART_HOME = "smart_home"
    AUDIO = "radio"
    GENERIC = "generic"


class VerificationStatus(Enum):
    PENDING = auto()
    VERIFIED = auto()
    FAILED = auto()
    FAILED_VERIFICATION = auto()


class PreconditionStatus(Enum):
    MATCH = auto()
    MISMATCH = auto()


class TransactionState(Enum):
    PRECONDITION_CHECK = auto()
    EXECUTING = auto()
    EXECUTED = auto()
    VERIFYING = auto()
    VERIFIED = auto()
    COMMITTED = auto()
    FAILED_CAPABILITY = auto()
    FAILED_PRECONDITION = auto()
    FAILED_EXECUTION = auto()
    FAILED_VERIFICATION = auto()
    ROLLED_BACK = auto()
    RECOVERY_REQUIRED = auto()


class ContractViolation(Exception):
    pass


class EpochLockError(Exception):
    pass


class LeaseExpiredError(Exception):
    pass


@dataclass
class VerificationResult:
    status: VerificationStatus = VerificationStatus.PENDING
    transaction_id: str = ""
    authorized_epoch: int = 0
    observed_epoch: int = 0
    uncertainty_total: float = 0.0
    uncertainty_limit: float = 0.1
    details: str = ""
    verified: bool = False


@dataclass
class CommitCertificate:
    transaction_id: str = ""
    lease_digest: str = ""
    timestamp: float = 0.0
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

    def __post_init__(self):
        if self.verification and self.verification.status == VerificationStatus.VERIFIED:
            if not self.observed_state_digest:
                raise ContractViolation("Verified commit requires observed state digest")


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


@dataclass
class ReconciledState:
    device_id: str = ""
    transaction_id: str = ""
    committed: Optional[CommittedState] = None
    observed: Optional[ObservedState] = None
    verified: bool = False
    divergence: bool = False

    def __post_init__(self):
        if self.verified and self.divergence:
            raise ContractViolation("divergent state cannot be verified")
        if self.observed and self.observed.device_id != self.device_id:
            raise ContractViolation("ObservedState device mismatch")


@dataclass
class DeviceIdentity:
    device_id: str = ""
    device_type: DeviceType = DeviceType.GENERIC
    name: str = ""
    vendor: str = ""


@dataclass
class DeviceState:
    power: bool = False
    volume: Union[int, float] = 0
    muted: bool = False
    input_source: str = ""
    channel: str = ""
    custom_state: Dict[str, Any] = field(default_factory=dict)

    @property
    def state_digest(self) -> str:
        data = {
            "power": self.power,
            "volume": float(self.volume),
            "muted": self.muted,
            "input_source": self.input_source,
            "channel": self.channel,
            "custom_state": self.custom_state,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@dataclass
class DeviceCapabilities:
    device_id: str = ""
    capabilities: Union[Set[str], List[str], FrozenSet[str]] = field(default_factory=set)
    supported_actions: List[str] = field(default_factory=list)


@dataclass
class CapabilityLease:
    lease_id: str = ""
    subject_id: str = ""
    object_id: str = ""
    device_id: str = ""
    capabilities: Union[FrozenSet[str], Set[str], List[str]] = field(default_factory=frozenset)
    granted_actions: List[str] = field(default_factory=list)
    valid_from: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    expiration_timestamp: float = 0.0
    authorized_epoch: int = 0
    max_world_state_age_ms: int = 0
    max_clock_skew_ms: int = 0
    nonce: str = ""

    def permits(self, action: str) -> bool:
        return action in self.capabilities or action in self.granted_actions

    @property
    def lease_digest(self) -> str:
        data = {
            "lease_id": self.lease_id,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "device_id": self.device_id,
            "authorized_epoch": self.authorized_epoch,
            "nonce": self.nonce,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@dataclass
class ActuationReceipt:
    receipt_id: str = ""
    intent_id: str = ""
    device_id: str = ""
    status: ActuationStatus = ActuationStatus.COMMITTED
    timestamp: float = 0.0


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


def verify_epoch_lock(authorized_epoch: int, observed_epoch: int) -> VerificationResult:
    if authorized_epoch != observed_epoch:
        return VerificationResult(
            status=VerificationStatus.FAILED_VERIFICATION,
            details="State epoch mismatch",
        )
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        authorized_epoch=authorized_epoch,
        observed_epoch=observed_epoch,
        verified=True,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
