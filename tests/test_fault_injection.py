import unittest, math
from src.voice.orchestrator import SpatialVoiceEngine

class TestFaultInjectionAndHorizon(unittest.TestCase):
    def setUp(self):
        self.engine = SpatialVoiceEngine()

    def test_nan_sensor_fault(self):
        corrupted_frame = [0.1, float("nan"), 0.3]
        res = self.engine.process_frame(corrupted_frame)
        self.assertEqual(res["status"], "FAULT_DETECTED")
        self.assertEqual(res["route"], "FAIL_SAFE_GATED")

    def test_clipped_signal_fault(self):
        clipped_frame = [0.1, 1.0, 0.2]
        res = self.engine.process_frame(clipped_frame)
        self.assertEqual(res["status"], "FAULT_DETECTED")
        self.assertEqual(res["route"], "FAIL_SAFE_GATED")

    def test_dead_channel_fault(self):
        dead_frame = [0.0, 0.0, 0.0]
        res = self.engine.process_frame(dead_frame)
        self.assertEqual(res["status"], "FAULT_DETECTED")
        self.assertEqual(res["route"], "FAIL_SAFE_GATED")

    def test_predictive_rising_threat(self):
        _ = self.engine.process_frame([0.01, -0.01, 0.01])
        res = self.engine.process_frame([0.5, -0.5, 0.5])
        self.assertEqual(res["status"], "processed")
        self.assertEqual(res["trajectory"], "RISING_THREAT")
