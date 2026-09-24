from datetime import datetime, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot, WorldStatePreconditionDriftError, require_world_state_preconditions


def test_world_state_missing_required_precondition_fails_closed():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=49,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":"on"},
        evidence_digest="sha256:missing-precondition-evidence",
    )

    with pytest.raises(WorldStatePreconditionDriftError):
        require_world_state_preconditions(
            snapshot,
            required={"power":"on","volume":10},
        )
