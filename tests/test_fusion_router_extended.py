import pytest
from audio_engine.fusion_router import TrustWeightedDecisionRouter

@pytest.fixture
def router():
    return TrustWeightedDecisionRouter()

@pytest.mark.parametrize("spatial,expected", [
    (0.00, "REDUCED_CONFIDENCE"),
    (0.25, "REDUCED_CONFIDENCE"),
    (0.35, "AMBIGUOUS_EVIDENCE"),
    (0.60, "ESCALATE"),
    (1.00, "ESCALATE"),
])
def test_continuous_spatial_confidence(router, spatial, expected):
    assert router.evaluate(raw_threat=0.85, sensor_trust=0.9, spatial_agreement=spatial) == expected

def test_ambiguous_evidence_states(router):
    assert router.evaluate(raw_threat=0.85, sensor_trust=0.9, spatial_agreement=0.4) == "AMBIGUOUS_EVIDENCE"
    assert router.evaluate(raw_threat=0.6, sensor_trust=0.8, spatial_agreement=0.2) == "AMBIGUOUS_EVIDENCE"

def test_trust_monotonicity(router):
    trusts = [0.9, 0.7, 0.5, 0.3, 0.1]
    results = [router.evaluate(raw_threat=0.85, sensor_trust=t, spatial_agreement=1.0) for t in trusts]
    assert results[0] == "ESCALATE"
    assert results[-1] == "SUPPLIED_OR_DEGRADED"

def test_staleness_monotonicity(router):
    ages = [0.0, 1.0, 3.0, 6.0, 10.0]
    results = [router.evaluate(raw_threat=0.85, sensor_trust=0.9, spatial_agreement=1.0, sensor_age=age) for age in ages]
    assert results[0] == "ESCALATE"
    assert results[-1] == "SUPPLIED_OR_DEGRADED"

def test_conflict_persistence(router):
    for p in range(5):
        res = router.evaluate(raw_threat=0.85, sensor_trust=0.8, spatial_agreement=0.2, persistence_counter=p)
        if p >= 3:
            assert res == "DEGRADED_STATE"

def test_boundary_thresholds(router):
    assert router.evaluate(raw_threat=0.499999, sensor_trust=0.8, spatial_agreement=1.0) == "SUPPLIED_OR_DEGRADED"
    assert router.evaluate(raw_threat=0.50, sensor_trust=0.8, spatial_agreement=1.0) == "PERMIT_ESCALATION"
    assert router.evaluate(raw_threat=0.500001, sensor_trust=0.8, spatial_agreement=1.0) == "PERMIT_ESCALATION"
    assert router.evaluate(raw_threat=0.799999, sensor_trust=0.8, spatial_agreement=1.0) == "PERMIT_ESCALATION"
    assert router.evaluate(raw_threat=0.80, sensor_trust=0.8, spatial_agreement=1.0) == "ESCALATE"
    assert router.evaluate(raw_threat=0.800001, sensor_trust=0.8, spatial_agreement=1.0) == "ESCALATE"
