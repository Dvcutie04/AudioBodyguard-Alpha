from datetime import datetime, timezone

from src.verification.world_state import WorldStateSnapshot, require_world_state_epoch


def test_world_state_matching_epoch_returns_original_snapshot():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=46,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":"on"},
        evidence_digest="sha256:epoch-match-evidence",
    )

    result=require_world_state_epoch(snapshot, expected_epoch=46)

    assert result is snapshot
