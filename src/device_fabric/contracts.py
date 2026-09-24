from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, FrozenSet, Set, Union
from datetime import datetime
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

class ContractViolation(Exception):
    pass

class EpochLockError(Exception):
    pass

class LeaseExpiredError(Exception):
    pass

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
    playback_position_seconds: Union[int, float] = 0.0

    @property
    def state_digest(self) -> str:
        data = {"power": self.power, "volume": float(self.volume), "muted": self.muted, "input_source": self.input_source, "channel": self.channel, "custom_state": self.custom_state, "playback_position_seconds": float(self.playback_position_seconds)}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

@dataclass
class PhysicalSnapshot:
    device_id: str = ""
    state: DeviceState = field(default_factory=DeviceState)
    epoch: int = 0
    observed_at: float = 0.0
    evidence_digest: str = ""

    @property
    def state_digest(self) -> str:
        return self.state.state_digest

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
        if self.valid_from is not None and (self.valid_from.tzinfo is None or self.valid_from.utcoffset() is None):
            raise ValueError("valid_from must be timezone-aware")
        if self.expires_at is not None and (self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None):
            raise ValueError("expires_at must be timezone-aware")
        if self.valid_from is not None and self.expires_at is not None and self.valid_from >= self.expires_at:
            raise ValueError("capability lease validity window is invalid")
        data = {"lease_id": self.lease_id, "subject_id": self.subject_id, "object_id": self.object_id, "device_id": self.device_id, "authorized_epoch": self.authorized_epoch, "max_world_state_age_ms": self.max_world_state_age_ms, "max_clock_skew_ms": self.max_clock_skew_ms, "capabilities": sorted(self.capabilities), "granted_actions": sorted(self.granted_actions), "valid_from": None if self.valid_from is None else self.valid_from.timestamp(), "expires_at": None if self.expires_at is None else self.expires_at.timestamp(), "nonce": self.nonce}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

@dataclass
class ActuationReceipt:
    receipt_id: str = ""
    intent_id: str = ""
    device_id: str = ""
    status: ActuationStatus = ActuationStatus.COMMITTED
    timestamp: float = 0.0
    transaction_id: str = ""
    capability_digest: str = ""

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
    transaction_id: str = ""
    capability_digest: str = ""
    controller_resource_id: str = ""
    controller_id: str = ""
    controller_fencing_token: int = 0

@dataclass
class PhysicalVerificationRecord:
    intent_id: str = ""
    device_id: str = ""
    receipt_id: str = ""
    expected_state_digest: str = ""
    observed_state_digest: str = ""
    authorization_digest: str = ""
    transaction_id: str = ""
    capability_digest: str = ""
    world_state_evidence_digest: str = ""
    observed_state_evidence_digest: str = ""
    world_state_epoch: int = 0
    observed_state_epoch: Optional[int] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
