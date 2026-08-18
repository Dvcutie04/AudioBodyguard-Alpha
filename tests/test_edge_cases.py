import unittest
from src.voice.predictive_horizon import PredictiveHorizon
from src.voice.sensor_health import SensorHealthMonitor
from src.voice.trust_router import TrustGradientRouter

class TestEdgeCases(unittest.TestCase):
    def test_horizon_buffer_overflow(self):
        ph = PredictiveHorizon()
        for _ in range(20):
            ph.update_and_predict([0.1, 0.2])

    def test_health_empty_channel(self):
        sh = SensorHealthMonitor()
        res = sh.inspect_frame([[]])
        self.assertIn("FAULT_EMPTY_CHANNEL", str(res))

    def test_router_speculative(self):
        tr = TrustGradientRouter()
        res = tr.evaluate({"trust_score": 0.75, "entropy": 0.2})
        self.assertIsNotNone(res)
