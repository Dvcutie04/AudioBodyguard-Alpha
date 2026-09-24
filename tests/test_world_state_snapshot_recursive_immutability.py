from datetime import datetime, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot


def test_world_state_snapshot_state_is_recursively_immutable():
    snapshot=WorldStateSnapshot(
        target_id="living_room_tv",
        epoch=43,
        observed_at=datetime(2026,9,3,12,1,0,tzinfo=timezone.utc),
        state={
            "audio":{"volume":10,"modes":["movie","night"]},
            "flags":{"verified","local"},
        },
        evidence_digest="sha256:nested-evidence",
    )

    assert snapshot.state["audio"]["volume"]==10
    assert snapshot.state["audio"]["modes"]==("movie","night")
    assert snapshot.state["flags"]==frozenset({"verified","local"})

    with pytest.raises(TypeError):
        snapshot.state["audio"]["volume"]=99

    with pytest.raises(AttributeError):
        snapshot.state["audio"]["modes"].append("sports")

    with pytest.raises(AttributeError):
        snapshot.state["flags"].add("changed")
