from dataclasses import dataclass
from typing import Tuple
import hashlib

@dataclass(frozen=True)
class QuantumWorkItem:
    work_id: str
    feature_vector: Tuple[float, ...]
    feature_schema: str
    circuit_id: str
    circuit_version: str
    shots: int = 1024
    priority: int = 0
    source: str = "acoustic"
    telemetry_hash: str = ""

    @classmethod
    def from_features(cls, work_id, feature_vector, feature_schema, circuit_id, circuit_version, shots=1024, priority=0, source="acoustic"):
        values = tuple(float(x) for x in feature_vector)
        payload = ",".join(f"{x:.8g}" for x in values).encode()
        digest = hashlib.sha256(payload).hexdigest()
        return cls(work_id, values, feature_schema, circuit_id, circuit_version, shots, priority, source, digest)
