import time
from src.inference.inference_result import InferenceResult
from src.inference.evidence_vector import EvidenceVector
from src.inference.sensor_gate import SensorQualityGate
from src.inference.temporal_accumulator import TemporalEvidenceAccumulator

class ThreatInferenceEngine:
    def __init__(self, model_version: str = "v1.0.0-omega"):
        self.model_version = model_version
        self.sensor_gate = SensorQualityGate()
        self.accumulator = TemporalEvidenceAccumulator()

    def evaluate(self, event_id: str, timestamp: float, raw_stats: dict, ev: EvidenceVector) -> InferenceResult:
        start_time = time.time_ns()
        if not self.sensor_gate.validate(raw_stats):
            latency = (time.time_ns() - start_time) / 1000.0
            return InferenceResult(event_id, timestamp, 0.0, 0.0, "UNKNOWN_SENSOR_DEGRADED", "UNKNOWN", {}, self.model_version, latency, False)
        
        instant_p = min(1.0, max(0.0, (0.3 * ev.anomaly_score) + (0.3 * ev.impulsiveness) + (0.4 * ev.escalation)))
        smoothed_p = self.accumulator.update(instant_p)
        
        confidence = min(1.0, max(0.1, 1.0 - abs(ev.persistence - 0.5)))
        
        if smoothed_p < 0.35:
            state = "BENIGN"
            hypothesis = "Normal ambient environment"
        elif smoothed_p < 0.75:
            state = "ELEVATED"
            hypothesis = "Noticeable transient or non-standard acoustic activity"
        else:
            state = "THREAT"
            hypothesis = "High-confidence high-escalation threat signature detected"
            
        summary = {"anomaly_score": ev.anomaly_score, "escalation": ev.escalation, "smoothed_probability": smoothed_p}
        latency = (time.time_ns() - start_time) / 1000.0
        
        return InferenceResult(event_id, timestamp, smoothed_p, confidence, hypothesis, state, summary, self.model_version, latency, True)
