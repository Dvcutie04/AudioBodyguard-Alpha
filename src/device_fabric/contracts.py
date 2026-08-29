from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, Mapping, Optional, Sequence, Set


# ============================================================================
# Exceptions
# ============================================================================

class ContractViolation(ValueError):
    """Raised when a contract invariant or field validation fails."""
    pass


class EpochLockError(Exception):
    """Raised when an authorized epoch fails to match the observed epoch."""
    pass


class LeaseExpiredError(Exception):
    """Raised when attempting to operate on an expired capability lease."""
    pass


# ============================================================================
# Enumerations
# ============================================================================

class ActuationStatus(Enum):
    PENDING = auto()
    EXECUTING = auto()
    COMMITTED = auto()
    REJECTED = auto()
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


# ============================================================================
# Core Identity & Capabilities
# ============================================================================

@dataclass
class DeviceIdentity:
    device_id: str
    device_type: DeviceType = DeviceType.TV
    name: str = ""
    vendor: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = "1.0"
    hardware_revision: Optional[str] = None

    def __init__(
        self,
        device_id: str,
        device_type: DeviceType = DeviceType.TV,
        name: str = "",
        vendor: str = "",
        manufacturer: str = "",
        model: str = "",
        firmware_version: str = "1.0",
        hardware_revision: Optional[str] = None,
        **kwargs: Any,
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.name = name or device_id
        self.vendor = vendor or manufacturer
        self.manufacturer = manufacturer or vendor
        self.model = model
        self.firmware_version = firmware_version
        self.hardware_revision = hardware_revision


@dataclass(frozen=True)
class DeviceCapabilities:
    supported_actions: Sequence[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityLease:
    lease_id: str
    device_id: str = ""
    capability: str = ""
    subject_id: str = ""
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    expires_at: Any = None
    valid_from: Optional[Any] = None
    granted_at: Optional[float] = None
    issuer: Optional[str] = None
    authorized_epoch: int = 0
    max_world_state_age_ms: int = 5000
    max_clock_skew_ms: int = 2000
    nonce: str = ""

    def __init__(
        self,
        lease_id: str,
        device_id: str = "",
        capability: str = "",
        subject_id: str = "",
        capabilities: Any = None,
        expires_at: Any = None,
        valid_from: Optional[Any] = None,
        granted_at: Optional[float] = None,
        issuer: Optional[str] = None,
        authorized_epoch: int = 0,
        max_world_state_age_ms: int = 5000,
        max_clock_skew_ms: int = 2000,
        nonce: str = "",
        **kwargs: Any,
    ):
        self.lease_id = lease_id
        self.device_id = device_id
        self.capability = capability
        self.subject_id = subject_id
        if capabilities is not None:
            self.capabilities = frozenset(capabilities)
        else:
            self.capabilities = frozenset([capability]) if capability else frozenset()
        self.expires_at = expires_at
        self.valid_from = valid_from
        self.granted_at = granted_at
        self.issuer = issuer
        self.authorized_epoch = authorized_epoch
        self.max_world_state_age_ms = max_world_state_age_ms
        self.max_clock_skew_ms = max_clock_skew_ms
        self.nonce = nonce

    def is_valid(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        exp = self.expires_at
        if isinstance(exp, datetime):
            exp = exp.timestamp()
        if exp is not None and exp <= now:
            return False
        if self.valid_from is not None:
            vf = self.valid_from.timestamp() if isinstance(self.valid_from, datetime) else self.valid_from
            if vf > now:
                return False
        return True


# ============================================================================
# Device State & Serialization
# ============================================================================

@dataclass
class DeviceState:
    power_state: str = "OFF"
    power: bool = False
    volume: float = 0.0
    muted: bool = False
    channel: int = 1
    input_source: str = "HDMI1"
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        power_state: str = "OFF",
        power: Optional[bool] = None,
        volume: float = 0.0,
        muted: bool = False,
        channel: int = 1,
        input_source: str = "HDMI1",
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        if power is not None:
            self.power = power
            self.power_state = "ON" if power else "OFF"
        else:
            self.power_state = power_state
            self.power = power_state.upper() == "ON"
        self.volume = float(volume)
        self.muted = muted
        self.channel = channel
        self.input_source = input_source
        self.payload = payload if payload is not None else {}
        self.metadata = metadata if metadata is not None else {}

    @property
    def state_digest(self) -> str:
        """Deterministic SHA-256 state representation."""
        canonical_map = {
            "input_source": self.input_source,
            "muted": self.muted,
            "payload": self.payload,
            "power": self.power,
            "power_state": self.power_state,
            "volume": self.volume,
        }
        raw_bytes = json.dumps(canonical_map, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()


@dataclass(frozen=True)
class ObservedState(DeviceState):
    observed_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class PredictedState:
    power_state: str = "OFF"
    volume: int = 0
    muted: bool = False
    channel: int = 1
    input_source: str = "HDMI1"
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    predicted_at: float = field(default_factory=time.time)


# ============================================================================
# Transaction & Actuation Artifacts
# ============================================================================

@dataclass(frozen=True)
class AuthorizedActionIntent:
    intent_id: str
    device_id: str
    action: str
    capability_lease: CapabilityLease
    target_state: Dict[str, Any] = field(default_factory=dict)
    authorized_epoch: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ActuationReceipt:
    """Canonical 12-field physical actuation receipt."""
    receipt_id: str
    action_id: str
    device_id: str
    intent_digest: str
    status: ActuationStatus
    timestamp: float
    transaction_digest: str
    capability_digest: str
    pre_state_digest: str
    post_state_digest: str
    physical_state_digest: str
    executed_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class CommitCertificate:
    certificate_id: str
    transaction_id: str
    device_id: str
    committed_at: float = field(default_factory=time.time)
    signature: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# Compatibility alias for physical layer runtime
PhysicalCommitCertificate = CommitCertificate


@dataclass(frozen=True)
class CommittedState:
    power_state: str = "OFF"
    volume: int = 0
    muted: bool = False
    channel: int = 1
    input_source: str = "HDMI1"
    payload: Dict[str, Any] = field(default_factory=dict)
    committed_at: float = field(default_factory=time.time)
    commit_certificate: Optional[Any] = None


@dataclass(frozen=True)
class ReconciledState:
    committed_state: CommittedState
    observed_state: ObservedState
    reconciled_at: float = field(default_factory=time.time)
    invariants_held: bool = True


@dataclass(frozen=True)
class VerificationResult:
    success: bool
    transaction_id: str = ""
    message: str = ""
    status: VerificationStatus = VerificationStatus.VERIFIED
    verified_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Functions
# ============================================================================

def verify_epoch_lock(
    authorized_epoch: int = 0,
    observed_epoch: int = 0,
    *args: Any,
    **kwargs: Any,
) -> bool:
    """Verifies that the authorized epoch matches the observed state epoch."""
    auth = kwargs.get("authorized_epoch", authorized_epoch)
    obs = kwargs.get("observed_epoch", observed_epoch)
    return auth == obs
