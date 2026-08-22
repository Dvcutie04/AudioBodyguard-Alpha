import pytest
from audio_engine.trust_model import TrustEngine

def test_trust_engine_initialization():
    engine = TrustEngine(alpha=0.2, initial_trust=1.0)
    assert engine.effective_trust == 1.0

def test_trust_recovery_cycle():
    engine = TrustEngine(alpha=0.5, initial_trust=1.0)
    assert engine.effective_trust == 1.0
    engine.update(freshness_factor=1.0, noise_factor=0.2, conflict_factor=0.5, stability_factor=1.0)
    degraded = engine.effective_trust
    assert degraded < 1.0
    for _ in range(5):
        engine.update(freshness_factor=1.0, noise_factor=1.0, conflict_factor=1.0, stability_factor=1.0)
    assert engine.effective_trust > degraded
