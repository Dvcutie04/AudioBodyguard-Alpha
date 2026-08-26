import math
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AcousticObservation:
    node_id: str = "edge_node_01"
    sequence_id: int = 0
    timestamp: float = 0.0
    spl_estimate: float = 60.0
    event_class: str = "ambient"
    confidence: float = 1.0
    temporal_metric: float = 0.0
    privacy_status: str = "RAW_AUDIO_DEAD"
    feature_digest: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    crypto_digest: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def __post_init__(self):
        # Enforce non-negative sequence and timestamp constraints
        if self.sequence_id < 0:
            raise ValueError("sequence_id must be non-negative")
        if self.timestamp < 0.0:
            raise ValueError("timestamp must be non-negative")

        # Enforce confidence bounds [0.0, 1.0]
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        # Enforce finite numeric values
        for val, name in [
            (self.spl_estimate, "spl_estimate"),
            (self.temporal_metric, "temporal_metric"),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"{name} must be a finite float")

        # Strict privacy status invariant check
        if self.privacy_status != "RAW_AUDIO_DEAD":
            raise ValueError("privacy_status must strictly be RAW_AUDIO_DEAD")

        # Verify digest hex length format (64 hex characters for SHA-256)
        for digest, name in [
            (self.feature_digest, "feature_digest"),
            (self.crypto_digest, "crypto_digest"),
        ]:
            if len(digest) != 64 or not all(c in "0123456789abcdefABCDEF" for c in digest):
                raise ValueError(f"{name} must be a valid 64-character hex SHA-256 string")
