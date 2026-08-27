from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional
import hashlib
import time
import uuid
import json

class TransactionState(Enum):
    PENDING = auto()
    LEASE_VALIDATED = auto()
    SIMULATED = auto()
    PRECHECK_PASSED = auto()
    EXECUTING = auto()
    COMMITTED = auto()
    
    # Terminal & Recovery States
    FAILED_VERIFICATION = auto()
    FAILED_DRIFT = auto()
    FAILED_CAPABILITY = auto()
    ROLLBACK_REQUIRED = auto()
    ROLLED_BACK = auto()
    RECOVERY_REQUIRED = auto()
    PHYSICAL_STATE_UNKNOWN = auto()

class PreconditionStatus(Enum):
    MATCH = auto()
    DRIFT = auto()
    STALE = auto()
    UNKNOWN = auto()
    MALFORMED = auto()
    UNAVAILABLE = auto()

@dataclass(frozen=True)
class DeviceState:
    device_id: str
    epoch: int
    payload: Dict[str, Any]
    observed_at: float = field(default_factory=time.time)
    firmware_identity: str = "unknown"
    
    @property
    def digest(self) -> str:
        canonical_payload = json.dumps(self.payload, sort_keys=True)
        data = f"{self.device_id}|{self.epoch}|{self.firmware_identity}|{canonical_payload}"
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass(frozen=True)
class CapabilityLease:
    device_id: str
    capability_digest: str
    firmware_identity: str
    protocol_version: str
    issued_at: float
    expires_at: float
    nonce: str
    issuer: str
    
    @property
    def lease_digest(self) -> str:
        data = f"{self.device_id}|{self.capability_digest}|{self.firmware_identity}|{self.nonce}"
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass(frozen=True)
class AuthorizedActionIntent:
    intent_id: str
    device_id: str
    operation: str
    target_state: DeviceState
    expected_pre_state: DeviceState
    authorization_digest: str
    deadline_at: float
    created_at: float = field(default_factory=time.time)

    @property
    def intent_digest(self) -> str:
        data = f"{self.intent_id}|{self.operation}|{self.target_state.digest}|{self.expected_pre_state.digest}"
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass(frozen=True)
class TransactionIdentity:
    intent_id: str
    device_id: str
    intent_digest: str
    capability_digest: str
    
    @property
    def tx_hash(self) -> str:
        data = f"{self.intent_id}|{self.device_id}|{self.intent_digest}|{self.capability_digest}"
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass(frozen=True)
class VerificationResult:
    transaction_id: str
    expected_state_digest: str
    observed_state_digest: str
    match: bool
    observation_epoch: int
    observed_at: float
    device_id: str
    verification_method: str
    failure_code: Optional[str] = None
    lineage_digest: Optional[str] = None
