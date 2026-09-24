import unittest
from src.policy.policy_vector import PolicyVectorManager
from src.policy.safety_governor import SafetyGovernor
from src.core.threat_evaluator import ThreatEvaluator
class TestThreatEvaluator(unittest.TestCase):
    def test_evaluation(self):
        pm = PolicyVectorManager()
        gov = SafetyGovernor(pm)
        evaluator = ThreatEvaluator(gov)
        res = evaluator.assess_acoustic_spike(95.0, "sharp_transient")
        self.assertIn("p_threat", res)
        self.assertIn("evaluation", res)
if __name__ == "__main__":
    unittest.main()
