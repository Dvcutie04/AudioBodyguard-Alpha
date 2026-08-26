import unittest
from src.edge.protocol import AcousticObservation


class TestEdgeProtocol(unittest.TestCase):

    def setUp(self):
        self.valid_kwargs = {
            "spl_estimate": 65.0,
            "spectral_flux": 0.42,
            "zero_crossing_rate": 0.15,
            "crest_factor": 3.2,
            "device_id": "edge_node_01",
        }

    def test_raw_audio_field_is_impossible(self):
        obs = AcousticObservation(**self.valid_kwargs)

        # Verify dynamic attribute assignment is blocked by dataclass slots
        with self.assertRaises(AttributeError):
            setattr(obs, "raw_audio", b"10101010")

        # Verify setting existing fields is blocked by frozen constraint
        with self.assertRaises(AttributeError):
            setattr(obs, "spl_estimate", 70.0)


if __name__ == "__main__":
    unittest.main()
