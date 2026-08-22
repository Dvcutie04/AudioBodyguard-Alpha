import pytest
from audio_engine.fusion_router import TrustWeightedDecisionRouter

@pytest.fixture
def router():
    return TrustWeightedDecisionRouter()

def test_high_threat_agreement(router):
    assert router.evaluate(raw_threat=0.85, sensor_trust=0.9, spatial_agreement=True) == "ESCALATE"

def test_high_threat_low_trust(router):
    assert router.evaluate(raw_threat=0.85, sensor_trust=0.2, spatial_agreement=True) == "SUPPLIED_OR_DEGRADED"

def test_high_threat_spatial_contradiction(router):
    assert router.evaluate(raw_threat=0.85, sensor_trust=0.9, spatial_agreement=False) == "REDUCED_CONFIDENCE"

def test_moderate_threat_corroboration(router):
    assert router.evaluate(raw_threat=0.5, sensor_trust=0.8, spatial_agreement=True) == "PERMIT_ESCALATION"

def test_sensor_becomes_stale(router):
    assert router.evaluate(raw_threat=0.85, sensor_trust=0.9, spatial_agreement=True, sensor_age=6.0) == "SUPPLIED_OR_DEGRADED"

def test_conflicting_evidence_persists(router):
    assert router.evaluate(raw_threat=0.85, sensor_trust=0.8, spatial_agreement=False, persistence_counter=3) == "DEGRADED_STATE"

def test_invariant_unreliable_sensor_never_inflates(router):
    assert router.evaluate(raw_threat=0.99, sensor_trust=0.1, spatial_agreement=True) in ["SUPPLIED_OR_DEGRADED", "REDUCED_CONFIDENCE"]
