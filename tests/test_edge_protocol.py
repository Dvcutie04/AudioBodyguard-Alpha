import unittest
from src.edge.protocol import AcousticObservation


class TestEdgeProtocol(unittest.TestCase):

    def setUp(self):
        # Instantiate directly or adjust keys to match src/edge/protocol.py definition
        self.obs = AcousticObservation()

    def test_raw_audio_field_is_impossible(self):
        # Verify setting a non-existent field (dynamic attribute) raises AttributeError via slots
        with self.assertRaises(AttributeError):
            setattr(self.obs, "raw_audio", b"10101010")

        # Verify setting an existing frozen field raises AttributeError
        with self.assertRaises(AttributeError):
            setattr(self.obs, "spl_estimate", 70.0)


if __name__ == "__main__":
    unittest.main()
