from src.device_fabric.contracts import CapabilityLease, DeviceState, PhysicalSnapshot, AuthorizedActionIntent
from src.device_fabric.precondition_gate import PreconditionGate, PreconditionResult
from src.device_fabric.mocks.mock_tv import MockTVAdapter

def test_rejected_precondition_cannot_mutate_device():
    adapter=MockTVAdapter("tv_1")
    before=adapter.device.state.state_digest
    expected=adapter.device.state
    snapshot=PhysicalSnapshot(device_id="tv_1", state=expected, epoch=42, observed_at=1000.0)
    lease=CapabilityLease(device_id="tv_1", authorized_epoch=41, capabilities=frozenset({"set_volume"}))
    intent=AuthorizedActionIntent(device_id="tv_1", operation="set_volume", target_state=DeviceState(power=False, volume=99.0), expected_pre_state=expected)
    result=PreconditionGate().evaluate(intent, lease, snapshot)
    assert result == PreconditionResult.EPOCH_DRIFT
    assert adapter.device.state.state_digest == before
    assert adapter.device.state.volume == 10.0
