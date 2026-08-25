from dataclasses import dataclass
from typing import Dict, Optional
from src.inference.threat_trajectory import TrajectoryState

@dataclass(frozen=True)
class InferenceResult:
    event_id: str
    timestamp: float
    threat_probability: float
    confidence: float
    hypothesis: str
    semantic_state: str
    feature_summary: Dict[str, float]
    model_version: str
    inference_latency_us: float
    sensor_quality_ok: bool
    trajectory: Optional[TrajectoryState] = None

