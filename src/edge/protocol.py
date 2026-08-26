import math
from dataclasses import dataclass
from enum import Enum


class PrivacyStatus(Enum):
    RAW_AUDIO_DEAD = "RAW_AUDIO_DEAD"


@dataclass(frozen=True, slots=True)
class AcousticObservation:
    node_id: str
    sequence_id: int
    monotonic_timestamp_ns: int
    spl_estimate: float
    event_class: str
    confidence: float
    temporal_metric: float
    privacy_status: PrivacyStatus
    feature_digest: str
    payload_digest: str

    def __post_init__(self):
        # Strict type and state validation for Privacy Status
        if not isinstance(self.privacy_status, PrivacyStatus) or self.privacy_status != PrivacyStatus.RAW_AUDIO_DEAD:
            raise ValueError("privacy_status must be PrivacyStatus.RAW_AUDIO_DEAD")

        # Non-negative sequence ID and nanosecond monotonic timestamp
        if self.sequence_id < 0:
            raise ValueError("sequence_id must be non-negative")
        if self.monotonic_timestamp_ns < 0:
            raise ValueError("monotonic_timestamp_ns must be non-negative")

        # Confidence bounds [0.0, 1.0]
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        # Finite metrics check
        for val, name in [
            (self.spl_estimate, "spl_estimate"),
            (self.temporal_metric, "temporal_metric"),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"{name} must be a finite float")

        # Hex digest format check (SHA-256 length)
        for digest, name in [
            (self.feature_digest, "feature_digest"),
            (self.payload_digest, "payload_digest"),
        ]:
            if len(digest) != 64 or not all(c in "0123456789abcdefABCDEF" for c in digest):
                raise ValueError(f"{name} must be a valid 64-character hex SHA-256 string")
