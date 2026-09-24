from src.device_fabric.contracts import DeviceState
from src.device_fabric.mocks.mock_tv import MockTV


def test_playback_position_is_digest_bound_physical_state():
    before=DeviceState(power=True,playback_position_seconds=0.0)
    after=DeviceState(power=True,playback_position_seconds=45.0)
    assert before.playback_position_seconds==0.0
    assert after.playback_position_seconds==45.0
    assert before.state_digest!=after.state_digest


def test_mock_tv_declares_playback_position_capability():
    tv=MockTV(device_id="living-room-tv")
    assert "set_playback_position" in tv.capabilities.capabilities
    assert tv.state.playback_position_seconds==0.0
