from datetime import datetime, timezone

import pytest

from src.verification.world_state import WorldStateSnapshot


def test_world_state_snapshot_rejects_invalid_evidence_envelope():
    cases=(
        {"target_id":"","state":{"power":"on"},"evidence_digest":"sha256:test"},
        {"target_id":"   ","state":{"power":"on"},"evidence_digest":"sha256:test"},
        {"target_id":123,"state":{"power":"on"},"evidence_digest":"sha256:test"},
        {"target_id":"living_room_tv","state":["power","on"],"evidence_digest":"sha256:test"},
        {"target_id":"living_room_tv","state":{"power":"on"},"evidence_digest":""},
        {"target_id":"living_room_tv","state":{"power":"on"},"evidence_digest":"   "},
        {"target_id":"living_room_tv","state":{"power":"on"},"evidence_digest":123},
    )

    for case in cases:
        with pytest.raises(ValueError):
            WorldStateSnapshot(
                target_id=case["target_id"],
                epoch=1,
                observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),
                state=case["state"],
                evidence_digest=case["evidence_digest"],
            )


def test_world_state_snapshot_rejects_invalid_provenance():
    for provenance in ("","   ",123,None):
        with pytest.raises(ValueError):
            WorldStateSnapshot(target_id="living_room_tv",epoch=1,observed_at=datetime(2026,9,3,12,0,0,tzinfo=timezone.utc),state={"power":"on"},evidence_digest="sha256:test",provenance=provenance)
