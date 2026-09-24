from src.control.authorized_intent import SignedActionIntent
import pytest

from src.control.device_fabric_bridge import Gen3DeviceFabricBridge,PhysicalCommitRejected
from src.device_fabric.contracts import DeviceState


def _intent(operation,parameters):
    return SignedActionIntent(intent_id="intent-media-1",device_id="living-room-tv",operation=operation,parameters=parameters,issuer_id="issuer-1",policy_digest="policy-1",capability_lease_digest="lease-1",created_at=100.0,expires_at=101.0,nonce="nonce-1",transaction_id="transaction-1",protocol_version="1")


def test_bridge_translates_playback_position_to_digest_bound_target_state():
    before=DeviceState(power=True,volume=17.0,playback_position_seconds=3.0)
    intent=_intent("SET_PLAYBACK_POSITION",{"playback_position_seconds":45.0,"evidence_digest":"f"*64,"segment_start_seconds":0.0,"segment_end_seconds":45.0})
    target=Gen3DeviceFabricBridge._translate_state(None,intent,before)
    assert target.playback_position_seconds==45.0
    assert target.power is True
    assert target.volume==17.0
    assert target.state_digest!=before.state_digest


def test_unrelated_bridge_operation_preserves_playback_position():
    before=DeviceState(power=True,volume=17.0,playback_position_seconds=12.5)
    intent=_intent("SET_VOLUME",{"volume":10.0})
    target=Gen3DeviceFabricBridge._translate_state(None,intent,before)
    assert target.volume==10.0
    assert target.playback_position_seconds==12.5

@pytest.mark.parametrize("value",(True,-0.1,float("nan"),float("inf"),"45",None))
def test_invalid_playback_position_is_rejected_before_target_state(value):
    before=DeviceState(power=True,playback_position_seconds=3.0)
    intent=_intent("SET_PLAYBACK_POSITION",{"playback_position_seconds":value})
    with pytest.raises(PhysicalCommitRejected):
        Gen3DeviceFabricBridge._translate_state(None,intent,before)


@pytest.mark.parametrize("value",(3.0,2.9))
def test_non_forward_playback_position_is_rejected(value):
    before=DeviceState(power=True,playback_position_seconds=3.0)
    intent=_intent("SET_PLAYBACK_POSITION",{"playback_position_seconds":value})
    with pytest.raises(PhysicalCommitRejected):
        Gen3DeviceFabricBridge._translate_state(None,intent,before)

@pytest.mark.parametrize("parameters",(
    {"playback_position_seconds":45.0,"segment_end_seconds":45.0},
    {"playback_position_seconds":45.0,"segment_start_seconds":0.0},
    {"playback_position_seconds":45.0,"segment_start_seconds":45.0,"segment_end_seconds":45.0},
    {"playback_position_seconds":45.0,"segment_start_seconds":True,"segment_end_seconds":45.0},
))
def test_playback_requires_valid_signed_segment_bounds(parameters):
    intent=_intent("SET_PLAYBACK_POSITION",parameters)
    with pytest.raises(PhysicalCommitRejected,match="Invalid playback evidence segment"):
        Gen3DeviceFabricBridge._translate_state(None,intent,DeviceState(playback_position_seconds=3.0))


def test_playback_target_must_equal_signed_segment_end():
    intent=_intent("SET_PLAYBACK_POSITION",{"playback_position_seconds":44.0,"segment_start_seconds":0.0,"segment_end_seconds":45.0})
    with pytest.raises(PhysicalCommitRejected,match="PLAYBACK_TARGET_EVIDENCE_MISMATCH"):
        Gen3DeviceFabricBridge._translate_state(None,intent,DeviceState(playback_position_seconds=3.0))

