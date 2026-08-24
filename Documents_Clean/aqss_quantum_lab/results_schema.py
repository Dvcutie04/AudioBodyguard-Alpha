from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class ModelOutput:
    """Output from a threat detection model (classical or quantum)."""
    p_threat: float  # Threat probability [0.0, 1.0]
    latency_us: float  # Inference latency in microseconds

@dataclass
class BenchmarkRecord:
    """Single benchmark trial record."""
    sample_id: str
    ground_truth: int  # 0 = no threat, 1 = threat
    classical: ModelOutput
    quantum: ModelOutput

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
