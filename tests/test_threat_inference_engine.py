"""
Unit tests for ThreatInferenceEngine Bayesian probability evaluation and attenuation recommendations.
"""

import pytest
from src.inference.threat_inference_engine import ThreatInferenceEngine, ThreatAssessment


def test_nominal_environment_no_threat():
    engine = ThreatInferenceEngine(threat_threshold=0.65)
    # Low noise (55 dB), high trust (1.0), high expectation Z (0.8)
    assessment = engine.evaluate_threat(
        expectation_z=0.8,
        consensus_trust=1.0,
        ambient_db=55.0,
        target_db=65.0
    )
    
    assert assessment.is_threat_detected is False
    assert assessment.threat_probability < 0.65
    assert assessment.recommended_attenuation_db == 0.0


def test_high_noise_triggers_threat_and_attenuation():
    engine = ThreatInferenceEngine(threat_threshold=0.65)
    # Excessive noise (95 dB), high trust (1.0), low expectation Z (-0.6)
    assessment = engine.evaluate_threat(
        expectation_z=-0.6,
        consensus_trust=1.0,
        ambient_db=95.0,
        target_db=65.0
    )
    
    assert assessment.is_threat_detected is True
    assert assessment.threat_probability >= 0.65
    assert assessment.recommended_attenuation_db == 30.0


def test_low_trust_suppresses_untrusted_threat_trigger():
    engine = ThreatInferenceEngine(threat_threshold=0.65)
    # Excessive noise (95 dB), but low consensus trust (0.2)
    assessment = engine.evaluate_threat(
        expectation_z=-0.6,
        consensus_trust=0.2,
        ambient_db=95.0,
        target_db=65.0
    )
    
    # Low trust suppresses threat detection to prevent false positives from compromised nodes
    assert assessment.is_threat_detected is False
    assert assessment.recommended_attenuation_db == 0.0
