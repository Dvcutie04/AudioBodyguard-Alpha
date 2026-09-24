from datetime import datetime, timedelta, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot, WorldStateStaleError, require_fresh_world_state


def test_world_state_stale_gate_fails_closed():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=44,
        observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
        state={"power":"on"},
        evidence_digest="sha256:freshness-evidence",
    )

    now=datetime(2026,9,3,12,0,6,tzinfo=timezone.utc)

    with pytest.raises(WorldStateStaleError):
        require_fresh_world_state(
            snapshot,
            now=now,
            max_age=timedelta(seconds=5),
        )
