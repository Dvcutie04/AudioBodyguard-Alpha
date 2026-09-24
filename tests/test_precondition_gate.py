from src.device_fabric.contracts import CapabilityLease, DeviceState, PhysicalSnapshot, AuthorizedActionIntent

def test_matching_epoch_and_digest_permit_commit():
    state=DeviceState(power=True, volume=25.0)
    snapshot=PhysicalSnapshot(device_id="tv_1", state=state, epoch=42, observed_at=1000.0)
    lease=CapabilityLease(device_id="tv_1", authorized_epoch=42, capabilities=frozenset({"set_volume"}))
    intent=AuthorizedActionIntent(device_id="tv_1", operation="set_volume", expected_pre_state=state)
    assert lease.authorized_epoch == snapshot.epoch
    assert intent.expected_pre_state.state_digest == snapshot.state_digest

def test_epoch_drift_blocks_commit():
    state=DeviceState(power=True, volume=25.0)
    snapshot=PhysicalSnapshot(device_id="tv_1", state=state, epoch=43, observed_at=1001.0)
    lease=CapabilityLease(device_id="tv_1", authorized_epoch=42, capabilities=frozenset({"set_volume"}))
    assert lease.authorized_epoch != snapshot.epoch

def test_state_digest_drift_blocks_commit():
    expected=DeviceState(power=True, volume=25.0)
    current=DeviceState(power=True, volume=30.0)
    snapshot=PhysicalSnapshot(device_id="tv_1", state=current, epoch=42, observed_at=1001.0)
    intent=AuthorizedActionIntent(device_id="tv_1", operation="set_volume", expected_pre_state=expected)
    assert intent.expected_pre_state.state_digest != snapshot.state_digest
