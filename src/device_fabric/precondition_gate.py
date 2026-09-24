import time
import math
from enum import Enum, auto

class PreconditionResult(Enum):
    ALLOW = auto()
    DEVICE_MISMATCH = auto()
    CAPABILITY_DENIED = auto()
    EPOCH_DRIFT = auto()
    PRECONDITION_DRIFT = auto()
    AUTH_EXPIRED = auto()
    INTENT_EXPIRED = auto()
    WORLD_STATE_STALE = auto()
    CONTROLLER_FENCE_STALE = auto()
    ADAPTIVE_PROPOSAL_INVALID = auto()
    ADAPTIVE_ACTION_MISMATCH = auto()

class PreconditionGate:
    def evaluate(self, intent, lease, snapshot):
        if intent.device_id != lease.device_id or intent.device_id != snapshot.device_id:
            return PreconditionResult.DEVICE_MISMATCH
        if not lease.permits(intent.operation):
            return PreconditionResult.CAPABILITY_DENIED
        if lease.valid_from is not None and (lease.valid_from.tzinfo is None or lease.valid_from.utcoffset() is None):
            return PreconditionResult.AUTH_EXPIRED
        if lease.expires_at is not None and (lease.expires_at.tzinfo is None or lease.expires_at.utcoffset() is None):
            return PreconditionResult.AUTH_EXPIRED
        now = time.time()
        if lease.valid_from is not None and now < lease.valid_from.timestamp():
            return PreconditionResult.AUTH_EXPIRED
        if lease.expires_at is not None and now >= lease.expires_at.timestamp():
            return PreconditionResult.AUTH_EXPIRED
        if intent.deadline_at and now >= intent.deadline_at:
            return PreconditionResult.INTENT_EXPIRED
        if lease.authorized_epoch != snapshot.epoch:
            return PreconditionResult.EPOCH_DRIFT
        if not math.isfinite(snapshot.observed_at):
            return PreconditionResult.WORLD_STATE_STALE
        if lease.max_clock_skew_ms > 0 and (snapshot.observed_at - now) * 1000.0 > lease.max_clock_skew_ms:
            return PreconditionResult.WORLD_STATE_STALE
        if lease.max_world_state_age_ms > 0 and (now - snapshot.observed_at) * 1000.0 > lease.max_world_state_age_ms:
            return PreconditionResult.WORLD_STATE_STALE
        if intent.expected_pre_state is None:
            return PreconditionResult.PRECONDITION_DRIFT
        if intent.expected_pre_state.state_digest != snapshot.state_digest:
            return PreconditionResult.PRECONDITION_DRIFT
        return PreconditionResult.ALLOW
