from datetime import datetime, timezone

from src.device_fabric.contracts import DeviceState, PhysicalSnapshot
from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot


def test_world_state_evidence_converts_to_physical_snapshot_without_authority():
    world=WorldStateSnapshot(
        target_id="tv_integration_node_1",
        epoch=51,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={
            "power": True,
            "volume": 23.0,
            "muted": False,
            "input_source": "HDMI1",
            "channel": "7",
            "custom_state": {"room":"living"},
        },
        evidence_digest="sha256:world-state-adapter-evidence",
    )

    physical=to_physical_snapshot(world)

    assert isinstance(physical, PhysicalSnapshot)
    assert isinstance(physical.state, DeviceState)
    assert physical.device_id==world.target_id
    assert physical.epoch==world.epoch
    assert physical.observed_at==world.observed_at.timestamp()
    assert physical.state.power is True
    assert physical.state.volume==23.0
    assert physical.state.muted is False
    assert physical.state.input_source=="HDMI1"
    assert physical.state.channel=="7"
    assert physical.state.custom_state=={"room":"living"}
    assert physical.evidence_digest == ""
    assert not hasattr(physical,"capabilities")
    assert not hasattr(physical,"authorization_digest")


def test_predicted_world_state_cannot_convert_to_physical_snapshot():
    import pytest
    from datetime import datetime,timezone
    from src.verification.world_state import WorldStateSnapshot,to_physical_snapshot
    world=WorldStateSnapshot(target_id="tv_integration_node_1",epoch=51,observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),state={"power":True,"volume":23.0},evidence_digest="sha256:predicted-state",provenance="PREDICTED")
    with pytest.raises(ValueError,match="observed"):
        to_physical_snapshot(world)
