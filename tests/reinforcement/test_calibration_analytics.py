import unittest
from src.shadow.calibration_analytics import CalibrationAnalyticsEngine

class TestCalibrationAnalytics(unittest.TestCase):
    def test_well_calibrated_window(self):
        engine = CalibrationAnalyticsEngine(window_days=7)
        records = [
            {"confidence_weight": 0.8, "feedback_type": "AGREE", "bounded_delta": 0.05},
            {"confidence_weight": 0.85, "feedback_type": "AGREE", "bounded_delta": 0.02},
            {"confidence_weight": 0.2, "feedback_type": "DISAGREE", "bounded_delta": 0.01}
        ]
        metrics = engine.evaluate_window(records)
        self.assertEqual(metrics.total_decisions, 3)
        self.assertLess(metrics.calibration_error, 0.3)
        self.assertEqual(metrics.status, "WELL_CALIBRATED")

    def test_empty_records(self):
        engine = CalibrationAnalyticsEngine()
        metrics = engine.evaluate_window([])
        self.assertEqual(metrics.status, "INSUFFICIENT_DATA")

if __name__ == "__main__":
    unittest.main()
