import time
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class SensorObservation:
    sensor_id: str
    modality: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.0
    integrity: float = 1.0
    freshness: float = 1.0
    provenance: str = "local_direct"
    anomaly_score: float = 0.0

    def compute_epistemic_weight(self) -> float:
        base_weight = self.confidence * self.integrity * self.freshness
        penalized_weight = max(0.0, base_weight - (self.anomaly_score * 0.5))
        return round(penalized_weight, 4)

class SensorTrustEvaluator:
    def __init__(self, max_staleness_seconds: float = 2.0):
        self.max_staleness = max_staleness_seconds

    def evaluate(self, observation: SensorObservation) -> Dict[str, Any]:
        now = time.time()
        age = now - observation.timestamp

        if age > self.max_staleness:
            observation.freshness = 0.0
        else:
            observation.freshness = max(0.0, 1.0 - (age / self.max_staleness))

        epistemic_weight = observation.compute_epistemic_weight()

        return {
            "sensor_id": observation.sensor_id,
            "modality": observation.modality,
            "epistemic_weight": epistemic_weight,
            "is_trusted": epistemic_weight > 0.5,
            "metrics": {
                "confidence": observation.confidence,
                "integrity": observation.integrity,
                "freshness": observation.freshness,
                "anomaly_score": observation.anomaly_score
            }
        }
