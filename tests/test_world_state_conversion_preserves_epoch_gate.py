from datetime import datetime, timezone

from src.device_fabric.contracts import AuthorizedActionIntent, CapabilityLease
from src.device_fabric.precondition_gate import PreconditionGate, PreconditionResult
from src.verification.world_state import WorldStateSnapshot, to_physical_snapshot


def test_world_state_conversion_preserves_epoch_drift_fail_closed_gate():
    world=WorldStateSnapshot(
        target_id="tv_integration_node_1",
        epoch=53,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":False,"volume":10.0,"muted":False,"input_source":"","channel":"","custom_state":{}},
        evidence_digest="sha256:converted-epoch-evidence",
    )
    snapshot=to_physical_snapshot(world)
    lease=CapabilityLease(
        device_id=world.target_id,
        capabilities={"set_volume"},
        authorized_epoch=54,
    )
    intent=AuthorizedActionIntent(
        device_id=world.target_id,
        operation="set_volume",
        expected_pre_state=snapshot.state,
    )

    result=PreconditionGate().evaluate(intent,lease,snapshot)

    assert result==PreconditionResult.EPOCH_DRIFT
