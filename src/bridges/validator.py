import hashlib
from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope


class EnvelopeValidator:

    def __init__(self):
        self._seen_sequences = set()

    def validate(self, envelope: ObservationEnvelope) -> bool:
        # 1. Encode the observation payload directly as-is
        encoded_bytes = CanonicalCodec.encode_observation(envelope.payload)
        computed_digest = hashlib.sha256(encoded_bytes).hexdigest()

        # 2. Match against envelope's declared digest
        if computed_digest != envelope.payload_digest:
            raise ValueError("Payload digest mismatch: payload contents have been tampered with")

        # 3. Replay check
        state_key = (envelope.node_id, envelope.sequence_id)
        if state_key in self._seen_sequences:
            raise ValueError(f"Replay detected for sequence {envelope.sequence_id} from node {envelope.node_id}")

        self._seen_sequences.add(state_key)
        return True
