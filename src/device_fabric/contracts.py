import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeviceType(Enum):
    TV = "TV"
    SMART_SPEAKER = "SMART_SPEAKER"
    AV_RECEIVER = "AV_RECEIVER"


class ActuationStatus(Enum):
    PREPARED = "PREPARED"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFIED = "VERIFIED"
    ROLLED_BACK = "ROLLED_BACK"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    ROLLBACK_UNAVAILABLE = "ROLLBACK_UNAVAILABLE"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    VERIFICATION_MISMATCH = "VERIFICATION_MISMATCH"
    VERIFICATION_TIMEOUT = "VERIFICATION_TIMEOUT"
    CAPABILITY_REJECTED = "CAPABILITY_REJECTED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    DUPLICATE_ABSORBED = "DUPLICATE_ABSORBED"


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    device_type: DeviceType
    manufacturer: str
    model: str


@dataclass(frozen=True)
class DeviceCapabilities:
    volume_absolute: bool = True
    volume_delta: bool = True
    mute: bool = True
    power: bool = True
    input_select: bool = False
    max_volume_delta_db: float = 10.0
    min_volume_db: float = 0.0
    max_volume_db: float = 100.0

    @property
    def capability_digest(self) -> str:
        payload = {
            "volume_absolute": self.volume_absolute,
            "volume_delta": self.volume_delta,
            "mute": self.mute,
            "power": self.power,
            "input_select": self.input_select,
            "max_volume_delta_db": self.max_volume_delta_db,
            "min_volume_db": self.min_volume_db,
            "max_volume_db": self.max_volume_db,
        }
        raw_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DeviceState:
    power: bool
    volume: float
    muted: bool
    input_source: str = "HDMI_1"

    @property
    def state_digest(self) -> str:
        payload = {
            "power": self.power,
            "volume": round(float(self.volume), 2),
            "muted": self.muted,
            "input_source": self.input_source,
        }
        raw_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TransactionIdentity:
    action_id: str
    device_id: str
    intent_digest: str

    @property
    def transaction_digest(self) -> str:
        raw_string = f"{self.action_id}:{self.device_id}:{self.intent_digest}"
        return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ActuationReceipt:
    receipt_id: str
    action_id: str
    device_id: str
    intent_digest: str
    status: str  # ActuationStatus value or str string representation
    timestamp: float = field(default_factory=time.time)
    transaction_digest: Optional[str] = None
    capability_digest: Optional[str] = None
    pre_state_digest: Optional[str] = None
    post_state_digest: Optional[str] = None
    fabric_sequence: Optional[int] = None


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    expected_state: DeviceState
    observed_state: DeviceState
    error_message: Optional[str] = None
    transaction_digest: Optional[str] = None
    verification_digest: Optional[str] = None
