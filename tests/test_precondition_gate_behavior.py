from src.device_fabric.contracts import CapabilityLease, DeviceState, PhysicalSnapshot, AuthorizedActionIntent
from src.device_fabric.precondition_gate import PreconditionGate, PreconditionResult

def make_case():
    state=DeviceState(power=True, volume=25.0)
    snapshot=PhysicalSnapshot(device_id="tv_1", state=state, epoch=42, observed_at=1000.0)
    lease=CapabilityLease(device_id="tv_1", authorized_epoch=42, capabilities=frozenset({"set_volume"}))
    intent=AuthorizedActionIntent(device_id="tv_1", operation="set_volume", expected_pre_state=state)
    return intent, lease, snapshot

def test_matching_preconditions_allow():
    intent, lease, snapshot=make_case()
    result=PreconditionGate().evaluate(intent, lease, snapshot)
    assert result == PreconditionResult.ALLOW

def test_wrong_device_rejects():
    intent, lease, snapshot=make_case()
    intent.device_id="tv_2"
    assert PreconditionGate().evaluate(intent, lease, snapshot) == PreconditionResult.DEVICE_MISMATCH

def test_missing_capability_rejects():
    intent, lease, snapshot=make_case()
    lease.capabilities=frozenset()
    assert PreconditionGate().evaluate(intent, lease, snapshot) == PreconditionResult.CAPABILITY_DENIED

def test_epoch_drift_rejects():
    intent, lease, snapshot=make_case()
    snapshot.epoch=43
    assert PreconditionGate().evaluate(intent, lease, snapshot) == PreconditionResult.EPOCH_DRIFT

def test_state_drift_rejects():
    intent, lease, snapshot=make_case()
    snapshot.state=DeviceState(power=True, volume=30.0)
    assert PreconditionGate().evaluate(intent, lease, snapshot) == PreconditionResult.PRECONDITION_DRIFT


def test_future_observation_beyond_clock_skew_rejects(monkeypatch):
    intent,lease,snapshot=make_case()
    lease.max_world_state_age_ms=5000
    lease.max_clock_skew_ms=2000
    snapshot.observed_at=1003.0
    monkeypatch.setattr("src.device_fabric.precondition_gate.time.time",lambda:1000.0)
    assert PreconditionGate().evaluate(intent,lease,snapshot)==PreconditionResult.WORLD_STATE_STALE


def test_nan_observed_at_rejects(monkeypatch):
    intent,lease,snapshot=make_case()
    lease.max_world_state_age_ms=5000
    lease.max_clock_skew_ms=2000
    snapshot.observed_at=float("nan")
    monkeypatch.setattr("src.device_fabric.precondition_gate.time.time",lambda:1000.0)
    assert PreconditionGate().evaluate(intent,lease,snapshot)==PreconditionResult.WORLD_STATE_STALE


def test_infinite_observed_at_rejects(monkeypatch):
    monkeypatch.setattr("src.device_fabric.precondition_gate.time.time",lambda:1000.0)
    for observed_at in (float("inf"),float("-inf")):
        intent,lease,snapshot=make_case()
        lease.max_world_state_age_ms=5000
        lease.max_clock_skew_ms=2000
        snapshot.observed_at=observed_at
        assert PreconditionGate().evaluate(intent,lease,snapshot)==PreconditionResult.WORLD_STATE_STALE


def test_future_observation_at_exact_clock_skew_boundary_allows(monkeypatch):
    intent,lease,snapshot=make_case()
    lease.max_world_state_age_ms=5000
    lease.max_clock_skew_ms=2000
    snapshot.observed_at=1002.0
    monkeypatch.setattr("src.device_fabric.precondition_gate.time.time",lambda:1000.0)
    assert PreconditionGate().evaluate(intent,lease,snapshot)==PreconditionResult.ALLOW
