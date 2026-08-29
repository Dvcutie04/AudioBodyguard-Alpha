from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional


class ActuationStatus(Enum):
    PENDING = auto()
    EXECUTING = auto()
    COMMITTED = auto()
    REJECTED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    manufacturer: str
    model: str
    firmware_version: str
    hardware_revision: Optional[str] = None


@dataclass(frozen=True)
class CapabilityLease:
    lease_id: str
    device_id: str
    capability: str
    expires_at: float
    valid_from: Optional[datetime] = None
    granted_at: Optional[float] = None
    issuer: Optional[str] = None

    def is_valid(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if self.expires_at <= now:
            return False
        if self.valid_from is not None and self.valid_from.timestamp() > now:
            return False
        return True


@dataclass(frozen=True)
class DeviceState:
    power_state: str = "OFF"
    volume: int = 0
    muted: bool = False
    channel: int = 1
    input_source: str = "HDMI1"
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


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


@dataclass(frozen=True)
class CommittedState:
    power_state: str = "OFF"
    volume: int = 0
    muted: bool = False
    channel: int = 1
    input_source: str = "HDMI1"
    payload: Dict[str, Any] = field(default_factory=dict)
    committed_at: float = field(default_factory=time.time)
    commit_certificate: Optional[str] = None


@dataclass(frozen=True)
class VerificationResult:
    success: bool
    transaction_id: str = ""
    message: str = ""
    verified_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


def verify_epoch_lock(
    authorized_epoch: int,
    observed_epoch: int,
    *args,
    **kwargs,
) -> bool:
    """Verifies that the observed epoch matches the authorized epoch lock."""
    auth = kwargs.get("authorized_epoch", authorized_epoch)
    obs = kwargs.get("observed_epoch", observed_epoch)
    return auth == obs
