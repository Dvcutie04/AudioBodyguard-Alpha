from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot


def test_world_state_snapshot_is_immutable_observed_reality():
    observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc)

    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=42,
        observed_at=observed_at,
        state={"power":"on","volume":10},
        evidence_digest="sha256:test-evidence",
    )

    assert snapshot.target_id=="living_room_tv"
    assert snapshot.epoch==42
    assert snapshot.observed_at==observed_at
    assert snapshot.state["power"]=="on"
    assert snapshot.state["volume"]==10
    assert snapshot.evidence_digest=="sha256:test-evidence"

    with pytest.raises(FrozenInstanceError):
        snapshot.epoch=43

    with pytest.raises(TypeError):
        snapshot.state["volume"]=99
