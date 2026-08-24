import pytest
from aqss_phase1_core import BayesianThreatEngine, AcousticObservation

class TestBayesianThreatEngine:
    def test_initialization(self):
        engine = BayesianThreatEngine(pr=0.85)
        assert engine.pr == 0.85

    def test_infer_low_threat(self):
        engine = BayesianThreatEngine(pr=0.85)
        obs = AcousticObservation(
            rms=0.01,
            peak=0.02,
            spectral_centroid=1000.0,
            zcr=100.0,
            db_level=20.0
        )
        result = engine.infer(obs)
        assert 0.0 <= result["p_threat"] <= 1.0
        assert 0.0 <= result["likelihood"] <= 1.0
        assert result["p_threat"] < 0.5  # Low threat expectation

    def test_infer_high_threat(self):
        engine = BayesianThreatEngine(pr=0.85)
        obs = AcousticObservation(
            rms=0.8,
            peak=0.9,
            spectral_centroid=5000.0,
            zcr=5000.0,
            db_level=90.0
        )
        result = engine.infer(obs)
        assert 0.0 <= result["p_threat"] <= 1.0
        assert result["p_threat"] > 0.5  # High threat expectation

    def test_infer_bounded_output(self):
        engine = BayesianThreatEngine(pr=0.5)
        obs = AcousticObservation(
            rms=0.5,
            peak=0.5,
            spectral_centroid=2500.0,
            zcr=2500.0,
            db_level=50.0
        )
        result = engine.infer(obs)
        assert isinstance(result, dict)
        assert "p_threat" in result
        assert "likelihood" in result
        assert 0.0 <= result["p_threat"] <= 1.0
        assert 0.0 <= result["likelihood"] <= 1.0
