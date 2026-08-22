import unittest
from src.voice.feature_fabric import FeatureFabric
from src.voice.trust_router import TrustGradientRouter

class TestMultiChannelFabric(unittest.TestCase):
    def setUp(self):
        self.fabric = FeatureFabric()
        self.router = TrustGradientRouter()

    def test_single_channel(self):
        res = self.fabric.extract_features([0.1, -0.2, 0.3])
        self.assertEqual(res["channels"], 1)
        self.assertEqual(res["energy_delta"], 0.0)

    def test_multi_channel_spatial_delta(self):
        ch1 = [0.1, -0.2, 0.3]
        ch2 = [0.5, -0.8, 0.9]
        res = self.fabric.extract_features([ch1, ch2])
        self.assertEqual(res["channels"], 2)
        self.assertGreater(res["energy_delta"], 0.0)

    def test_router_integration(self):
        res = self.fabric.extract_features([[0.001, -0.001], [0.002, -0.002]])
        decision = self.router.evaluate(res)
        self.assertEqual(decision["route"], "NOISE_GATE")
