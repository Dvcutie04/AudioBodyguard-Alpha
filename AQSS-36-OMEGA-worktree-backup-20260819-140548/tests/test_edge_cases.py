import unittest
from src.voice.predictive_horizon import PredictiveHorizon
from src.voice.sensor_health import SensorHealthMonitor
from src.voice.trust_router import TrustGradientRouter

class TestEdgeCases(unittest.TestCase):
    def test_horizon_buffer_overflow(self):
        ph = PredictiveHorizon()
        for i in range(50):
            ph.update_and_predict({"energy": float(i)})

    def test_health_empty_frame(self):
        sh = SensorHealthMonitor()
        res = sh.inspect_frame([])
        self.assertEqual(res.get("status"), "FAULT_EMPTY_FRAME")

    def test_health_empty_channel(self):
        sh = SensorHealthMonitor()
        res = sh.inspect_frame([[]])
        self.assertTrue("FAULT_EMPTY_CHANNEL" in str(res.get("status")))

    def test_router_speculative(self):
        tr = TrustGradientRouter()
        res = tr.evaluate({"energy": 0.05, "zero_crossings": 10})
        self.assertEqual(res.get("route"), "HIGH_FREQUENCY_SPECULATIVE")
