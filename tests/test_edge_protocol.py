import unittest
from src.edge.protocol import AcousticObservation, PrivacyStatus


class TestEdgeProtocol(unittest.TestCase):

    def setUp(self):
        self.valid_kwargs = {
            "node_id": "edge_node_01",
            "sequence_id": 1,
            "monotonic_timestamp_ns": 1000000000,
            "spl_estimate": 60.0,
            "event_class": "ambient",
            "confidence": 1.0,
            "temporal_metric": 0.5,
            "privacy_status": PrivacyStatus.RAW_AUDIO_DEAD,
            "feature_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "payload_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        }
        self.obs = AcousticObservation(**self.valid_kwargs)

    def test_valid_observation_instantiation(self):
        self.assertEqual(self.obs.node_id, "edge_node_01")
        self.assertEqual(self.obs.privacy_status, PrivacyStatus.RAW_AUDIO_DEAD)

    def test_invalid_privacy_status_raises(self):
        invalid_kwargs = self.valid_kwargs.copy()
        invalid_kwargs["privacy_status"] = "RAW_AUDIO_DEAD"  # String instead of Enum
        with self.assertRaises(ValueError):
            AcousticObservation(**invalid_kwargs)

    def test_raw_audio_field_is_impossible(self):
        with self.assertRaises((AttributeError, TypeError)):
            setattr(self.obs, "raw_audio", b"10101010")

        with self.assertRaises((AttributeError, TypeError)):
            setattr(self.obs, "spl_estimate", 70.0)


if __name__ == "__main__":
    unittest.main()
