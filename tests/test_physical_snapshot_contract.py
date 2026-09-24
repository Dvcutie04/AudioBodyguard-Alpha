from src.device_fabric.contracts import DeviceState, PhysicalSnapshot

def test_snapshot_captures_physical_identity_epoch_and_observation():
    state=DeviceState(power=True, volume=25.0, muted=False, input_source="HDMI_2")
    s=PhysicalSnapshot(device_id="tv_1", state=state, epoch=42, observed_at=1000.0)
    assert s.device_id == "tv_1"
    assert s.state_digest == state.state_digest
    assert s.epoch == 42
    assert s.observed_at == 1000.0

def test_snapshot_digest_changes_when_state_changes():
    a=DeviceState(power=True, volume=25.0)
    b=DeviceState(power=True, volume=30.0)
    sa=PhysicalSnapshot(device_id="tv_1", state=a, epoch=42, observed_at=1000.0)
    sb=PhysicalSnapshot(device_id="tv_1", state=b, epoch=43, observed_at=1001.0)
    assert sa.state_digest != sb.state_digest

def test_state_drift_requires_epoch_and_digest_match():
    expected=DeviceState(power=True, volume=25.0)
    current=PhysicalSnapshot(device_id="tv_1", state=expected, epoch=42, observed_at=1000.0)
    assert current.epoch == 42 and current.state_digest == expected.state_digest
    drifted_state=DeviceState(power=True, volume=30.0)
    assert current.state_digest != drifted_state.state_digest
    assert current.epoch != 43
