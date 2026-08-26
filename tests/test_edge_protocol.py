import unittest
from src.edge.protocol import AcousticObservation


class TestEdgeProtocol(unittest.TestCase):

    def setUp(self):
        self.obs = AcousticObservation()

    def test_raw_audio_field_is_impossible(self):
        # Verify adding new dynamic field is blocked by slots/immutability
        with self.assertRaises((AttributeError, TypeError)):
            setattr(self.obs, "raw_audio", b"10101010")

        # Verify modifying existing frozen field is blocked
        with self.assertRaises((AttributeError, TypeError)):
            setattr(self.obs, "spl_estimate", 70.0)


if __name__ == "__main__":
    unittest.main()
