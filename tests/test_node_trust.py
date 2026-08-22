import pytest
from audio_engine.node_trust import NodeTrust, TrustEvaluator

def test_tamper_state_cannot_be_averaged_away():
    evaluator = TrustEvaluator(current_known_epoch=10)
    trust = NodeTrust(
        identity=1.0,
        freshness=1.0,
        acoustic_health=1.0,
        spatial_consistency=1.0,
        calibration=1.0,
        tamper_state=0.05,
        temporal_integrity=1.0,
        behavioral_stability=1.0,
        epoch=10
    )
    state, _, reasons = evaluator.evaluate(trust)
    assert state == "QUARANTINE"
    assert "TAMPER_DETECTED" in reasons

def test_identity_failure_rejected():
    evaluator = TrustEvaluator(current_known_epoch=1)
    trust = NodeTrust(
        identity=0.5,
        freshness=1.0,
        acoustic_health=1.0,
        spatial_consistency=1.0,
        calibration=1.0,
        tamper_state=1.0,
        temporal_integrity=1.0,
        behavioral_stability=1.0,
        epoch=1
    )
    state, _, reasons = evaluator.evaluate(trust)
    assert state == "REJECT"
    assert "IDENTITY_FAILURE" in reasons

def test_healthy_node_passes():
    evaluator = TrustEvaluator(current_known_epoch=42)
    trust = NodeTrust(
        identity=0.95,
        freshness=0.95,
        acoustic_health=0.90,
        spatial_consistency=0.95,
        calibration=0.90,
        tamper_state=0.95,
        temporal_integrity=0.95,
        behavioral_stability=0.90,
        epoch=42
    )
    state, effective_trust, reasons = evaluator.evaluate(trust)
    assert state == "TRUSTED"
    assert effective_trust >= 0.9
    assert "TRUST_HEALTHY" in reasons

def test_stale_epoch_rejected():
    evaluator = TrustEvaluator(current_known_epoch=15)
    trust = NodeTrust(
        identity=1.0, freshness=1.0, acoustic_health=1.0,
        spatial_consistency=1.0, calibration=1.0, tamper_state=1.0,
        temporal_integrity=1.0, behavioral_stability=1.0,
        epoch=14
    )
    state, _, reasons = evaluator.evaluate(trust)
    assert state == "REJECT"
    assert "STALE_EPOCH_REJECTED" in reasons

def test_future_epoch_advances():
    evaluator = TrustEvaluator(current_known_epoch=10)
    trust = NodeTrust(
        identity=1.0, freshness=1.0, acoustic_health=1.0,
        spatial_consistency=1.0, calibration=1.0, tamper_state=1.0,
        temporal_integrity=1.0, behavioral_stability=1.0,
        epoch=12
    )
    state, _, reasons = evaluator.evaluate(trust)
    assert state == "TRUSTED"
    assert evaluator.current_epoch == 12
    assert "EPOCH_ADVANCED" in reasons

def test_tamper_failure_precedes_composite_scoring():
    evaluator = TrustEvaluator(current_known_epoch=1)
    trust = NodeTrust(
        identity=1.0, freshness=0.1, acoustic_health=0.1,
        spatial_consistency=0.1, calibration=0.1, tamper_state=0.0,
        temporal_integrity=1.0, behavioral_stability=0.1,
        epoch=1
    )
    state, _, reasons = evaluator.evaluate(trust)
    assert state == "QUARANTINE"
    assert "TAMPER_DETECTED" in reasons

def test_trust_score_is_bounded_0_to_1():
    evaluator = TrustEvaluator(current_known_epoch=1)
    trust = NodeTrust(
        identity=1.0, freshness=1.0, acoustic_health=1.0,
        spatial_consistency=1.0, calibration=1.0, tamper_state=1.0,
        temporal_integrity=1.0, behavioral_stability=1.0,
        epoch=1
    )
    _, effective_trust, _ = evaluator.evaluate(trust)
    assert 0.0 <= effective_trust <= 1.0
