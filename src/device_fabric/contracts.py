import time
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional, Dict, Any


class DeviceType(Enum):
    SMART_TV = "SMART_TV"
    SPEAKER = "SPEAKER"
    THERMOSTAT = "THERMOSTAT"
    LIGHT = "LIGHT"
    GENERIC = "GENERIC"


class ActuationStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class TransactionState(Enum):
    PRECONDITION_CHECK = 1
    EXECUTING = 2
    EXECUTED = 3
    VERIFYING = 4
    VERIFIED = 5
    FAILED_PRECONDITION = 6
    FAILED_EXECUTION = 7
    FAILED_VERIFICATION = 8
    FAILED_CAPABILITY = 9
    ROLLED_BACK = 10
    RECOVERY_REQUIRED = 11
    FAILED_DRIFT = 12
    COMMITTED = 13


class VerificationStatus(Enum):
    VERIFIED = "VERIFIED"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class PreconditionStatus(Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    TIMEOUT = "TIMEOUT"


class ContractViolation(Exception):
    """Raised when a device fabric contract invariant is violated."""
    pass


@dataclass
class DeviceIdentity:
    device_id: str
    device_type: DeviceType = DeviceType.SMART_TV
    firmware_version: str = "1.0.0"


@dataclass
class DeviceState:
    power: bool = True
    volume: float = 50.0
    input_source: str = "HDMI_1"


@dataclass
class ObservedState:
    state: DeviceState
    timestamp: float = field(default_factory=time.time)
    raw_payload: Optional[Dict[str, Any]] = None


@dataclass
class PredictedState:
    predicted_state: DeviceState
    confidence: float = 1.0
    timestamp: float = 0.0


@dataclass
class CommittedState:
    state: DeviceState
    commit_timestamp: float = field(default_factory=time.time)
    commit_hash: Optional[str] = None


@dataclass
class AuthorizedActionIntent:
    intent_id: str
    device_id: str
    operation: str
    expected_pre_state: DeviceState
    target_state: DeviceState
    authorization_digest: str
    nonce: str


@dataclass
class CapabilityLease:
    device_id: str
    lease_id: str
    subject_id: str
    capabilities: FrozenSet[str]
    authorization_digest: str
    firmware_identity: str
    protocol_version: str
    nonce: str
    expires_at: float = 0.0

    def __post_init__(self):
        if not self.nonce:
            raise ContractViolation("Capability lease requires nonce for replay protection")


@dataclass
class VerificationResult:
    status: VerificationStatus
    details: Optional[str] = None
    verified: bool = False


@dataclass
class CommitCertificate:
    verification_result: VerificationResult
    observed_state_digest: Optional[str] = None

    def __post_init__(self):
        if (
            self.verification_result.status == VerificationStatus.VERIFIED
            and not self.observed_state_digest
        ):
            raise ContractViolation("Verified commit requires observed state digest")


@dataclass
class ActuationReceipt:
    receipt_id: str
    device_id: str
    success: bool
    status: ActuationStatus = ActuationStatus.SUCCESS
    applied_state: Optional[DeviceState] = None
    execution_time_ms: float = 0.0
    details: Optional[str] = None


def verify_epoch_lock(epoch_lock: str, current_epoch: int) -> bool:
    """Verifies that the provided epoch lock matches current system epoch."""
    if not epoch_lock:
        return False
    try:
        return int(epoch_lock) == current_epoch
    except (ValueError, TypeError):
        return str(epoch_lock) == str(current_epoch)
