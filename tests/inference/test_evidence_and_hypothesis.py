import pytest
from src.inference.evidence_envelope import EvidenceEnvelope


def test_evidence_envelope_creation():
    envelope = EvidenceEnvelope(
        source_id="mic_array_01",
        timestamp=1000.0,
        feature_vector={
            "f1": 0.5,
            "f2": 0.5,
            "f3": 0.5,
            "f4": 0.5,
            "f5": 0.5,
            "f6": 0.5,
            "f7": 0.5,
            "f8": 0.5,
        },
        quality_score=0.9,
    )
    assert envelope.source_id == "mic_array_01"
    assert envelope.timestamp == 1000.0
    assert len(envelope.feature_vector) == 8
    assert envelope.quality_score == 0.9
