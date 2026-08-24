from dataclasses import dataclass

@dataclass(frozen=True)
class EvidenceVector:
    acoustic_energy: float
    spectral_change: float
    impulsiveness: float
    periodicity: float
    persistence: float
    spatial_change: float
    escalation: float
    anomaly_score: float
