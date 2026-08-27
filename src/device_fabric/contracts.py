import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

# --- LEGACY & BACKWARD COMPATIBILITY ENUMS ---
class DeviceType(Enum):
    TV = "TV"
    SPEAKER = "SPEAKER"
    LIGHT = "LIGHT"
    THERMOSTAT = "THERMOSTAT"
    UNKNOWN = "UNKNOWN"

class ActuationStatus(Enum):
    EXECUTED = "EXECUTED"
    DUPLICATE_ABSORBED = "DUPLICATE_ABSORBED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"

# --- PHASE 2.5 ENUMS ---
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


# --- DEVICE & STATE MODELS (MERGED) ---
@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    device_type: DeviceType
    manufacturer: str
    model: str
    firmware_version: str

@dataclass(frozen=True)
class DeviceCapabilities:
    capability_digest: str
    supported_commands: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class DeviceState:
    # Legacy fields for MockTVAdapter and current integration tests
    power: bool = False
    volume: float = 0.0
    muted: bool = False
    input_source: str = ""
    
    # Phase 2.5 Fields
    device_id: str = "unknown"
    epoch: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)
    observed_at: float = field(default_factory=time.time)
    firmware_identity: str = "unknown"
    
    @property
    def state_digest(self) -> str:
        # Legacy digest method
        data = f"{self.power}|{self.volume}|{self.muted}|{self.input_source}"
        return hashlib.sha256(data.encode()).hexdigest()

    @property
    def digest(self) -> str:
        # Phase 2.5 cryptographic digest
        canonical_payload = json.dumps(self.payload, sort_keys=True)
        data = f"{self.device_id}|{self.epoch}|{self.firmware_identity}|{canonical_payload}"
        return hashlib.sha256(data.encode()).hexdigest()


# --- TRANSACTION & LINEAGE MODELS ---
@dataclass(frozen=True)
class ActuationReceipt:
    receipt_id: str
    action_id: str
    device_id: str
    intent_digest: str
    status: str
    timestamp: float
    transaction_digest: str
    capability_digest: str
    pre_state_digest: str
    post_state_digest: str
    fabric_sequence: int

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
    # Phase 2.5 fields
    intent_id: str = ""
    device_id: str = ""
    intent_digest: str = ""
    capability_digest: str = ""
    
    # Legacy backward compatibility field
    action_id: str = ""
    
    @property
    def tx_hash(self) -> str:
        # Phase 2.5 identity hash
        data = f"{self.intent_id}|{self.device_id}|{self.intent_digest}|{self.capability_digest}"
        return hashlib.sha256(data.encode()).hexdigest()

    @property
    def transaction_digest(self) -> str:
        # Legacy backward compatibility for older router logic
        data = f"{self.action_id}|{self.device_id}|{self.intent_digest}"
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass(frozen=True)
class VerificationResult:
    # Legacy fields
    verified: bool = False
    expected_state: Optional[DeviceState] = None
    observed_state: Optional[DeviceState] = None
    error_message: Optional[str] = None
    transaction_digest: Optional[str] = None
    verification_digest: Optional[str] = None
    
    # Phase 2.5 fields
    transaction_id: str = ""
    expected_state_digest: str = ""
    observed_state_digest: str = ""
    match: bool = False
    observation_epoch: int = 0
    observed_at: float = field(default_factory=time.time)
    device_id: str = "unknown"
    verification_method: str = "unknown"
    failure_code: Optional[str] = None
    lineage_digest: Optional[str] = None
