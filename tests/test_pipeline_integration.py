# Replace legacy DecisionEnvelope(...) instantiation inside tests/test_pipeline_integration.py

envelope = DecisionEnvelope(
    node_id="sensor_node_01",
    sequence_id=getattr(self, "sequence_counter", 1),
    trust_epoch=1,
    effective_trust=sensor_trust,
    trust_reason_codes=["HEALTHY"],
    evidence_digest="sha256_mock_digest",
    spatial_confidence=spatial_agreement,
    sensor_age=sensor_age,
    persistence_counter=persistence_counter,
    decision_state=decision_state,
)
