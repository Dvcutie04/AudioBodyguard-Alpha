from unittest import TestCase
from src.security.causal_trust import CausalTrustEvaluator

class TestCausalTrust(TestCase):
    def test_trust_score_bounds(self):
        evaluator = CausalTrustEvaluator()
        score = evaluator.evaluate(freshness_score=1.0, sensor_quality=0.9, historical_consistency=0.8)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_trust_degradation(self):
        evaluator = CausalTrustEvaluator()
        high_score = evaluator.evaluate(1.0, 1.0, 1.0)
        low_score = evaluator.evaluate(0.1, 0.2, 0.0)
        self.assertGreater(high_score, low_score)

if __name__ == "__main__":
    import unittest
    unittest.main()
