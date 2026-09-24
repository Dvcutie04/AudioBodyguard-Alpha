import unittest
from src.policy.policy_vector import PolicyVectorManager, PolicyUpdateEvent
from src.policy.safety_governor import SafetyGovernor
class TestPolicySystem(unittest.TestCase):
    def test_all(self):
        m = PolicyVectorManager()
        g = SafetyGovernor(m)
        self.assertEqual(m.current_state.version, 0)
        res = g.evaluate_action("alert", 0.75, 10.0)
        self.assertTrue(res["is_alert"])
if __name__ == "__main__":
    unittest.main()
