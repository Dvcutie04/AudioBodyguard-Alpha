import hashlib
from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope
from src.edge.protocol import AcousticObservation


class EnvelopeValidator:

    def __init__(self):
        self._seen_sequences = set()

    def validate(self, envelope: ObservationEnvelope) -> bool:
        # Reconstruct observation with zeroed payload_digest to check canonical hash
        payload_dict = envelope.payload.__dict__.copy()
        payload_dict["payload_digest"] = "0" * 64
        
        temp_obs = AcousticObservation(**payload_dict)
        encoded_bytes = CanonicalCodec.encode_observation(temp_obs)
        computed_digest = hashlib.sha256(encoded_bytes).hexdigest()

        if computed_digest != envelope.payload_digest:
            raise ValueError("Payload digest mismatch: payload contents have been tampered with")

        # Replay protection check
        state_key = (envelope.node_id, envelope.sequence_id)
        if state_key in self._seen_sequences:
            raise ValueError(f"Replay detected for sequence {envelope.sequence_id} from node {envelope.node_id}")

        self._seen_sequences.add(state_key)
        return True
