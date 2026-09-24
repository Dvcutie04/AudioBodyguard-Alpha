from datetime import datetime, timezone, timedelta
from src.device_fabric.contracts import CapabilityLease, DeviceState, PhysicalSnapshot, AuthorizedActionIntent
from src.device_fabric.precondition_gate import PreconditionGate, PreconditionResult

def make_case():
    state=DeviceState(power=True, volume=25.0)
    now=datetime.now(timezone.utc)
    snapshot=PhysicalSnapshot(device_id="tv_1", state=state, epoch=42, observed_at=now.timestamp())
    lease=CapabilityLease(device_id="tv_1", authorized_epoch=42, capabilities=frozenset({"set_volume"}), valid_from=now-timedelta(seconds=1), expires_at=now+timedelta(seconds=30), max_world_state_age_ms=5000)
    intent=AuthorizedActionIntent(device_id="tv_1", operation="set_volume", expected_pre_state=state, deadline_at=now.timestamp()+10)
    return intent, lease, snapshot

def test_expired_lease_rejects():
    intent, lease, snapshot=make_case()
    lease.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    assert PreconditionGate().evaluate(intent, lease, snapshot) == PreconditionResult.AUTH_EXPIRED

def test_expired_intent_rejects():
    intent, lease, snapshot=make_case()
    intent.deadline_at=datetime.now(timezone.utc).timestamp()-1
    assert PreconditionGate().evaluate(intent, lease, snapshot) == PreconditionResult.INTENT_EXPIRED

def test_stale_world_state_rejects():
    intent, lease, snapshot=make_case()
    snapshot.observed_at=datetime.now(timezone.utc).timestamp()-10
    assert PreconditionGate().evaluate(intent, lease, snapshot) == PreconditionResult.WORLD_STATE_STALE


def test_precondition_gate_rejects_naive_valid_from():
    from datetime import datetime,timezone
    from src.device_fabric.contracts import CapabilityLease,DeviceState,PhysicalSnapshot
    from src.device_fabric.precondition_gate import PreconditionGate,PreconditionResult
    class Intent:
        device_id="tv_1"
        operation="set_volume"
        deadline_at=0.0
        expected_pre_state=DeviceState()
    lease=CapabilityLease(device_id="tv_1",authorized_epoch=42,capabilities=frozenset({"set_volume"}),valid_from=datetime(1970,1,1,0,0,0))
    snapshot=PhysicalSnapshot(device_id="tv_1",state=Intent.expected_pre_state,epoch=42,observed_at=__import__("time").time())
    result=PreconditionGate().evaluate(Intent(),lease,snapshot)
    assert result is not PreconditionResult.ALLOW


def test_precondition_gate_rejects_naive_expires_at():
    from datetime import datetime
    from src.device_fabric.contracts import CapabilityLease,DeviceState,PhysicalSnapshot
    from src.device_fabric.precondition_gate import PreconditionGate,PreconditionResult
    class Intent:
        device_id="tv_1"
        operation="set_volume"
        deadline_at=0.0
        expected_pre_state=DeviceState()
    lease=CapabilityLease(device_id="tv_1",authorized_epoch=42,capabilities=frozenset({"set_volume"}),expires_at=datetime(2999,1,1,0,0,0))
    snapshot=PhysicalSnapshot(device_id="tv_1",state=Intent.expected_pre_state,epoch=42,observed_at=__import__("time").time())
    result=PreconditionGate().evaluate(Intent(),lease,snapshot)
    assert result is not PreconditionResult.ALLOW


def test_precondition_gate_rejects_reversed_validity_interval():
    from datetime import datetime,timezone
    from src.device_fabric.contracts import CapabilityLease,DeviceState,PhysicalSnapshot
    from src.device_fabric.precondition_gate import PreconditionGate,PreconditionResult
    class Intent:
        device_id="tv_1"
        operation="set_volume"
        deadline_at=0.0
        expected_pre_state=DeviceState()
    lease=CapabilityLease(device_id="tv_1",authorized_epoch=42,capabilities=frozenset({"set_volume"}),valid_from=datetime.fromtimestamp(300.0,timezone.utc),expires_at=datetime.fromtimestamp(200.0,timezone.utc))
    snapshot=PhysicalSnapshot(device_id="tv_1",state=Intent.expected_pre_state,epoch=42,observed_at=__import__("time").time())
    result=PreconditionGate().evaluate(Intent(),lease,snapshot)
    assert result is PreconditionResult.AUTH_EXPIRED


def test_precondition_gate_rejects_future_reversed_validity_interval():
    from datetime import datetime,timezone,timedelta
    from src.device_fabric.contracts import CapabilityLease,DeviceState,PhysicalSnapshot
    from src.device_fabric.precondition_gate import PreconditionGate,PreconditionResult
    class Intent:
        device_id="tv_1"
        operation="set_volume"
        deadline_at=0.0
        expected_pre_state=DeviceState()
    now=datetime.now(timezone.utc)
    lease=CapabilityLease(device_id="tv_1",authorized_epoch=42,capabilities=frozenset({"set_volume"}),valid_from=now+timedelta(seconds=20),expires_at=now+timedelta(seconds=10))
    snapshot=PhysicalSnapshot(device_id="tv_1",state=Intent.expected_pre_state,epoch=42,observed_at=__import__("time").time())
    result=PreconditionGate().evaluate(Intent(),lease,snapshot)
    assert result is PreconditionResult.AUTH_EXPIRED
