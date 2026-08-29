from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional


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
class DeviceState:
    power: bool = True
    volume: float = 50.0
    input_source: str = "HDMI_1"


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
