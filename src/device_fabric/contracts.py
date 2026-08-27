from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional
import time


class DeviceType(Enum):
    TV = "TV"
    SMART_SPEAKER = "SMART_SPEAKER"
    AV_RECEIVER = "AV_RECEIVER"


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


@dataclass(frozen=True)
class DeviceState:
    power: bool
    volume: float
    muted: bool
    input_source: str = "HDMI_1"


@dataclass(frozen=True)
class ActuationReceipt:
    receipt_id: str
    action_id: str
    device_id: str
    intent_digest: str
    status: str  # "EXECUTED", "REJECTED", "FAILED"
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    expected_state: DeviceState
    observed_state: DeviceState
    error_message: Optional[str] = None
