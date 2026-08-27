import pytest
from src.inference.bayesian_adapter import ChangePointEvidence
from src.inference.evidence_envelope import EvidenceEnvelope


def test_evidence_envelope_creation():
    envelope = EvidenceEnvelope(
        event_id="evt_test",
        sequence=1,
        source_id="node_1",
        sensor_quality=1.0,
        feature_vector=[0.5] * 8,
        change_point_evidence=ChangePointEvidence(),
        posterior_before=0.1,
        posterior_after=0.2,
    )
    assert envelope.event_id == "evt_test"
    assert envelope.sequence == 1
    assert envelope.source_id == "node_1"
