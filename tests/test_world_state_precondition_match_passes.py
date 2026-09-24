from datetime import datetime, timezone

from src.verification.world_state import WorldStateSnapshot, require_world_state_preconditions


def test_world_state_matching_preconditions_return_original_snapshot():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=48,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":"on","volume":10},
        evidence_digest="sha256:precondition-match-evidence",
    )

    result=require_world_state_preconditions(
        snapshot,
        required={"power":"on","volume":10},
    )

    assert result is snapshot
