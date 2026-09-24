from datetime import datetime, timezone

from src.device_fabric.contracts import AuthorizedActionIntent, CapabilityLease, DeviceState
from src.device_fabric.precondition_gate import PreconditionGate, PreconditionResult
from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot


def test_world_state_conversion_preserves_precondition_drift_fail_closed_gate():
    world=WorldStateSnapshot(
        target_id="tv_integration_node_1",
        epoch=54,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":False,"volume":10.0,"muted":False,"input_source":"HDMI1","channel":"7","custom_state":{"room":"living"}},
        evidence_digest="sha256:converted-precondition-evidence",
    )
    snapshot=to_physical_snapshot(world)
    lease=CapabilityLease(
        device_id=world.target_id,
        capabilities={"set_volume"},
        authorized_epoch=54,
    )
    expected=DeviceState(
        power=False,
        volume=99.0,
        muted=False,
        input_source="HDMI1",
        channel="7",
        custom_state={"room":"living"},
    )
    intent=AuthorizedActionIntent(
        device_id=world.target_id,
        operation="set_volume",
        expected_pre_state=expected,
    )

    result=PreconditionGate().evaluate(intent,lease,snapshot)

    assert expected.state_digest!=snapshot.state_digest
    assert result==PreconditionResult.PRECONDITION_DRIFT
