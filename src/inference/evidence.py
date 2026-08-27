import hashlib
import time
from typing import Optional, List
from src.bridges.envelope import ObservationEnvelope
from src.inference.hypothesis import HypothesisFrame


class TemporalEvidenceAccumulator:
    """
    Accumulates validated ObservationEnvelopes over a temporal window
    and calculates HypothesisFrame probability scores without leaking audio data.
    """

    def __init__(self, window_size: int = 5, spl_threshold: float = 70.0):
        self.window_size = window_size
        self.spl_threshold = spl_threshold
        self.buffer: List[ObservationEnvelope] = []

    def process_envelope(self, envelope: ObservationEnvelope) -> Optional[HypothesisFrame]:
        self.buffer.append(envelope)
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)

        if len(self.buffer) < self.window_size:
            return None

        # Calculate temporal evidence metrics over window
        avg_spl = sum(e.payload.spl_estimate for e in self.buffer) / len(self.buffer)
        high_spl_count = sum(1 for e in self.buffer if e.payload.spl_estimate >= self.spl_threshold)

        # Compute probability & quality
        probability = min(1.0, (high_spl_count / self.window_size) * 0.95 + 0.05)
        evidence_quality = 0.90 if avg_spl > 65.0 else 0.75

        # Build composite source lineage digest over all envelopes in the window
        combined_digests = ":".join(e.payload_digest for e in self.buffer)
        lineage_digest = hashlib.sha256(combined_digests.encode("utf-8")).hexdigest()

        start_seq = self.buffer[0].sequence_id
        end_seq = self.buffer[-1].sequence_id
        window_duration_ns = self.buffer[-1].monotonic_timestamp_ns - self.buffer[0].monotonic_timestamp_ns

        return HypothesisFrame(
            hypothesis_id=f"hyp_seq_{start_seq}_{end_seq}",
            hypothesis_type="COMMERCIAL_ACTIVE",
            hypothesis_probability=probability,
            evidence_quality=evidence_quality,
            model_confidence=0.92,
            evidence_window_ns=window_duration_ns,
            sequence_start=start_seq,
            sequence_end=end_seq,
            source_lineage_digest=lineage_digest,
            model_version="v1.0.0",
            created_at_ns=time.time_ns(),
        )
