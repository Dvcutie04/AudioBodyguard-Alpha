from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class WorldStateSnapshot:
    target_id: str
    epoch: int
    observed_at: datetime
    state: Mapping[str, Any]
    evidence_digest: str
    provenance: str = "OBSERVED"

    def __post_init__(self) -> None:
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("epoch must be a non-negative integer")
        if not isinstance(self.observed_at, datetime):
            raise ValueError("observed_at must be a datetime")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if not isinstance(self.target_id, str) or not self.target_id.strip():
            raise ValueError("target_id must be a nonblank string")
        if not isinstance(self.state, Mapping):
            raise ValueError("state must be a mapping")
        if not isinstance(self.evidence_digest, str) or not self.evidence_digest.strip():
            raise ValueError("evidence_digest must be a nonblank string")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("provenance must be a nonblank string")
        object.__setattr__(self, "state", _freeze(self.state))

class WorldStateStaleError(ValueError):
    pass


def require_fresh_world_state(snapshot: WorldStateSnapshot, *, now: datetime, max_age) -> WorldStateSnapshot:
    if now - snapshot.observed_at > max_age:
        raise WorldStateStaleError("WORLD_STATE_STALE")
    return snapshot

class WorldStateEpochDriftError(ValueError):
    pass


def require_world_state_epoch(snapshot: WorldStateSnapshot, *, expected_epoch: int) -> WorldStateSnapshot:
    if snapshot.epoch != expected_epoch:
        raise WorldStateEpochDriftError("EPOCH_DRIFT")
    return snapshot

class WorldStatePreconditionDriftError(ValueError):
    pass


def require_world_state_preconditions(snapshot: WorldStateSnapshot, *, required: Mapping[str, Any]) -> WorldStateSnapshot:
    for key, expected in required.items():
        if key not in snapshot.state or snapshot.state[key] != expected:
            raise WorldStatePreconditionDriftError("PRECONDITION_DRIFT")
    return snapshot

def to_physical_snapshot(snapshot: WorldStateSnapshot):
    from src.device_fabric.contracts import DeviceState, PhysicalSnapshot

    if snapshot.provenance != "OBSERVED":
        raise ValueError("only observed world state may become a physical snapshot")

    state=DeviceState(
        power=snapshot.state.get("power", False),
        volume=snapshot.state.get("volume", 0.0),
        muted=snapshot.state.get("muted", False),
        input_source=snapshot.state.get("input_source", ""),
        channel=snapshot.state.get("channel", ""),
        custom_state=dict(snapshot.state.get("custom_state", {})),
    )
    return PhysicalSnapshot(
        device_id=snapshot.target_id,
        state=state,
        epoch=snapshot.epoch,
        observed_at=snapshot.observed_at.timestamp(),
    )
