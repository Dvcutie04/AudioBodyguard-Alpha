import hashlib
import unittest
from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope
from src.bridges.protocol import MessageType, ProtocolVersion
from src.bridges.validator import EnvelopeValidator
from src.edge.protocol import AcousticObservation, PrivacyStatus


class TestBridgesModule(unittest.TestCase):

    def setUp(self):
        # 1. Base kwargs with dummy payload_digest
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

        # 2. Derive initial target canonical digest
        temp_obs = AcousticObservation(**base_kwargs)
        calculated_hash = hashlib.sha256(CanonicalCodec.encode_observation(temp_obs)).hexdigest()

        # 3. Apply calculated hash to base kwargs
        base_kwargs["payload_digest"] = calculated_hash
        self.obs = AcousticObservation(**base_kwargs)

        # 4. Compute final exact hash of self.obs
        final_digest = hashlib.sha256(CanonicalCodec.encode_observation(self.obs)).hexdigest()

        # 5. Lock both observation and envelope to the true final digest
        base_kwargs["payload_digest"] = final_digest
        self.obs = AcousticObservation(**base_kwargs)

        self.envelope = ObservationEnvelope(
            protocol_version=ProtocolVersion.AQSS_EDGE_OBSERVATION_V1,
            message_type=MessageType.ACOUSTIC_OBSERVATION,
            node_id="edge_node_01",
            sequence_id=1,
            monotonic_timestamp_ns=1000000000,
            payload_digest=final_digest,
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
