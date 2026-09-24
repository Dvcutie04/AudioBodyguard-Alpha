from datetime import datetime, timedelta, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot, WorldStateStaleError, require_fresh_world_state


def test_world_state_freshness_boundary_is_inclusive():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=45,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":"on"},
        evidence_digest="sha256:boundary-evidence",
    )

    max_age=timedelta(seconds=5)

    result=require_fresh_world_state(
        snapshot,
        now=datetime(2026,9,3,12,0,5,tzinfo=timezone.utc),
        max_age=max_age,
    )
    assert result is snapshot

    with pytest.raises(WorldStateStaleError):
        require_fresh_world_state(
            snapshot,
            now=datetime(2026,9,3,12,0,5,1,tzinfo=timezone.utc),
            max_age=max_age,
        )
