from datetime import datetime, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot, WorldStateEpochDriftError, require_world_state_epoch


def test_world_state_epoch_drift_fails_closed():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=45,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":"on"},
        evidence_digest="sha256:epoch-evidence",
    )

    with pytest.raises(WorldStateEpochDriftError):
        require_world_state_epoch(snapshot, expected_epoch=46)
