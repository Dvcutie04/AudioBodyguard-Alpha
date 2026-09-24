from datetime import datetime, timezone, timedelta
from src.device_fabric.contracts import CapabilityLease, DeviceState, PhysicalSnapshot, AuthorizedActionIntent
from src.device_fabric.precondition_gate import PreconditionGate, PreconditionResult
from src.device_fabric.physical_commit_gate import PhysicalCommitGate
from src.device_fabric.mocks.mock_tv import MockTVAdapter

class CountingAdapter:
    def __init__(self):
        self.calls=0
        self.adapter=MockTVAdapter("tv_1")

    async def execute_intent(self, intent, *args, **kwargs):
        self.calls += 1
        return await self.adapter.execute_intent(intent, *args, **kwargs)

def make_valid_case():
    adapter=CountingAdapter()
    state=adapter.adapter.device.state
    now=datetime.now(timezone.utc)
    snapshot=PhysicalSnapshot(device_id="tv_1", state=state, epoch=42, observed_at=now.timestamp())
    lease=CapabilityLease(device_id="tv_1", authorized_epoch=42, capabilities=frozenset({"set_volume"}), valid_from=now-timedelta(seconds=1), expires_at=now+timedelta(seconds=30), max_world_state_age_ms=5000)
    intent=AuthorizedActionIntent(device_id="tv_1", operation="set_volume", target_state=DeviceState(power=False, volume=55.0), expected_pre_state=state, deadline_at=now.timestamp()+10)
    return adapter, intent, lease, snapshot

def test_valid_preconditions_allow_commit_path():
    adapter, intent, lease, snapshot=make_valid_case()
    result=PreconditionGate().evaluate(intent, lease, snapshot)
    assert result == PreconditionResult.ALLOW

import pytest

@pytest.mark.asyncio
async def test_valid_precondition_calls_adapter_once_and_executes():
    adapter, intent, lease, snapshot=make_valid_case()
    result=await PhysicalCommitGate().commit(intent, lease, snapshot, adapter)
    assert result.status.name == "EXECUTED"
    assert adapter.calls == 1
    assert adapter.adapter.device.state.volume == 55.0

@pytest.mark.asyncio
async def test_rejected_precondition_never_calls_adapter():
    adapter, intent, lease, snapshot=make_valid_case()
    snapshot.epoch=43
    result=await PhysicalCommitGate().commit(intent, lease, snapshot, adapter)
    assert result == PreconditionResult.EPOCH_DRIFT
    assert adapter.calls == 0
    assert adapter.adapter.device.state.volume == 10.0

@pytest.mark.asyncio
async def test_capability_denied_never_calls_adapter():
    adapter, intent, lease, snapshot=make_valid_case()
    lease.capabilities=frozenset()
    result=await PhysicalCommitGate().commit(intent, lease, snapshot, adapter)
    assert result == PreconditionResult.CAPABILITY_DENIED
    assert adapter.calls == 0
    assert adapter.adapter.device.state.volume == 10.0

@pytest.mark.asyncio
async def test_expired_authorization_never_calls_adapter():
    adapter, intent, lease, snapshot=make_valid_case()
    lease.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    result=await PhysicalCommitGate().commit(intent, lease, snapshot, adapter)
    assert result == PreconditionResult.AUTH_EXPIRED
    assert adapter.calls == 0
    assert adapter.adapter.device.state.volume == 10.0

@pytest.mark.asyncio
async def test_expired_intent_never_calls_adapter():
    adapter, intent, lease, snapshot=make_valid_case()
    intent.deadline_at=datetime.now(timezone.utc).timestamp()-1
    result=await PhysicalCommitGate().commit(intent, lease, snapshot, adapter)
    assert result == PreconditionResult.INTENT_EXPIRED
    assert adapter.calls == 0
    assert adapter.adapter.device.state.volume == 10.0

@pytest.mark.asyncio
async def test_device_mismatch_never_calls_adapter():
    adapter, intent, lease, snapshot=make_valid_case()
    snapshot.device_id="tv_wrong"
    result=await PhysicalCommitGate().commit(intent, lease, snapshot, adapter)
    assert result == PreconditionResult.DEVICE_MISMATCH
    assert adapter.calls == 0
    assert adapter.adapter.device.state.volume == 10.0


@pytest.mark.asyncio
async def test_naive_valid_from_never_calls_adapter():
    adapter,intent,lease,snapshot=make_valid_case()
    lease.valid_from=datetime(1970,1,1,0,0,0)
    result=await PhysicalCommitGate().commit(intent,lease,snapshot,adapter)
    assert result == PreconditionResult.AUTH_EXPIRED
    assert adapter.calls == 0
    assert adapter.adapter.device.state.volume == 10.0


@pytest.mark.asyncio
async def test_naive_expires_at_never_calls_adapter():
    adapter,intent,lease,snapshot=make_valid_case()
    lease.expires_at=datetime(2999,1,1,0,0,0)
    result=await PhysicalCommitGate().commit(intent,lease,snapshot,adapter)
    assert result == PreconditionResult.AUTH_EXPIRED
    assert adapter.calls == 0
    assert adapter.adapter.device.state.volume == 10.0


@pytest.mark.asyncio
async def test_controller_handoff_during_preconditions_never_reaches_adapter():
    from src.control.active_controller_lease import ActiveControllerLeaseAuthority
    authority=ActiveControllerLeaseAuthority()
    first=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    adapter,intent,lease,snapshot=make_valid_case()
    class HandoffPreconditionGate:
        def evaluate(self,candidate,physical_lease,physical_snapshot):
            authority.handoff(current_lease=first,next_controller_id="phone-b",now=101.0,ttl_seconds=30.0)
            return PreconditionResult.ALLOW
    gate=PhysicalCommitGate(precondition_gate=HandoffPreconditionGate(),controller_authority=authority,controller_lease=first,controller_now=102.0)
    result=await gate.commit(intent,lease,snapshot,adapter)
    assert result is PreconditionResult.CONTROLLER_FENCE_STALE
    assert adapter.calls==0
    assert adapter.adapter.device.state.volume==10.0


@pytest.mark.asyncio
async def test_active_controller_fence_reaches_adapter_once():
    from src.control.active_controller_lease import ActiveControllerLeaseAuthority
    authority=ActiveControllerLeaseAuthority()
    active=authority.acquire(resource_id="tv:living-room",controller_id="phone-a",now=100.0,ttl_seconds=30.0)
    adapter,intent,lease,snapshot=make_valid_case()
    result=await PhysicalCommitGate(controller_authority=authority,controller_lease=active,controller_now=101.0).commit(intent,lease,snapshot,adapter)
    assert result.status.name=="EXECUTED"
    assert adapter.calls==1
    assert adapter.adapter.device.state.volume==55.0


@pytest.mark.asyncio
async def test_incomplete_controller_fence_context_never_reaches_adapter():
    from src.control.active_controller_lease import ActiveControllerLeaseAuthority
    authority=ActiveControllerLeaseAuthority()
    adapter,intent,lease,snapshot=make_valid_case()
    result=await PhysicalCommitGate(controller_authority=authority).commit(intent,lease,snapshot,adapter)
    assert result is PreconditionResult.CONTROLLER_FENCE_STALE
    assert adapter.calls==0
    assert adapter.adapter.device.state.volume==10.0
