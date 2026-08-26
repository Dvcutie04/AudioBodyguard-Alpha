import hashlib
from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope
from src.edge.protocol import PrivacyStatus


class EnvelopeValidator:
    """Validates schema, digest integrity, and sequence monotonic invariants."""

    def __init__(self):
        self._last_sequence: dict[str, int] = {}

    def validate(self, envelope: ObservationEnvelope) -> bool:
        # Enforce non-replayed, strictly increasing sequence ID per node
        last_seq = self._last_sequence.get(envelope.node_id, -1)
        if envelope.sequence_id <= last_seq:
            raise ValueError(
                f"Replay or out-of-order frame detected for node {envelope.node_id}: "
                f"seq {envelope.sequence_id} <= last {last_seq}"
            )

        # Enforce canonical payload digest matches calculated SHA-256
        encoded_payload = CanonicalCodec.encode_observation(envelope.payload)
        calculated_digest = hashlib.sha256(encoded_payload).hexdigest()
        if calculated_digest != envelope.payload_digest:
            raise ValueError("Payload digest mismatch: payload contents have been tampered with")

        # Enforce strict privacy status invariant
        if envelope.payload.privacy_status != PrivacyStatus.RAW_AUDIO_DEAD:
            raise ValueError("Invalid privacy status in observation payload")

        self._last_sequence[envelope.node_id] = envelope.sequence_id
        return True
