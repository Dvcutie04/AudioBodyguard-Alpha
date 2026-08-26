from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class HypothesisFrame:
    hypothesis_id: str
    hypothesis_type: str
    hypothesis_probability: float
    evidence_quality: float
    model_confidence: float
    evidence_window_ns: int
    sequence_start: int
    sequence_end: int
    source_lineage_digest: str
    model_version: str
    created_at_ns: int
