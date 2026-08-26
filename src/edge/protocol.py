import math
import re
from dataclasses import dataclass
from enum import Enum

class PrivacyState(Enum):
    RAW_AUDIO_DEAD = "RAW_AUDIO_DEAD"

@dataclass(frozen=True, slots=True)
class AcousticObservation:
    node_id: str
    sequence: int
    monotonic_timestamp: float
    spl_estimate: float
    event_class: str
    confidence: float
    temporal_velocity: float
    temporal_acceleration: float
    privacy_state: PrivacyState
    feature_digest: str
    cryptographic_digest: str

    def __post_init__(self):
        # 1. Structural constraints
        if self.sequence < 0:
            raise ValueError("Sequence must be >= 0")
        if self.monotonic_timestamp < 0:
            raise ValueError("Timestamp must be >= 0")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be in bounds [0.0, 1.0]")
            
        # 2. Finite numeric bounds (No NaN or Infinity injections)
        for val in (self.spl_estimate, self.confidence, self.temporal_velocity, 
                    self.temporal_acceleration, self.monotonic_timestamp):
            if not math.isfinite(val):
                raise ValueError(f"Numeric values must be finite, received: {val}")
        
        # 3. Explicit privacy enforcement
        if self.privacy_state != PrivacyState.RAW_AUDIO_DEAD:
            raise ValueError("Invalid privacy state: MUST be RAW_AUDIO_DEAD")
            
        # 4. Cryptographic lineage requirements (Assumes 64-char hex SHA-256)
        hex_pattern = re.compile(r"^[a-fA-F0-9]{64}$")
        if not hex_pattern.match(self.feature_digest):
            raise ValueError("feature_digest must be a valid 64-character hex string")
        if not hex_pattern.match(self.cryptographic_digest):
            raise ValueError("cryptographic_digest must be a valid 64-character hex string")
