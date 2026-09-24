from datetime import datetime, timedelta, timezone

from src.verification.world_state import (
    WorldStateSnapshot,
    require_fresh_world_state,
    require_world_state_epoch,
    require_world_state_preconditions,
 )


def test_world_state_physical_truth_gates_compose_on_valid_snapshot():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=50,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":"on","volume":10},
        evidence_digest="sha256:composed-truth-evidence",
    )

    result=require_fresh_world_state(
        snapshot,
        now=datetime(2026,9,3,12,0,4,tzinfo=timezone.utc),
        max_age=timedelta(seconds=5),
    )
    result=require_world_state_epoch(result, expected_epoch=50)
    result=require_world_state_preconditions(
        result,
        required={"power":"on","volume":10},
    )

    assert result is snapshot
