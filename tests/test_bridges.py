import hashlib
import unittest
from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope
from src.bridges.protocol import MessageType, ProtocolVersion
from src.bridges.validator import EnvelopeValidator
from src.edge.protocol import AcousticObservation, PrivacyStatus


class TestBridgesModule(unittest.TestCase):

    def setUp(self):
        # Base parameters with dummy digest placeholder
        base_kwargs = {
            "node_id": "edge_node_01",
            "sequence_id": 1,
            "monotonic_timestamp_ns": 1000000000,
            "spl_estimate": 60.0,
            "event_class": "ambient",
            "confidence": 1.0,
            "temporal_metric": 0.5,
            "privacy_status": PrivacyStatus.RAW_AUDIO_DEAD,
            "feature_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "payload_digest": "0000000000000000000000000000000000000000000000000000000000000000",
        }

        # Calculate canonical SHA-256 digest of observation payload
        temp_obs = AcousticObservation(**base_kwargs)
        encoded_bytes = CanonicalCodec.encode_observation(temp_obs)
        self.correct_digest = hashlib.sha256(encoded_bytes).hexdigest()

        # Update base kwargs to use matching computed digest
        base_kwargs["payload_digest"] = self.correct_digest
        
        # Recalculate hash for final observation object so state matches payload content
        final_obs = AcousticObservation(**base_kwargs)
        final_bytes = CanonicalCodec.encode_observation(final_obs)
        self.correct_digest = hashlib.sha256(final_bytes).hexdigest()

        base_kwargs["payload_digest"] = self.correct_digest
        self.obs = AcousticObservation(**base_kwargs)

        self.envelope = ObservationEnvelope(
            protocol_version=ProtocolVersion.AQSS_EDGE_OBSERVATION_V1,
            message_type=MessageType.ACOUSTIC_OBSERVATION,
            node_id="edge_node_01",
            sequence_id=1,
            monotonic_timestamp_ns=1000000000,
            payload_digest=self.correct_digest,
            authentication_tag="dummy_mac_tag",
            payload=self.obs,
        )

    def test_canonical_codec_roundtrip(self):
        encoded = CanonicalCodec.encode_observation(self.obs)
        decoded = CanonicalCodec.decode_observation(encoded)
        self.assertEqual(decoded.node_id, self.obs.node_id)
        self.assertEqual(decoded.privacy_status, PrivacyStatus.RAW_AUDIO_DEAD)

    def test_validator_accepts_valid_envelope(self):
        validator = EnvelopeValidator()
        self.assertTrue(validator.validate(self.envelope))

    def test_validator_rejects_replayed_sequence(self):
        validator = EnvelopeValidator()
        validator.validate(self.envelope)
        with self.assertRaises(ValueError):
            validator.validate(self.envelope)


if __name__ == "__main__":
    unittest.main()

