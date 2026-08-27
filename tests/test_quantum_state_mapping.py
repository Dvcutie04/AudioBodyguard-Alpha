import pytest
from src.quantum.classifier import TwoQubitAnalyticalClassifier


def test_two_qubit_analytical_classifier_invariants():
    classifier = TwoQubitAnalyticalClassifier()

    # 1. 0 <= p_i <= 1 and Sum(p_i) == 1.0 (within float tolerance)
    prob_dist = classifier.predict_probabilities(
        spl_normalized=0.75, spectral_flatness=0.30, theta_bias=0.1
    )
    assert len(prob_dist) == 4
    total_prob = sum(prob_dist.values())
    assert pytest.approx(total_prob, abs=1e-4) == 1.0
    for state, p in prob_dist.items():
        assert 0.0 <= p <= 1.0

    # 2. Deterministic probability vector for fixed inputs + theta_bias
    p1 = classifier.predict_probabilities(
        spl_normalized=0.5, spectral_flatness=0.5, theta_bias=0.2
    )
    p2 = classifier.predict_probabilities(
        spl_normalized=0.5, spectral_flatness=0.5, theta_bias=0.2
    )
    assert p1 == p2

    # 3. Out-of-bounds inputs (spl=0, spl=1, flatness=0, flatness=1) cleanly handled
    zero_bounds = classifier.predict_probabilities(
        spl_normalized=0.0, spectral_flatness=0.0, theta_bias=0.0
    )
    assert pytest.approx(sum(zero_bounds.values()), abs=1e-4) == 1.0

    one_bounds = classifier.predict_probabilities(
        spl_normalized=1.0, spectral_flatness=1.0, theta_bias=1.0
    )
    assert pytest.approx(sum(one_bounds.values()), abs=1e-4) == 1.0
