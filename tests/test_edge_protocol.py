import unittest
from src.edge.protocol import AcousticObservation, PrivacyState

class TestEdgeProtocol(unittest.TestCase):
    def setUp(self):
        self.valid_kwargs = {
            "node_id": "edge_node_alpha",
            "sequence": 42,
            "monotonic_timestamp": 1682345.0,
            "spl_estimate": 65.4,
            "event_class": "COMMERCIAL_TRANSITION",
            "confidence": 0.94,
            "temporal_velocity": 2.1,
            "temporal_acceleration": 0.5,
            "privacy_state": PrivacyState.RAW_AUDIO_DEAD,
            "feature_digest": "a" * 64,  # Mock valid SHA-256 hex
            "cryptographic_digest": "b" * 64
        }

    def test_observation_is_immutable(self):
        obs = AcousticObservation(**self.valid_kwargs)
        with self.assertRaises(AttributeError):
            obs.spl_estimate = 70.0  # Frozen check

    def test_raw_audio_field_is_impossible(self):
        obs = AcousticObservation(**self.valid_kwargs)
        
        # Because of slots=True, dynamically adding attributes is strictly blocked by the interpreter
        with self.assertRaises(AttributeError):
            obs.raw_audio = b"10101010"
            
        # Even attempting to bypass standard assignment fails
        with self.assertRaises(AttributeError):
            object.__setattr__(obs, "raw_audio", b"10101010")

    def test_invalid_confidence_rejected(self):
        kwargs = self.valid_kwargs.copy()
        kwargs["confidence"] = 1.05
        with self.assertRaises(ValueError):
            AcousticObservation(**kwargs)

    def test_invalid_sequence_rejected(self):
        kwargs = self.valid_kwargs.copy()
        kwargs["sequence"] = -1
        with self.assertRaises(ValueError):
            AcousticObservation(**kwargs)

    def test_invalid_privacy_state_rejected(self):
        kwargs = self.valid_kwargs.copy()
        kwargs["privacy_state"] = "JUST_A_STRING" # Must be the explicit Enum
        with self.assertRaises(ValueError):
            AcousticObservation(**kwargs)

    def test_non_finite_values_rejected(self):
        kwargs = self.valid_kwargs.copy()
        kwargs["spl_estimate"] = float('inf')
        with self.assertRaises(ValueError):
            AcousticObservation(**kwargs)

    def test_digest_required_and_formatted(self):
        kwargs = self.valid_kwargs.copy()
        kwargs["feature_digest"] = "too_short_hash"
        with self.assertRaises(ValueError):
            AcousticObservation(**kwargs)

if __name__ == "__main__":
    unittest.main()
