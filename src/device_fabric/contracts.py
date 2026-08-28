from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from hashlib import sha256
from typing import Mapping, Optional

class ContractViolation(ValueError):
    """Raised when a Physical Truth contract violates an invariant."""

@dataclass(frozen=True)
class DeviceState:
    """Strongly typed representation of physical device state."""
    power: bool
    volume: float
    input_source: str
    payload: Optional[Mapping[str, object]] = None

    def __post_init__(self) -> None:
        if not self.input_source:
            raise ContractViolation("DeviceState requires input_source")
        if self.volume < 0:
            raise ContractViolation("volume cannot be negative")

@dataclass(frozen=True)
class AuthorizedActionIntent:
    """An intent that has passed the Safety Governor and is ready for the Commit Layer."""
    intent_id: str
    device_id: str
    operation: str
    target_state: DeviceState
    expected_pre_state: DeviceState
    authorization_digest: str
    deadline_at: float

    def __post_init__(self) -> None:
        if not self.intent_id:
            raise ContractViolation("intent_id required")
        if not self.device_id:
            raise ContractViolation("device_id required")
        if not self.operation:
            raise ContractViolation("operation required")
        if not self.authorization_digest:
            raise ContractViolation("authorization_digest required")
        if self.deadline_at <= 0:
            raise ContractViolation("deadline_at must be strictly positive")

# ... (rest of the file continues with TransactionState, PredictedState, etc.)
