from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set
from enum import Enum
from copy import deepcopy
import hashlib
import json
import time

class RollbackScope(Enum):
    DEVICE = "device"
    MEDIA_SESSION = "media_session"
    ROOM = "room"
    GLOBAL = "global"

class RequestOrigin(Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"

@dataclass(frozen=True)
class EnvironmentSnapshot:
    snapshot_id: str
    parent_snapshot_id: Optional[str]
    sequence: int
    timestamp_ns: int
    device_state: Dict[str, Any]
    policy_state: Dict[str, Any]
    context_hash: str
    state_digest: str = ""

@dataclass(frozen=True)
class RollbackRequest:
    target_snapshot_id: str
    requested_by: RequestOrigin
    scope: RollbackScope
    source_event_id: str
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

class SnapshotHasher:
    @staticmethod
    def compute_digest(parent_digest: str, sequence: int, device_state: Dict[str, Any], policy_state: Dict[str, Any], context_hash: str) -> str:
        canonical_data = {
            "parent": parent_digest,
            "sequence": sequence,
            "device": device_state,
            "policy": policy_state,
            "context": context_hash
        }
        payload = json.dumps(canonical_data, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

class SnapshotStore:
    def __init__(self):
        self.snapshots: Dict[str, EnvironmentSnapshot] = {}

    def save(self, snapshot: EnvironmentSnapshot):
        self.snapshots[snapshot.snapshot_id] = snapshot

    def get(self, snapshot_id: str) -> Optional[EnvironmentSnapshot]:
        return self.snapshots.get(snapshot_id)

class CausalLineageValidator:
    def __init__(self, store: SnapshotStore):
        self.store = store

    def validate_lineage(self, target: EnvironmentSnapshot, current_snapshot: Optional[EnvironmentSnapshot]) -> bool:
        curr = target
        while curr:
            expected_digest = SnapshotHasher.compute_digest(
                parent_digest=curr.parent_snapshot_id or "0" * 64,
                sequence=curr.sequence,
                device_state=curr.device_state,
                policy_state=curr.policy_state,
                context_hash=curr.context_hash
            )
            if curr.state_digest != expected_digest:
                return False
            
            if not curr.parent_snapshot_id:
                break
            curr = self.store.get(curr.parent_snapshot_id)
            if not curr:
                return False
        return True

class RollbackValidator:
    def __init__(self, lineage_validator: CausalLineageValidator):
        self.lineage_validator = lineage_validator

    def validate(self, request: RollbackRequest, target: EnvironmentSnapshot, current: Optional[EnvironmentSnapshot]) -> bool:
        if not target or not current:
            return False
        if target.sequence >= current.sequence:
            return False
        if not self.lineage_validator.validate_lineage(target, current):
            return False
        return True

class EnvironmentalUndoManager:
    def __init__(self):
        self.store = SnapshotStore()
        self.lineage_validator = CausalLineageValidator(self.store)
        self.rollback_validator = RollbackValidator(self.lineage_validator)
        self.current_id: Optional[str] = None
        self.sequence_counter: int = 0

    def current_snapshot(self) -> Optional[EnvironmentSnapshot]:
        if not self.current_id:
            return None
        return self.store.get(self.current_id)

    def create_snapshot(self, device_state: Dict[str, Any], policy_state: Dict[str, Any], context_hash: str) -> EnvironmentSnapshot:
        parent = self.current_snapshot()
        parent_id = parent.snapshot_id if parent else None
        parent_digest = parent.state_digest if parent else "0" * 64
        
        self.sequence_counter += 1
        seq = self.sequence_counter
        
        safe_device = deepcopy(device_state)
        safe_policy = deepcopy(policy_state)
        
        state_dig = SnapshotHasher.compute_digest(parent_digest, seq, safe_device, safe_policy, context_hash)
        snapshot_id = f"snap_{seq:016x}"
        
        snapshot = EnvironmentSnapshot(
            snapshot_id=snapshot_id,
            parent_snapshot_id=parent_id,
            sequence=seq,
            timestamp_ns=time.time_ns(),
            device_state=safe_device,
            policy_state=safe_policy,
            context_hash=context_hash,
            state_digest=state_dig
        )
        
        self.store.save(snapshot)
        self.current_id = snapshot_id
        return snapshot
