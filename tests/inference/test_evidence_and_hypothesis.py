def test_evidence_envelope_creation():
    envelope = EvidenceEnvelope(
        event_id="evt_001",
        sequence=1,
        source_id="mic_array_01",
        sensor_quality=0.9,
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
        change_point_evidence=None,
        posterior_before=0.5,
        posterior_after=0.6,
        timestamp=1000.0,
    )
    assert envelope.source_id == "mic_array_01"
    assert envelope.timestamp == 1000.0
    assert len(envelope.feature_vector) == 8
    assert envelope.sensor_quality == 0.9