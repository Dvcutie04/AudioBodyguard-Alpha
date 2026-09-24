import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class EvidenceVector:
    energy: float = 0.0
    timestamp: float = 0.0
    features: Dict[str, float] = field(default_factory=dict)

class EvidenceEnvelope:
    def __init__(self, event_id: str, sequence: int, source_id: str, sensor_quality: float, feature_vector: Dict[str, float], change_point_evidence: Any, posterior_before: float, posterior_after: float, model_version: str = "1.0.0", policy_version: str = "1.0.0", timestamp: Optional[float] = None):
        for val, name in [(sensor_quality, "sensor_quality"), (posterior_before, "posterior_before"), (posterior_after, "posterior_after")]:
            if val is not None and isinstance(val, float) and val != val:
                raise ValueError(f"NaN values not allowed in {name}")
        if not (0.0 <= sensor_quality <= 1.0) or not (0.0 <= posterior_before <= 1.0) or not (0.0 <= posterior_after <= 1.0):
            raise ValueError("Out of bounds")
        self._event_id, self._sequence, self._timestamp, self._source_id, self._sensor_quality, self._feature_vector, self._change_point_evidence, self._posterior_before, self._posterior_after, self._model_version, self._policy_version, self._immutable = event_id, sequence, (timestamp if timestamp is not None else time.time()), source_id, sensor_quality, dict(feature_vector), change_point_evidence, posterior_before, posterior_after, model_version, policy_version, True
    @property
    def event_id(self) -> str: return self._event_id
    @property
    def sequence(self) -> int: return self._sequence
    @property
    def timestamp(self) -> float: return self._timestamp
    @property
    def source_id(self) -> str: return self._source_id
    @property
    def sensor_quality(self) -> float: return self._sensor_quality
    @property
    def feature_vector(self) -> Dict[str, float]: return dict(self._feature_vector)
    @property
    def change_point_evidense(self) -> Any: return self._change_point_evidence
    @property
    def posterior_before(self) -> float: return self._posterior_before
    @property
    def posterior_after(self) -> float: return self._posterior_after
    @property
    def model_version(self) -> str: return self._model_version
    @property
    def policy_version(self) -> str: return self._policy_version
    def __setattr__(self, key, value):
        if getattr(self, "_immutable", False):
            raise AttributeError("Immutable")
        super().__setattr__(key, value)
