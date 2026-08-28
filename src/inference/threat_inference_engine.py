"""
AQSS-36-OMEGA Threat Inference Engine

Combines Pauli Z quantum expectation values, consensus trust scores,
and real-time sound pressure deltas into actionable threat probabilities.
"""

import math
from dataclasses import dataclass


@dataclass
class ThreatAssessment:
    threat_probability: float
    confidence_score: float
    is_threat_detected: bool
    recommended_attenuation_db: float


class ThreatInferenceEngine:
    """
    Bayesian threat probability calculation over quantum expectation and trust metrics.
    """
    def __init__(self, threat_threshold: float = 0.65):
        self.threat_threshold = threat_threshold

    def evaluate_threat(
        self,
        expectation_z: float,
        consensus_trust: float,
        ambient_db: float,
        target_db: float = 65.0
    ) -> ThreatAssessment:
        """
        Computes posterior threat probability P(Threat | Z, Trust, dB).
        """
        # Quantum risk component mapped from expectation value [-1.0, 1.0] -> [0.0, 1.0]
        quantum_risk = (1.0 - expectation_z) / 2.0
        
        # Acoustic excess ratio above target baseline
        db_delta = max(0.0, ambient_db - target_db)
        acoustic_severity = 1.0 - math.exp(-db_delta / 20.0)
        
        # Weighted threat probability calculation
        raw_probability = (0.4 * quantum_risk) + (0.6 * acoustic_severity)
        
        # Modulate probability by network trust score
        effective_probability = raw_probability * consensus_trust
        
        is_threat = effective_probability >= self.threat_threshold
        
        # Target attenuation calculation
        recommended_attenuation = db_delta if is_threat else 0.0

        return ThreatAssessment(
            threat_probability=round(effective_probability, 4),
            confidence_score=round(consensus_trust, 4),
            is_threat_detected=is_threat,
            recommended_attenuation_db=round(recommended_attenuation, 2)
        )
