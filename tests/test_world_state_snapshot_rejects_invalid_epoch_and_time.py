from datetime import datetime, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot


def test_world_state_snapshot_rejects_invalid_epoch_and_naive_time():
    cases=(
        {"epoch":-1,"observed_at":datetime(2026,9,3,12,0,0,tzinfo=timezone.utc)},
        {"epoch":1.5,"observed_at":datetime(2026,9,3,12,0,0,tzinfo=timezone.utc)},
        {"epoch":1,"observed_at":datetime(2026,9,3,12,0,0)},
    )

    for case in cases:
        with pytest.raises(ValueError):
            WorldStateSnapshot(
                target_id="living_room_tv",
                epoch=case["epoch"],
                observed_at=case["observed_at"],
                state={"power":"on"},
                evidence_digest="sha256:test-evidence",
            )
